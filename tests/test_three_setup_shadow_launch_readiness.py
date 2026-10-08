"""TS7 rejection mechanics; real host and durable proof remains Q1 evidence."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import subprocess
import sys
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import build_three_setup_shadow_deployment_bundle as bundle
from scripts import check_dependency_lock as locks
from scripts import run_three_setup_shadow_runtime as runtime_entry
from scripts import three_setup_shadow_preflight as preflight
from scripts.verify_exact_release import ExactReleaseError, verify_staged_release
from trader_assist_v0.contracts.common import canonical_json_bytes, sha256_hex
from trader_assist_v0.multi_asset_shadow.production import (
    ThreeSetupProductionError,
    load_three_setup_config,
)

SHA = "a" * 40
TREE = "b" * 40


def _wheel_bytes(*, tags: tuple[str, ...] = ("cp312-cp312-manylinux_2_28_x86_64",),
                 metadata_count: int = 1) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as archive:
        for index in range(metadata_count):
            prefix = "nautilus_trader-2.0.0rc5" if index == 0 else "other-1.0"
            archive.writestr(
                f"{prefix}.dist-info/WHEEL",
                "Wheel-Version: 1.0\n" + "".join(f"Tag: {tag}\n" for tag in tags),
            )
    return stream.getvalue()


def _linux_host(monkeypatch: pytest.MonkeyPatch, glibc: str = "2.35") -> None:
    monkeypatch.setattr(preflight.platform, "system", lambda: "Linux")
    monkeypatch.setattr(preflight.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(preflight.platform, "libc_ver", lambda: ("glibc", glibc))
    monkeypatch.setattr(preflight.sys, "version_info", (3, 12))


def test_v1_config_cannot_be_deploy_preflight_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scripts import verify_exact_release

    monkeypatch.setattr(verify_exact_release, "verify_staged_release", lambda *_a, **_k: None)
    manifest = tmp_path / "release.json"
    manifest.write_text("{}", encoding="utf-8")
    config = tmp_path / "config.json"
    config.write_bytes(
        canonical_json_bytes(
            {
                "schema": "trader-assist-v0/three-setup-production-config/v1",
            }
        )
    )
    with pytest.raises(preflight.PreflightError, match="active E4 v2"):
        preflight.verify_candidate(
            root=tmp_path,
            release_manifest=manifest,
            config_path=config,
            expected_sha=SHA,
            expected_tree=TREE,
            expected_manifest_digest="c" * 64,
            pip_check_with=Path("python3.12"),
        )


@pytest.mark.parametrize(
    "missing", ("e4_evidence_root", "e4_manifest_path", "e4_snapshot_path", "e4_bar_types")
)
def test_v2_config_requires_every_e4_identity_field(
    tmp_path: Path,
    missing: str,
) -> None:
    root = Path(__file__).parents[1]
    example = json.loads((root / "deploy/p4a/config/three-setup-shadow.json.example").read_text())
    example["release_sha"] = SHA
    del example[missing]
    path = tmp_path / "config.json"
    path.write_bytes(canonical_json_bytes(example))
    with pytest.raises(ThreeSetupProductionError):
        load_three_setup_config(path)


@pytest.mark.parametrize(
    ("system", "machine", "python", "libc", "wheel_tag", "message"),
    [
        ("Darwin", "x86_64", (3, 12), ("glibc", "2.35"), "manylinux_2_17_x86_64", "OS"),
        ("Linux", "aarch64", (3, 12), ("glibc", "2.35"), "manylinux_2_17_x86_64", "architecture"),
        ("Linux", "x86_64", (3, 11), ("glibc", "2.35"), "manylinux_2_17_x86_64", "Python"),
        ("Linux", "x86_64", (3, 12), ("glibc", "2.16"), "manylinux_2_17_x86_64", "glibc"),
        ("Linux", "x86_64", (3, 12), ("glibc", "2.35"), "manylinux_2_17_aarch64", "wheel tag"),
    ],
)
def test_host_prerequisite_rejections(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    system: str,
    machine: str,
    python: tuple[int, int],
    libc: tuple[str, str],
    wheel_tag: str,
    message: str,
) -> None:
    wheel = tmp_path / f"nautilus_trader-2.0.0rc5-cp312-cp312-{wheel_tag}.whl"
    wheel_bytes = _wheel_bytes(tags=(f"cp312-cp312-{wheel_tag}",))
    wheel.write_bytes(wheel_bytes)
    monkeypatch.setattr(preflight.platform, "system", lambda: system)
    monkeypatch.setattr(preflight.platform, "machine", lambda: machine)
    monkeypatch.setattr(preflight.platform, "libc_ver", lambda: libc)
    monkeypatch.setattr(preflight.sys, "version_info", python)
    monkeypatch.setattr(preflight, "PILOT_WHEEL_SHA256", hashlib.sha256(wheel_bytes).hexdigest())
    with pytest.raises(preflight.PreflightError, match=message):
        preflight.verify_host_prerequisites(wheel)


def test_host_wheel_hash_rejected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_17_x86_64.whl"
    wheel.write_bytes(b"wrong")
    monkeypatch.setattr(preflight.platform, "system", lambda: "Linux")
    monkeypatch.setattr(preflight.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(preflight.platform, "libc_ver", lambda: ("glibc", "2.35"))
    monkeypatch.setattr(preflight.sys, "version_info", (3, 12))
    with pytest.raises(preflight.PreflightError, match="hash"):
        preflight.verify_host_prerequisites(wheel)


def test_intrinsic_wheel_tags_survive_permissive_rename(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _linux_host(monkeypatch, "2.17")
    data = _wheel_bytes()
    monkeypatch.setattr(preflight, "PILOT_WHEEL_SHA256", hashlib.sha256(data).hexdigest())
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_17_x86_64.whl"
    wheel.write_bytes(data)
    with pytest.raises(preflight.PreflightError, match="glibc"):
        preflight.verify_host_prerequisites(wheel)


@pytest.mark.parametrize(
    ("data", "message"),
    [
        (b"not zip", "malformed"),
        (_wheel_bytes(metadata_count=0), "missing or ambiguous"),
        (_wheel_bytes(metadata_count=2), "missing or ambiguous"),
        (_wheel_bytes(tags=("cp312-abi3-manylinux_2_28_x86_64",)), "unsupported"),
    ],
)
def test_intrinsic_wheel_metadata_rejects_malformed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, data: bytes, message: str,
) -> None:
    _linux_host(monkeypatch)
    wheel = tmp_path / "wheel.whl"
    wheel.write_bytes(data)
    monkeypatch.setattr(preflight, "PILOT_WHEEL_SHA256", hashlib.sha256(data).hexdigest())
    with pytest.raises(preflight.PreflightError, match=message):
        preflight.verify_host_prerequisites(wheel)


def test_intrinsic_wheel_exact_hash_compatible_passes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _linux_host(monkeypatch, "2.35")
    data = _wheel_bytes()
    wheel = tmp_path / "diagnostic-name.whl"
    wheel.write_bytes(data)
    monkeypatch.setattr(preflight, "PILOT_WHEEL_SHA256", hashlib.sha256(data).hexdigest())
    preflight.verify_host_prerequisites(wheel)


@pytest.mark.parametrize(
    ("installed", "message"),
    [
        ({"nautilus-trader": "2.0.0rc5"}, "missing"),
        ({"demo": "1", "nautilus-trader": "2.0.0rc4"}, "version"),
        ({"demo": "1", "nautilus-trader": "2.0.0rc5", "extra": "1"}, "unlocked"),
        ({"demo": "1", "nautilus-trader": "2.0.0rc5", "trader-assist-v0": "1"}, "unlocked"),
    ],
)
def test_target_distribution_closure_rejects_wrong_sets(
    monkeypatch: pytest.MonkeyPatch,
    installed: dict[str, str],
    message: str,
) -> None:
    monkeypatch.setattr(
        locks,
        "distributions",
        lambda: [
            SimpleNamespace(metadata={"Name": name}, version=version)
            for name, version in installed.items()
        ],
    )
    with pytest.raises(SystemExit, match=message):
        locks._verify_installed(
            {"demo": ("1", "0" * 64)},
            {"nautilus-trader": ("2.0.0rc5", "1" * 64)},
            project_distribution_expected=False,
        )


def test_target_distribution_closure_accepts_only_runtime_plus_pilot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        locks,
        "distributions",
        lambda: [
            SimpleNamespace(metadata={"Name": "demo"}, version="1"),
            SimpleNamespace(metadata={"Name": "nautilus-trader"}, version="2.0.0rc5"),
        ],
    )
    locks._verify_installed(
        {"demo": ("1", "0" * 64)},
        {"nautilus-trader": ("2.0.0rc5", "1" * 64)},
        project_distribution_expected=False,
    )


def test_target_distribution_closure_rejects_duplicate_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        locks, "distributions",
        lambda: [
            SimpleNamespace(metadata={"Name": "demo"}, version="1"),
            SimpleNamespace(metadata={"Name": "Demo"}, version="1"),
        ],
    )
    with pytest.raises(SystemExit, match="duplicate installed distribution"):
        locks._verify_installed(
            {"demo": ("1", "0" * 64)}, project_distribution_expected=False,
        )


def test_target_import_origin_rejects_outside_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "staged/src"
    source.mkdir(parents=True)
    outside = tmp_path / "other/__init__.py"
    outside.parent.mkdir()
    outside.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        locks.importlib.util, "find_spec", lambda _: SimpleNamespace(origin=str(outside))
    )
    with pytest.raises(SystemExit, match="outside exact staged source"):
        locks._verify_target_import(source)


def test_retained_manifest_external_digest_catches_recomputed_mutation(
    tmp_path: Path,
) -> None:
    # The trusted digest must be held outside the staged, no-Git artifact.
    from scripts.verify_exact_release import REQUIRED_FILES

    for relative in REQUIRED_FILES:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    config = tmp_path / "deploy/p4a/config/three-setup-shadow.json.example"
    config.write_bytes(
        canonical_json_bytes(
            {
                "schema": "trader-assist-v0/three-setup-production-config/v2",
            }
        )
    )
    (tmp_path / "src").mkdir()
    (tmp_path / "src/example.py").write_text("x = 1\n", encoding="utf-8")
    from scripts.verify_exact_release import build_release_manifest

    manifest = build_release_manifest(tmp_path, release_sha=SHA, release_tree=TREE)
    trusted_digest = str(manifest["manifest_sha256"])
    altered = json.loads(json.dumps(manifest))
    altered["dev_lock_sha256"] = "0" * 64
    altered["manifest_sha256"] = sha256_hex(
        canonical_json_bytes(
            {key: value for key, value in altered.items() if key != "manifest_sha256"}
        )
    )
    with pytest.raises(ExactReleaseError, match="external expected digest"):
        verify_staged_release(
            tmp_path,
            altered,
            expected_release_sha=SHA,
            expected_release_tree=TREE,
            expected_manifest_digest=trusted_digest,
        )


def test_validate_only_bypasses_credential_and_notification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: list[str] = []
    monkeypatch.setattr(runtime_entry, "verify_candidate", lambda **_: called.append("preflight"))
    monkeypatch.setattr(
        runtime_entry,
        "_load_credential_file",
        lambda *_args, **_kwargs: pytest.fail("credential read in validate-only"),
    )
    args = runtime_entry._parser().parse_args(
        (
            "--enable-three-setup-shadow-runtime",
            "--mode",
            "THREE_SETUP_SHADOW_RELEASE",
            "--validate-only",
            "--config-path",
            str(tmp_path / "absent.json"),
            "--release-manifest",
            str(tmp_path / "release.json"),
            "--staged-root",
            str(tmp_path),
            "--expected-release-sha",
            SHA,
            "--expected-release-tree",
            TREE,
            "--expected-manifest-digest",
            "c" * 64,
            "--pip-check-with",
            "python3.12",
        )
    )
    asyncio.run(runtime_entry._run(args))
    assert called == ["preflight"]


def test_normal_runtime_requires_credential_before_composition(tmp_path: Path) -> None:
    args = runtime_entry._parser().parse_args(
        (
            "--enable-three-setup-shadow-runtime",
            "--mode",
            "THREE_SETUP_SHADOW_RELEASE",
            "--config-path",
            str(tmp_path / "absent.json"),
        )
    )
    with pytest.raises(Exception, match="normal runtime requires notification credential"):
        asyncio.run(runtime_entry._run(args))


def _candidate_repo(
    root: Path, *, secret: bool = False, l0: bool = False
) -> tuple[str, str]:
    from scripts.verify_exact_release import REQUIRED_FILES

    root.mkdir()
    for relative in REQUIRED_FILES:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")
    config = root / "deploy/p4a/config/three-setup-shadow.json.example"
    config.write_bytes(
        canonical_json_bytes(
            {
                "schema": "trader-assist-v0/three-setup-production-config/v2",
                "release_sha": "REPLACE_WITH_EXACT_40_LOWERCASE_GIT_SHA",
                "e4_bar_types": [],
                "cost_model": {"version": "REPLACE_WITH_REVIEWED_COST_MODEL"},
            }
        )
    )
    if l0:
        config.write_bytes(
            (Path(__file__).parents[1] / config.relative_to(root)).read_bytes()
        )
    source = root / "src/demo.py"
    source.parent.mkdir()
    source.write_text(
        'api_key = "abcdefghijk"\n' if secret else "VALUE = 1\n",
        encoding="utf-8",
    )
    (root / "scripts/verify_exact_release.py").write_text(
        "import sys\n"
        "import demo\n"
        "assert '--verify-staged' in sys.argv\n"
        "assert '--expected-manifest-digest' in sys.argv\n"
        "print('EXACT_RELEASE_VERIFY=PASS')\n",
        encoding="utf-8",
    )
    (root / "scripts/three_setup_shadow_preflight.py").write_text(
        "import demo\nprint('HOST_PREFLIGHT_FIXTURE=PASS')\n", encoding="utf-8",
    )
    for command in (
        ("git", "init"),
        ("git", "config", "user.email", "ts7@example.invalid"),
        ("git", "config", "user.name", "TS7 Test"),
        ("git", "add", "."),
        ("git", "commit", "-m", "fixture"),
    ):
        subprocess.run(command, cwd=root, check=True, capture_output=True)
    sha = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=root, text=True).strip()
    tree = subprocess.check_output(("git", "rev-parse", "HEAD^{tree}"), cwd=root, text=True).strip()
    return sha, tree


def test_bundle_hashes_every_transfer_file_and_verifies_before_install(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "candidate"
    sha, tree = _candidate_repo(root)
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_17_x86_64.whl"
    wheel.write_bytes(b"wheel fixture")
    monkeypatch.setattr(bundle, "PILOT_WHEEL_SHA256", hashlib.sha256(b"wheel fixture").hexdigest())
    output = bundle.build_bundle(
        root=root,
        output=tmp_path / "bundle",
        sha=sha,
        tree=tree,
        wheel=wheel,
        bar_1m="BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
        bar_5m="BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
        cost_version="reviewed-cost-v1",
    )
    manifest = json.loads((output / "bundle-manifest.json").read_text())
    actual = {p.relative_to(output).as_posix() for p in output.rglob("*") if p.is_file()}
    assert {e["path"] for e in manifest["files"]} == actual - {"bundle-manifest.json"}
    for entry in manifest["files"]:
        path = output / entry["path"]
        assert entry["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    remote = (output / "remote-qualification.sh").read_text()
    subprocess.run(("bash", "-n", str(output / "remote-qualification.sh")), check=True)
    assert remote.index("BUNDLE_HASH_VERIFY=PASS") < remote.index("--host-only")
    assert remote.index("--host-only") < remote.index('[[ "${1}" == "--install" ]]')
    assert remote.index('[[ "${1}" == "--install" ]]') < remote.index("install -d")
    assert "SERVICE=STOPPED; ACTIVATION=DEFAULT_OFF" in remote
    assert "notification.json" not in "".join(actual)


def _qualification_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, str], dict[str, str]]:
    root = tmp_path / "candidate"
    sha, tree = _candidate_repo(root)
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_28_x86_64.whl"
    wheel.write_bytes(b"wheel fixture")
    monkeypatch.setattr(bundle, "PILOT_WHEEL_SHA256", hashlib.sha256(b"wheel fixture").hexdigest())
    output = bundle.build_bundle(
        root=root, output=tmp_path / "bundle", sha=sha, tree=tree, wheel=wheel,
        bar_1m="BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
        bar_5m="BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
        cost_version="reviewed-cost-v1",
    )
    anchors = bundle.handoff_anchors(output)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    python = bin_dir / "python3.12"
    python.write_text(f"#!/bin/sh\nexec {sys.executable} \"$@\"\n", encoding="utf-8")
    python.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    for key in ("PYTHONDONTWRITEBYTECODE", "PYTHONPYCACHEPREFIX", "PYTHONSAFEPATH"):
        env.pop(key, None)
    return output, anchors, env


def _run_qualification(
    output: Path, anchors: dict[str, str], env: dict[str, str], *,
    mode: str = "--verify", cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        (
            "bash", str(output / "remote-qualification.sh"), mode,
            anchors["EXPECTED_RELEASE_SHA"], anchors["EXPECTED_RELEASE_TREE"],
            anchors["EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"],
            anchors["EXPECTED_BUNDLE_MANIFEST_SHA256"],
        ),
        env=env, cwd=cwd, capture_output=True, text=True, check=False,
    )


def _bundle_snapshot(output: Path) -> dict[str, str]:
    return {
        path.relative_to(output).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in output.rglob("*") if path.is_file()
    }


def test_untrusted_startup_hook_cannot_run_before_path_set_rejection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, anchors, env = _qualification_fixture(tmp_path, monkeypatch)
    marker = tmp_path / "startup-hook-ran"
    (output / "sitecustomize.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    env["PYTHONPATH"] = str(output)
    result = _run_qualification(output, anchors, env, cwd=output)
    assert result.returncode != 0
    assert "transfer path set mismatch" in result.stderr
    assert not marker.exists(), "unverified Python startup hook executed"
    assert "BUNDLE_HASH_VERIFY=PASS" not in result.stdout


def test_successful_verify_and_denied_install_leave_bundle_byte_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, anchors, env = _qualification_fixture(tmp_path, monkeypatch)
    before = _bundle_snapshot(output)
    verified = _run_qualification(output, anchors, env)
    assert verified.returncode == 0, verified.stderr
    assert "STAGED_RELEASE_VERIFY=PASS" in verified.stdout
    assert "HOST_PREFLIGHT_FIXTURE=PASS" in verified.stdout
    assert _bundle_snapshot(output) == before
    assert not any(
        path.name == "__pycache__" or path.suffix == ".pyc"
        for path in output.rglob("*")
    )
    denied = _run_qualification(output, anchors, env, mode="--install")
    assert denied.returncode != 0
    assert "current deployment authorization is required" in denied.stderr
    assert "INSTALL_VERIFIED=PASS" not in denied.stdout
    assert _bundle_snapshot(output) == before
    assert not any(
        path.name == "__pycache__" or path.suffix == ".pyc"
        for path in output.rglob("*")
    )


def test_independent_anchors_accept_original_and_staged_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, anchors, env = _qualification_fixture(tmp_path, monkeypatch)
    manifest = json.loads((output / "release-manifest.json").read_bytes())
    verify_staged_release(
        output / "payload", manifest,
        expected_release_sha=anchors["EXPECTED_RELEASE_SHA"],
        expected_release_tree=anchors["EXPECTED_RELEASE_TREE"],
        expected_manifest_digest=anchors["EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"],
    )
    result = _run_qualification(output, anchors, env)
    assert result.returncode == 0, result.stderr
    assert result.stdout.index("BUNDLE_HASH_VERIFY=PASS") < result.stdout.index(
        "EXACT_RELEASE_VERIFY=PASS"
    ) < result.stdout.index("HOST_PREFLIGHT_FIXTURE=PASS")
    assert "PREINSTALL_VERIFY=PASS; SERVICE=STOPPED; ACTIVATION=DEFAULT_OFF" in result.stdout
    assert "INSTALL_VERIFIED" not in result.stdout
    denied = _run_qualification(output, anchors, env, mode="--install")
    assert denied.returncode != 0
    assert "current deployment authorization is required" in denied.stderr
    assert "INSTALL_VERIFIED" not in denied.stdout


@pytest.mark.parametrize(
    "mutation", ("coupled", "release_digest", "bundle_rewrite", "extra", "missing", "symlink")
)
def test_independent_anchor_and_transfer_mutations_fail_before_host_or_install(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str,
) -> None:
    output, anchors, env = _qualification_fixture(tmp_path, monkeypatch)
    manifest_path = output / "bundle-manifest.json"
    bundle_manifest = json.loads(manifest_path.read_bytes())
    payload_file = output / "payload/src/demo.py"
    if mutation in {"coupled", "bundle_rewrite"}:
        payload_file.write_text("VALUE = 2\n", encoding="utf-8")
        entry = next(e for e in bundle_manifest["files"] if e["path"] == "payload/src/demo.py")
        entry["sha256"] = hashlib.sha256(payload_file.read_bytes()).hexdigest()
        if mutation == "coupled":
            release_path = output / "release-manifest.json"
            release = json.loads(release_path.read_bytes())
            release_entry = next(e for e in release["files"] if e["path"] == "src/demo.py")
            release_entry["sha256"] = entry["sha256"]
            release["manifest_sha256"] = sha256_hex(canonical_json_bytes(
                {k: v for k, v in release.items() if k != "manifest_sha256"}
            ))
            release_path.write_bytes(canonical_json_bytes(release))
            bundle_manifest["release_manifest_digest"] = release["manifest_sha256"]
            release_bundle_entry = next(
                e for e in bundle_manifest["files"] if e["path"] == "release-manifest.json"
            )
            release_bundle_entry["sha256"] = hashlib.sha256(release_path.read_bytes()).hexdigest()
            release_bundle_entry["size"] = release_path.stat().st_size
        manifest_path.write_bytes(canonical_json_bytes(bundle_manifest))
    elif mutation == "release_digest":
        release_path = output / "release-manifest.json"
        release = json.loads(release_path.read_bytes())
        release["files"][0]["sha256"] = "0" * 64
        release_path.write_bytes(canonical_json_bytes(release))
    elif mutation == "extra":
        (output / "extra.txt").write_text("unlisted", encoding="utf-8")
    elif mutation == "missing":
        payload_file.unlink()
    else:
        payload_file.unlink()
        payload_file.symlink_to(output / "release-manifest.json")
    result = _run_qualification(output, anchors, env, mode="--install")
    assert result.returncode != 0
    assert "HOST_PREFLIGHT_FIXTURE=PASS" not in result.stdout
    assert "PREINSTALL_VERIFY=PASS" not in result.stdout
    assert "INSTALL_VERIFIED" not in result.stdout
    if mutation in {"coupled", "bundle_rewrite"}:
        assert "independent bundle-manifest digest mismatch" in result.stderr
    if mutation == "release_digest":
        assert "independent release-manifest canonical digest mismatch" in result.stderr


def test_remote_script_mutation_rejected_before_execution(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    output, anchors, env = _qualification_fixture(tmp_path, monkeypatch)
    remote = output / "remote-qualification.sh"
    remote.write_text("#!/bin/sh\necho UPLOADED_CODE_RAN\n", encoding="utf-8")
    # Model the runbook's trusted pre-execution raw SHA256 comparison.
    assert hashlib.sha256(remote.read_bytes()).hexdigest() != anchors[
        "EXPECTED_REMOTE_QUALIFICATION_SHA256"
    ]
    assert "UPLOADED_CODE_RAN" not in _run_preexecution_guard(output, anchors, env).stdout


def _run_preexecution_guard(
    output: Path, anchors: dict[str, str], env: dict[str, str],
) -> subprocess.CompletedProcess[str]:
    guard = (
        "import hashlib, os, subprocess, sys\n"
        "root = sys.argv[1]\n"
        "for name, expected in ((\"bundle-manifest.json\", sys.argv[2]), "
        "(\"remote-qualification.sh\", sys.argv[3])):\n"
        "    actual = hashlib.sha256(open(os.path.join(root, name), 'rb').read()).hexdigest()\n"
        "    if actual != expected: raise SystemExit(2)\n"
        "subprocess.run(['bash', os.path.join(root, 'remote-qualification.sh'), "
        "'--verify', *sys.argv[4:]], check=True)\n"
    )
    return subprocess.run(
        (sys.executable, "-c", guard, str(output),
         anchors["EXPECTED_BUNDLE_MANIFEST_SHA256"],
         anchors["EXPECTED_REMOTE_QUALIFICATION_SHA256"],
         anchors["EXPECTED_RELEASE_SHA"], anchors["EXPECTED_RELEASE_TREE"],
         anchors["EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"],
         anchors["EXPECTED_BUNDLE_MANIFEST_SHA256"]),
        env=env, capture_output=True, text=True, check=False,
    )


def test_bundle_rejects_secret_shaped_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "candidate"
    sha, tree = _candidate_repo(root, secret=True)
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_17_x86_64.whl"
    wheel.write_bytes(b"wheel fixture")
    monkeypatch.setattr(bundle, "PILOT_WHEEL_SHA256", hashlib.sha256(b"wheel fixture").hexdigest())
    with pytest.raises(bundle.BundleError, match="secret-shaped"):
        bundle.build_bundle(
            root=root,
            output=tmp_path / "bundle",
            sha=sha,
            tree=tree,
            wheel=wheel,
            bar_1m="BTC-PERP.HYPERLIQUID-1-MINUTE-LAST-EXTERNAL",
            bar_5m="BTC-PERP.HYPERLIQUID-5-MINUTE-LAST-EXTERNAL",
            cost_version="reviewed-cost-v1",
        )


def test_wrapper_preflight_and_default_off_unit_are_bound() -> None:
    root = Path(__file__).parents[1]
    wrapper = (root / "scripts/p4a/run_three_setup_shadow_runtime.sh").read_text()
    unit = (root / "deploy/p4a/systemd/trader-assist-v0-three-setup.service").read_text()
    assert wrapper.index("ACTIVATION_PERMIT") < wrapper.index("--expected-manifest-digest")
    assert wrapper.index("--expected-manifest-digest") < wrapper.index(
        'exec "${PYTHON_EXECUTABLE}"'
    )
    assert "--pip-check-with python3.12" in wrapper
    assert "Restart=no" in unit
    assert "ExecStart=/opt/trader-assist-v0/scripts/p4a/run_three_setup_shadow_runtime.sh" in unit


@pytest.mark.parametrize("failure", ("permit", "enable", "mode", "preflight"))
def test_wrapper_failures_cannot_start_runtime(
    tmp_path: Path,
    failure: str,
) -> None:
    root = Path(__file__).parents[1]
    script = (root / "scripts/p4a/run_three_setup_shadow_runtime.sh").read_text()
    install = tmp_path / "opt/trader-assist-v0"
    etc = tmp_path / "etc/trader-assist-v0"
    script = script.replace("/opt/trader-assist-v0", str(install))
    script = script.replace("/etc/trader-assist-v0", str(etc))
    wrapper = tmp_path / "wrapper.sh"
    wrapper.write_text(script, encoding="utf-8")
    wrapper.chmod(0o750)
    python = install / "venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(
        "#!/usr/bin/env bash\n"
        'echo "$1" >> "$TS7_TEST_LOG"\n'
        '[[ "${TS7_FAIL_PREFLIGHT:-}" != "1" || "$1" != *preflight.py ]]\n',
        encoding="utf-8",
    )
    python.chmod(0o750)
    for relative in (
        "scripts/run_three_setup_shadow_runtime.py",
        "scripts/three_setup_shadow_preflight.py",
        "three-setup-release-manifest.json",
    ):
        path = install / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("fixture", encoding="utf-8")
    etc.mkdir(parents=True)
    (etc / "three-setup-shadow.json").write_text("{}", encoding="utf-8")
    credential = tmp_path / "credentials"
    credential.mkdir()
    (credential / "notification.json").write_text("fixture", encoding="utf-8")
    if failure != "permit":
        (etc / "three-setup-activation-permit").write_text("fixture", encoding="utf-8")
    log = tmp_path / "calls.log"
    import os

    env = {
        **os.environ,
        "CREDENTIALS_DIRECTORY": str(credential),
        "TRADER_ASSIST_V0_THREE_SETUP_CONFIG_PATH": str(etc / "three-setup-shadow.json"),
        "TRADER_ASSIST_V0_THREE_SETUP_ENABLE": "0" if failure == "enable" else "1",
        "TRADER_ASSIST_V0_THREE_SETUP_MODE": (
            "DISABLED" if failure == "mode" else "THREE_SETUP_SHADOW_RELEASE"
        ),
        "TRADER_ASSIST_V0_THREE_SETUP_RELEASE_SHA": SHA,
        "TRADER_ASSIST_V0_THREE_SETUP_RELEASE_TREE": TREE,
        "TRADER_ASSIST_V0_THREE_SETUP_MANIFEST_DIGEST": "c" * 64,
        "TS7_TEST_LOG": str(log),
        "TS7_FAIL_PREFLIGHT": "1" if failure == "preflight" else "0",
    }
    result = subprocess.run(("bash", str(wrapper)), env=env, capture_output=True)
    assert result.returncode != 0
    calls = log.read_text().splitlines() if log.exists() else []
    if failure == "preflight":
        assert len(calls) == 1 and calls[0].endswith("three_setup_shadow_preflight.py")
    else:
        assert calls == []


@pytest.mark.parametrize("override", [None, "missing", "cost", "bar"])
def test_l0_bundle_retains_full_identity_without_cost_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, override: str | None,
) -> None:
    from datetime import UTC, datetime

    from scripts.build_multi_asset_registry_seed import build_launch_identity
    from scripts.e4_nautilus_public_data_probe import launch_bars
    from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
    from trader_assist_v0.multi_asset_shadow.production import THREE_SETUP_L0_CONFIG_SCHEMA
    from trader_assist_v0.multi_asset_shadow.resolution import (
        FIRST_LAUNCH_20,
        resolve_first_launch_20,
    )

    root = tmp_path / "candidate"
    sha, tree = _candidate_repo(root, l0=True)
    observed_at = datetime(2026, 9, 27, tzinfo=UTC)
    metadata = [
        {"universe": [{"name": r.coin, "szDecimals": 2, "maxLeverage": 10}
                      for r in FIRST_LAUNCH_20 if r.dex == dex]}
        for dex in ("MAIN", "xyz")
    ]
    resolutions = resolve_first_launch_20(
        perp_dexes=[{"name": "main"}, {"name": "xyz"}],
        all_perp_metas=metadata, observed_at=observed_at,
    )
    seed = RegistryVersion.create(
        version="l0", created_at=observed_at, markets=tuple(r.market for r in resolutions),
    )
    snapshot, manifest = build_launch_identity(
        seed=seed,
        instruments=[SimpleNamespace(raw_symbol=r.coin, id=f"{r.coin}.HYPERLIQUID")
                     for r in FIRST_LAUNCH_20],
        sha=sha, tree=tree, run_id="bundle-test", observed_at_ns=1_000_000_000,
        metadata_evidence={},
    )
    artifacts = tmp_path / "launch"
    (artifacts / "e4").mkdir(parents=True)
    for name, model in (("registry-seed.json", seed),
                        ("e4/run-manifest.json", manifest),
                        ("e4/pit-universe-snapshot.json", snapshot)):
        (artifacts / name).write_text(model.model_dump_json(), encoding="utf-8")
    bars = launch_bars(seed, snapshot)
    (artifacts / "bar-types.json").write_bytes(canonical_json_bytes(list(bars)))
    wheel = tmp_path / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_17_x86_64.whl"
    wheel.write_bytes(b"wheel fixture")
    monkeypatch.setattr(bundle, "PILOT_WHEEL_SHA256", hashlib.sha256(b"wheel fixture").hexdigest())
    arguments = dict(
        root=root, output=tmp_path / "bundle", sha=sha, tree=tree, wheel=wheel,
        bar_1m=bars[0] if override == "bar" else "", bar_5m="",
        cost_version="example-cost" if override == "cost" else "",
        launch_artifacts=None if override == "missing" else artifacts,
    )
    if override is not None:
        with pytest.raises(bundle.BundleError, match="complete generated|legacy bar-pair/cost"):
            bundle.build_bundle(**arguments)
        assert not (tmp_path / "bundle").exists()
        return
    output = bundle.build_bundle(**arguments)
    config = json.loads((output / "config/three-setup-shadow.json").read_bytes())
    assert config["schema"] == THREE_SETUP_L0_CONFIG_SCHEMA
    assert config["profile"] == "FIRST_LAUNCH_20_DATA_COLLECTION_ONLY"
    assert config["cost_model"] is None
    assert config["e4_bar_types"] == list(bars)
    assert len(set(config["e4_bar_types"])) == 40
    assert config["qualification_digest"] == "NOT_QUALIFIED"
    assert (output / "identity/e4/run-manifest.json").read_bytes()
    assert (output / "identity/e4/pit-universe-snapshot.json").read_bytes()
    env = (output / "config/three-setup-shadow.env").read_text()
    assert "TRADER_ASSIST_V0_THREE_SETUP_ENABLE=0" in env
    assert "TRADER_ASSIST_V0_THREE_SETUP_MODE=DISABLED" in env
    assert not any("notification.json" in str(path) for path in output.rglob("*"))


def test_l0_install_stages_identity_and_service_permissions_without_service_control():
    from scripts.build_three_setup_shadow_deployment_bundle import _remote_script

    script = _remote_script("exact-rc5.whl")
    assert "existing traderassist service identity is required" in script
    assert "existing durable state requires separately reviewed replacement" in script
    assert 'cp -a "$BUNDLE_ROOT/identity/."' in script
    assert "chown -R traderassist:traderassist" in script
    assert "chgrp -R traderassist /opt/trader-assist-v0" in script
    assert "install -m 0640 -g traderassist" in script
    for command in ("systemctl start", "systemctl restart", "systemctl enable",
                    "systemctl daemon-reload", "systemctl stop"):
        assert command not in script


def _load_replay_controller():
    import importlib.util

    path = Path(__file__).parents[1] / "scripts/p4a/run_e4_replay_diagnostic.py"
    spec = importlib.util.spec_from_file_location("run_e4_replay_diagnostic_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_replay_controller_frozen_systemd_contract(tmp_path: Path) -> None:
    controller = _load_replay_controller()
    replay_root = Path("/var/tmp/trade-os-replay-37566655478-1")
    stage_root = Path("/opt/trader-assist-v0-replay-only-37566655478-1")
    args = SimpleNamespace(
        replay_root=replay_root,
        stage_root=stage_root,
        staged_python=stage_root / "runtime-venv/bin/python3.12",
        verifier=stage_root / "bundle/payload/scripts/e4_nautilus_public_data_probe.py",
        native_log=Path("/var/lib/trader-assist-v0/e4/native.jsonl"),
        manifest=Path("/var/lib/trader-assist-v0/e4/run-manifest.json"),
        replay_facts=None,
        unit_name="trade-os-e4-replay-diagnostic.service",
        production_service="trader-assist-v0-three-setup.service",
        activation_permit=Path("/etc/trader-assist-v0/three-setup-activation-permit"),
    )
    properties = controller._systemd_properties(
        work=replay_root / "work",
        proof=replay_root / "proof",
        stage_root=stage_root,
        native_log=args.native_log,
        manifest=args.manifest,
        replay_facts=None,
    )
    assert {
        "ProtectSystem=strict",
        "ProtectHome=yes",
        "PrivateNetwork=yes",
        "PrivateDevices=yes",
        "NoNewPrivileges=yes",
        "CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_KILL",
        "MemoryMax=1280M",
        "TasksMax=16",
        "RuntimeMaxSec=2400s",
        "Restart=no",
        "PrivateTmp=no",
    }.issubset(set(properties))
    assert (
        f"TemporaryFileSystem={replay_root / 'work'}:"
        "size=768M,nosuid,nodev,noexec,mode=0770,uid=0,gid=988"
    ) in properties
    assert all(
        not any(value.startswith(name + "=") for value in properties)
        for name in controller.FORBIDDEN_SYSTEMD_PROPERTIES
    )
    command = controller.build_systemd_run_argv(
        args,
        {
            "mem_available_bytes": controller.PRESTART_MEMAVAILABLE_MIN_BYTES,
            "swap_counters": {"pswpin": 0, "pswpout": 0},
            "source_bindings": {},
        },
    )
    assert command[:6] == [
        "systemd-run",
        "--unit",
        args.unit_name,
        "--wait",
        "--collect",
        "--service-type=exec",
    ]
    assert "--execute-authorized-replay" in command
    assert controller.REPLAY_UID == 999
    assert controller.REPLAY_GID == 988
    assert controller.CHILD_DEADLINE_SECONDS == 1800
    assert controller.EVIDENCE_ALLOWANCE_SECONDS == 300
    assert controller.RUNTIME_MAX_SECONDS == 2400
    assert controller.WORK_TMPFS_MAX_BYTES == 768 * 1024 * 1024
    assert controller.CGROUP_MEMORY_MAX_BYTES == 1280 * 1024 * 1024
    assert controller.PRESTART_MEMAVAILABLE_MIN_BYTES == 1408 * 1024 * 1024
    assert controller.VERIFIER_HWM_MAX_BYTES == 256 * 1024 * 1024
    assert controller.TASKS_MAX == 16


def test_replay_controller_bounded_stream_retains_cap_and_hashes_full_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _load_replay_controller()
    monkeypatch.setattr(controller, "STREAM_RETAIN_MAX_BYTES", 32)
    payload = b"0123456789" * 20
    output = tmp_path / "child.log"
    capture = controller._BoundedCapture(io.BytesIO(payload), output)
    capture.start()
    capture.join()
    evidence = capture.payload()
    assert output.read_bytes() == payload[:32]
    assert evidence["byte_count"] == len(payload)
    assert evidence["retained_bytes"] == 32
    assert evidence["full_stream_sha256"] == hashlib.sha256(payload).hexdigest()
    assert evidence["truncation_marker"] == "TRUNCATED=YES"


def test_replay_controller_complete_surviving_work_inventory(tmp_path: Path) -> None:
    controller = _load_replay_controller()
    work = tmp_path / "work"
    nested = work / "verifier"
    nested.mkdir(parents=True)
    retained = nested / "scratch.sqlite"
    retained.write_bytes(b"retained-scratch")
    inventory = controller._work_inventory(work)
    entry = next(item for item in inventory["entries"] if item["path"] == "verifier/scratch.sqlite")
    assert entry["type"] == "regular"
    assert entry["size"] == len(b"retained-scratch")
    assert entry["sha256"] == hashlib.sha256(b"retained-scratch").hexdigest()
    assert inventory["regular_file_count"] == 1
    assert inventory["total_regular_file_bytes"] == len(b"retained-scratch")

    (work / "unexpected-link").symlink_to(retained)
    with pytest.raises(controller.ReplayControllerError, match="non-regular special entry"):
        controller._work_inventory(work)


def test_replay_controller_release_and_runbook_binding() -> None:
    from scripts.verify_exact_release import REQUIRED_FILES

    assert "scripts/p4a/run_e4_replay_diagnostic.py" in REQUIRED_FILES
    root = Path(__file__).parents[1]
    controller_source = (root / "scripts/p4a/run_e4_replay_diagnostic.py").read_text()
    for fragment in (
        "stdin=subprocess.DEVNULL",
        "close_fds=True",
        "shell=False",
        '"PYTHONDONTWRITEBYTECODE": "1"',
        '"PYTHONNOUSERSITE": "1"',
        '"TMPDIR": str(temp)',
        '"TMP": str(temp)',
        '"TEMP": str(temp)',
        '"HOME": str(home)',
        '"XDG_CACHE_HOME": str(cache)',
    ):
        assert fragment in controller_source
    runbook = (root / "docs/operations/THREE_SETUP_SHADOW_DEPLOYMENT.md").read_text()
    assert "scripts/p4a/run_e4_replay_diagnostic.py" in runbook
    assert "complete surviving-WORK inventory" in runbook
    assert "complete-WORK byte-copy contract is superseded" in runbook

@pytest.mark.parametrize("late_at", ("never", "pending_fsync", "pass_fsync"))
def test_replay_controller_a7_proof_deadline_final_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    late_at: str,
) -> None:
    controller = _load_replay_controller()
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "controller-result.json").write_text(
        json.dumps({"status": "REPLAY_DIAGNOSTIC_CHILD_COMPLETE", "blockers": []}),
        encoding="utf-8",
    )
    (proof / "child.stdout.log").write_bytes(b"already retained")
    clock = [200.0]
    monkeypatch.setattr(controller.time, "monotonic", lambda: clock[0])
    original_fsync = controller._fsync_dir

    def fsync_with_late_completion(directory: Path) -> None:
        original_fsync(directory)
        manifest_path = proof / "proof-manifest.json"
        if directory == proof and manifest_path.is_file():
            state = json.loads(manifest_path.read_bytes())["DURABLE_EVIDENCE_EXPORT"]
            if (late_at == "pending_fsync" and state == "PENDING") or (
                late_at == "pass_fsync" and state == "PASS"
            ):
                clock[0] = 301.0

    monkeypatch.setattr(controller, "_fsync_dir", fsync_with_late_completion)
    blockers: list[str] = []
    result = controller._finalize_proof(
        proof,
        export_status="PASS",
        blockers=blockers,
        source_binding={"original": True},
        source_identities={"controller": True},
        unit_properties={"bound": True},
        evidence_deadline=300.0,
    )
    durable = json.loads((proof / "proof-manifest.json").read_bytes())
    controller_result = json.loads((proof / "controller-result.json").read_bytes())
    assert result == durable
    assert (proof / "child.stdout.log").read_bytes() == b"already retained"
    if late_at == "never":
        assert durable["DURABLE_EVIDENCE_EXPORT"] == "PASS"
        assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" not in blockers
        return

    assert durable["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
    assert controller_result["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in blockers
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in durable["blockers"]
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in controller_result["blockers"]
    for item in durable["files"]:
        contents = (proof / item["path"]).read_bytes()
        assert item["sha256"] == hashlib.sha256(contents).hexdigest()
        assert item["size"] == len(contents)
    assert durable["post_fsync_readback_sha256_equality"] is True


@pytest.mark.parametrize("late", (False, True))
def test_replay_controller_a7_inside_unit_terminal_decision(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    late: bool,
) -> None:
    controller = _load_replay_controller()
    work, proof = tmp_path / "work", tmp_path / "proof"
    (work / "verifier").mkdir(parents=True)
    proof.mkdir(mode=0o750)
    for relative in (
        "verifier/replay-diagnostic.json",
        "verifier/replay-verifier-resources.json",
        "child.stdout.log",
        "child.stderr.log",
    ):
        (work / relative).write_text(relative, encoding="utf-8")

    # Simulated root/unit attributes only; no real systemd or verifier process.
    monkeypatch.setattr(controller.os, "geteuid", lambda: 0)
    original_lstat = controller.Path.lstat

    def fake_lstat(path: Path):
        if path == proof:
            return SimpleNamespace(st_uid=0, st_gid=0, st_mode=0o40750)
        return original_lstat(path)

    monkeypatch.setattr(controller.Path, "lstat", fake_lstat)
    expected = {"sha256": "bound"}
    preflight = {
        "source_identities": {"controller": expected, "verifier": expected},
        "mem_available_bytes": controller.PRESTART_MEMAVAILABLE_MIN_BYTES,
        "swap_counters": {"pswpin": 0, "pswpout": 0},
    }
    monkeypatch.setattr(controller, "_decode_internal", lambda _: preflight)
    monkeypatch.setattr(controller, "_systemd_properties", lambda **_: [])
    monkeypatch.setattr(controller, "_work_mount_evidence", lambda _: {})
    monkeypatch.setattr(controller, "_systemd_unit_evidence", lambda *_: {})
    monkeypatch.setattr(controller, "_source_bindings_from_host", lambda *_: {
        "native_log": expected, "manifest": expected,
    })
    monkeypatch.setattr(controller, "_file_binding", lambda _: expected)
    monkeypatch.setattr(controller, "_minimal_child_env", lambda _: {})
    monkeypatch.setattr(controller, "_run_credential_probe", lambda *_: {"probe": "PASS"})
    monkeypatch.setattr(controller, "_run_verifier_child", lambda *_: (
        {"returncode": 0, "timed_out": False}, 300.0,
    ))
    monkeypatch.setattr(controller, "_swap_counters", lambda: preflight["swap_counters"])
    clock = [200.0]
    monkeypatch.setattr(controller.time, "monotonic", lambda: clock[0])
    original_fsync = controller._fsync_dir

    def complete_fsync(directory: Path) -> None:
        original_fsync(directory)
        manifest_path = proof / "proof-manifest.json"
        if late and directory == proof and manifest_path.exists():
            if json.loads(manifest_path.read_bytes())["DURABLE_EVIDENCE_EXPORT"] == "PASS":
                clock[0] = 301.0

    monkeypatch.setattr(controller, "_fsync_dir", complete_fsync)
    args = SimpleNamespace(
        host_preflight="test", replay_root=tmp_path,
        stage_root=tmp_path / "stage", unit_name="synthetic-only",
        native_log=tmp_path / "native", manifest=tmp_path / "manifest",
        verifier=tmp_path / "verifier", replay_facts=None,
    )
    rc = controller._inside_unit(args)
    output = capsys.readouterr().out
    durable = json.loads((proof / "proof-manifest.json").read_bytes())
    result = json.loads((proof / "controller-result.json").read_bytes())
    if late:
        assert rc != 0
        assert "DURABLE_EVIDENCE_EXPORT=PASS" not in output
        assert durable["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
        assert result["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
        assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in durable["blockers"]
        for item in durable["files"]:
            data = (proof / item["path"]).read_bytes()
            assert item["sha256"] == hashlib.sha256(data).hexdigest()
    else:
        assert rc == 0
        assert "DURABLE_EVIDENCE_EXPORT=PASS" in output
        assert durable["DURABLE_EVIDENCE_EXPORT"] == "PASS"
    assert (proof / "replay-diagnostic.json").exists()
    assert (proof / "child.stdout.log").exists()


def test_replay_controller_a7_uncorrectable_published_pass_is_unproven(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _load_replay_controller()
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "controller-result.json").write_text('{"blockers":[]}', encoding="utf-8")
    clock = [200.0]
    monkeypatch.setattr(controller.time, "monotonic", lambda: clock[0])
    original_fsync = controller._fsync_dir
    original_replace = controller._write_json_replace

    def fsync_after_pass(directory: Path) -> None:
        original_fsync(directory)
        path = proof / "proof-manifest.json"
        if path.exists() and json.loads(path.read_bytes())["DURABLE_EVIDENCE_EXPORT"] == "PASS":
            clock[0] = 301.0

    def fail_correction(path: Path, value: object) -> bytes:
        if path.name == "controller-result.json":
            raise OSError("simulated corrective storage failure")
        return original_replace(path, value)

    monkeypatch.setattr(controller, "_fsync_dir", fsync_after_pass)
    monkeypatch.setattr(controller, "_write_json_replace", fail_correction)
    result = controller._finalize_proof(
        proof, export_status="PASS", blockers=[], source_binding=None,
        source_identities=None, unit_properties=None, evidence_deadline=300.0,
    )
    assert result["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
    assert result["REPLAY_EVIDENCE_RETENTION_UNPROVEN"] is True
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in result["blockers"]

def test_replay_controller_a7_last_post_fsync_readback_overrun(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    controller = _load_replay_controller()
    proof = tmp_path / "proof"
    proof.mkdir()
    (proof / "controller-result.json").write_text('{"blockers":[]}', encoding="utf-8")
    clock = [200.0]
    pass_fsync_count = [0]
    monkeypatch.setattr(controller.time, "monotonic", lambda: clock[0])
    real_fsync = controller._fsync_dir
    real_read = controller.Path.read_bytes
    manifest_path = proof / "proof-manifest.json"

    def recorded_fsync(directory: Path) -> None:
        real_fsync(directory)
        if manifest_path.exists() and directory == proof:
            if json.loads(real_read(manifest_path))["DURABLE_EVIDENCE_EXPORT"] == "PASS":
                pass_fsync_count[0] += 1

    def delayed_last_readback(path: Path) -> bytes:
        data = real_read(path)
        if path == manifest_path and pass_fsync_count[0] >= 2:
            clock[0] = 301.0
        return data

    monkeypatch.setattr(controller, "_fsync_dir", recorded_fsync)
    monkeypatch.setattr(controller.Path, "read_bytes", delayed_last_readback)
    result = controller._finalize_proof(
        proof, export_status="PASS", blockers=[], source_binding=None,
        source_identities=None, unit_properties=None, evidence_deadline=300.0,
    )
    assert pass_fsync_count[0] >= 2
    assert result["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in result["blockers"]
    final_manifest = json.loads(real_read(manifest_path))
    assert final_manifest["DURABLE_EVIDENCE_EXPORT"] == "FAIL"
    final_controller = json.loads(real_read(proof / "controller-result.json"))
    assert "DURABLE_EVIDENCE_ALLOWANCE_EXCEEDED" in final_controller["blockers"]
    for item in final_manifest["files"]:
        data = real_read(proof / item["path"])
        assert item["sha256"] == hashlib.sha256(data).hexdigest()
