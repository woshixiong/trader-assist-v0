"""Offline execution of the manual release builder's identity/transport seams.

The parser deliberately admits only this workflow's block YAML subset. Full
Actions schema and Linux/rc5/provider qualification remain GitHub obligations.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from scripts import build_three_setup_shadow_deployment_bundle as builder
from scripts.build_multi_asset_registry_seed import build_launch_identity
from scripts.e4_nautilus_public_data_probe import launch_bars
from tests.test_three_setup_shadow_launch_readiness import _candidate_repo
from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
from trader_assist_v0.multi_asset_shadow.resolution import FIRST_LAUNCH_20, resolve_first_launch_20

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/three-setup-release-bundle.yml"
SHA = "a79d7d5349b5f4dbb1143e43daf6eea1f75d81f3"
TREE = "c6e53c79158eb69e1fd62d2fe7389019f9524eb5"


def parse_workflow(source: str) -> dict[str, Any]:
    """Parse maps, lists of maps, simple scalars and literal blocks; reject extras."""
    lines = source.splitlines()

    def indentation(line: str) -> int:
        assert "\t" not in line
        return len(line) - len(line.lstrip(" "))

    def scalar(value: str) -> Any:
        if value.startswith(('"', "'")):
            result = ast.literal_eval(value)
            assert isinstance(result, str)
            return result
        assert value and not value.startswith(("&", "*", "!", "[", "{", ">", "|"))
        assert " #" not in value
        if value in ("true", "false"):
            return value == "true"
        return int(value) if re.fullmatch(r"[0-9]+", value) else value

    def parse(block: list[str], level: int) -> Any:
        block = [line for line in block if line.strip() and not line.lstrip().startswith("#")]
        assert block and indentation(block[0]) == level
        if block[0][level:].startswith("- "):
            items = []
            starts = [
                i
                for i, line in enumerate(block)
                if indentation(line) == level and line[level:].startswith("- ")
            ]
            assert starts[0] == 0
            for index, start in enumerate(starts):
                end = starts[index + 1] if index + 1 < len(starts) else len(block)
                first = " " * (level + 2) + block[start][level + 2 :]
                items.append(parse([first, *block[start + 1 : end]], level + 2))
            return items
        result = {}
        index = 0
        while index < len(block):
            line = block[index]
            assert indentation(line) == level
            match = re.fullmatch(r"([^:]+):(.*)", line[level:])
            assert match
            key = match[1].strip('"')
            assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key) and key not in result
            value = match[2].strip()
            end = index + 1
            while end < len(block) and indentation(block[end]) > level:
                end += 1
            children = block[index + 1 : end]
            if value == "|":
                assert children
                margin = level + 2
                assert all(indentation(child) >= margin for child in children)
                result[key] = "\n".join(child[margin:] for child in children) + "\n"
            elif value:
                assert not children
                result[key] = scalar(value)
            else:
                assert children
                result[key] = parse(children, level + 2)
            index = end
        return result

    return parse(lines, 0)


def steps() -> dict[str, dict[str, Any]]:
    return {
        step["id"]: step
        for step in parse_workflow(WORKFLOW.read_text())["jobs"]["build-release-bundle"]["steps"]
        if "id" in step
    }


def python_block(step_id: str) -> str:
    code = steps()[step_id]["run"]
    match = re.search(r"<<'PY'\n(.*?)\nPY\n", code, re.DOTALL)
    assert match
    compile(match[1], f"{step_id}-workflow", "exec")
    return match[1]


def shell_run(step_id: str, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-c", steps()[step_id]["run"]],
        cwd=cwd,
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def python_run(
    step_id: str, env: dict[str, str], code: str | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-B", "-c", code or python_block(step_id)],
        cwd=ROOT,
        env={
            **os.environ,
            "PYTHONPATH": f"{ROOT}/src:{ROOT}",
            "PYTHONDONTWRITEBYTECODE": "1",
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
    )


def assert_pass(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def git(path: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(path), *args], text=True, stderr=subprocess.DEVNULL
    ).strip()


def test_structure_and_authority() -> None:
    workflow = parse_workflow(WORKFLOW.read_text())
    assert set(workflow) == {"name", "on", "permissions", "jobs"}
    assert workflow["permissions"] == {"contents": "read"}
    assert set(workflow["on"]) == {"workflow_dispatch"}
    inputs = workflow["on"]["workflow_dispatch"]["inputs"]
    assert set(inputs) == {"release_sha", "release_tree"}
    for name, value in [("release_sha", SHA), ("release_tree", TREE)]:
        assert inputs[name]["default"] == value
        assert inputs[name]["required"] is True and inputs[name]["type"] == "string"
    assert set(workflow["jobs"]) == {"build-release-bundle"}
    job = workflow["jobs"]["build-release-bundle"]
    assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == 30
    assert set(job) == {"runs-on", "timeout-minutes", "defaults", "env", "steps"}
    assert job["defaults"] == {"run": {"shell": "bash"}}
    assert job["env"]["RELEASE_SHA"] == SHA and job["env"]["RELEASE_TREE"] == TREE
    assert job["env"]["CONTROL_HEAD"] == "${{ github.sha }}"
    assert "/release/src:" in job["env"]["PYTHONPATH"]
    actions = [step for step in job["steps"] if "uses" in step]
    assert [action["uses"] for action in actions] == [
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    ]
    for action, path, ref in zip(
        actions[:2],
        ["control", "release"],
        ["${{ github.sha }}", "${{ env.RELEASE_SHA }}"],
        strict=True,
    ):
        assert action["with"] == {
            "path": path,
            "ref": ref,
            "fetch-depth": 0,
            "persist-credentials": False,
        }
    assert actions[2]["with"] == {"python-version": "3.12"}
    upload = actions[-1]
    assert upload == job["steps"][-1] and "if" not in upload
    assert upload["with"] == {
        "name": (
            "three-setup-release-${{ env.RELEASE_SHA }}-"
            "${{ github.run_id }}-${{ github.run_attempt }}"
        ),
        "path": "${{ env.BUILD_ROOT }}/three-setup-release-bundle.tar.gz",
        "if-no-files-found": "error",
        "compression-level": 0,
        "retention-days": 14,
    }
    executable = "\n".join(step["run"] for step in job["steps"] if "run" in step)
    for prohibited in (
        "secrets.",
        "GH_TOKEN",
        "ssh ",
        "scp ",
        "sftp ",
        "sudo ",
        "aws ",
        "systemctl ",
        "--install",
        "--qualify-l0",
        "LiveNode",
        "eval ",
        "source ",
        "continue-on-error",
        "pip install -e",
        "ls-remote",
    ):
        assert prohibited not in executable
    assert "${{" not in executable
    dependencies = steps()["dependencies"]["run"]
    for required in (
        "--require-hashes",
        "--no-deps --only-binary=:all:",
        "release/requirements-dev.lock",
        "release/requirements-nautilus-pilot.lock",
        "--verify-pilot-installed",
        "-m pip check",
        "PILOT_WHEEL_SHA256",
        "verify_host_prerequisites(wheel)",
        "version('nautilus-trader') == '2.0.0rc5'",
        "platform.system() == 'Linux'",
        "platform.machine() == 'x86_64'",
        "sys.version_info[:2] == (3, 12)",
        "package-source",
    ):
        assert required in dependencies
    # Every embedded Python block must parse, and every shell step must parse in bash.
    for step in job["steps"]:
        if "run" in step:
            assert_pass(
                subprocess.run(
                    ["bash", "-n"], input=step["run"], capture_output=True, text=True, check=False
                )
            )
            for code in re.findall(r"<<'PY'\n(.*?)\nPY\n", step["run"], re.DOTALL):
                compile(code, step["name"], "exec")


@pytest.mark.parametrize(
    "mutation",
    ["short", "uppercase", "wrong_sha", "wrong_tree", "short_tree", "malformed_tree", "injection"],
)
def test_dispatch_input_rejection(tmp_path: Path, mutation: str) -> None:
    env = {
        "RELEASE_SHA": SHA,
        "RELEASE_TREE": TREE,
        "INPUT_RELEASE_SHA": SHA,
        "INPUT_RELEASE_TREE": TREE,
    }
    assert_pass(shell_run("inputs", tmp_path, env))
    if mutation in ("wrong_tree", "short_tree", "malformed_tree"):
        env["INPUT_RELEASE_TREE"] = {
            "wrong_tree": "b" * 40,
            "short_tree": TREE[:12],
            "malformed_tree": "z" * 40,
        }[mutation]
    else:
        env["INPUT_RELEASE_SHA"] = {
            "short": SHA[:12],
            "uppercase": SHA.upper(),
            "wrong_sha": "a" * 40,
            "injection": "$(touch injected)",
        }[mutation]
    assert shell_run("inputs", tmp_path, env).returncode != 0
    assert not (tmp_path / "injected").exists()


@pytest.mark.parametrize("mutation", ["sha", "tree", "dirty", "untracked", "control"])
def test_checkout_drift_rejection(tmp_path: Path, mutation: str) -> None:
    sha, tree = _candidate_repo(tmp_path / "release")
    control, _ = _candidate_repo(tmp_path / "control")
    env = {"RELEASE_SHA": sha, "RELEASE_TREE": tree, "CONTROL_HEAD": control}
    assert_pass(shell_run("identity", tmp_path, env))
    if mutation == "sha":
        env["RELEASE_SHA"] = "a" * 40
    elif mutation == "tree":
        env["RELEASE_TREE"] = "b" * 40
    elif mutation == "control":
        env["CONTROL_HEAD"] = "c" * 40
    elif mutation == "dirty":
        (tmp_path / "release/src/demo.py").write_text("CHANGED = 1\n")
    else:
        (tmp_path / "release/untracked").touch()
    assert shell_run("identity", tmp_path, env).returncode != 0


@pytest.fixture
def bundle_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Use the real L0 builders and existing minimal clean-source fixture."""
    release = tmp_path / "release"
    sha, tree = _candidate_repo(release, l0=True)
    control, _ = _candidate_repo(tmp_path / "control")
    # Make the control identity distinct even when fixture commits share a second.
    (tmp_path / "control/control-only").write_text("CONTROL\n")
    git(tmp_path / "control", "add", ".")
    git(tmp_path / "control", "commit", "-m", "later control")
    control = git(tmp_path / "control", "rev-parse", "HEAD")
    assert control != sha
    observed = datetime(2026, 9, 27, tzinfo=UTC)
    metadata = [
        {
            "universe": [
                {"name": request.coin, "szDecimals": 2, "maxLeverage": 10}
                for request in FIRST_LAUNCH_20
                if request.dex == dex
            ]
        }
        for dex in ("MAIN", "xyz")
    ]
    resolutions = resolve_first_launch_20(
        perp_dexes=[{"name": "main"}, {"name": "xyz"}],
        all_perp_metas=metadata,
        observed_at=observed,
    )
    seed = RegistryVersion.create(
        version="l0", created_at=observed, markets=tuple(item.market for item in resolutions)
    )
    snapshot, manifest = build_launch_identity(
        seed=seed,
        instruments=[
            SimpleNamespace(raw_symbol=r.coin, id=f"{r.coin}.HYPERLIQUID") for r in FIRST_LAUNCH_20
        ],
        sha=sha,
        tree=tree,
        run_id="l0-test",
        observed_at_ns=1_000_000_000,
        metadata_evidence={},
    )
    root = tmp_path / "build"
    launch = root / "launch"
    (launch / "e4").mkdir(parents=True)
    for name, model in [
        ("registry-seed.json", seed),
        ("e4/run-manifest.json", manifest),
        ("e4/pit-universe-snapshot.json", snapshot),
    ]:
        (launch / name).write_text(model.model_dump_json())
    (launch / "bar-types.json").write_bytes(canonical_json_bytes(list(launch_bars(seed, snapshot))))
    wheel = root / "nautilus_trader-2.0.0rc5-cp312-cp312-manylinux_2_28_x86_64.whl"
    wheel.write_bytes(b"wheel fixture")
    monkeypatch.setattr(
        builder, "PILOT_WHEEL_SHA256", hashlib.sha256(wheel.read_bytes()).hexdigest()
    )
    output = builder.build_bundle(
        root=release,
        output=root / "bundle",
        sha=sha,
        tree=tree,
        wheel=wheel,
        bar_1m="",
        bar_5m="",
        launch_artifacts=launch,
    )
    anchors = builder.handoff_anchors(output)
    (root / "builder-stdout.txt").write_text(
        "THREE_SETUP_BUNDLE=fixture\n"
        + "".join(f"{key}={value}\n" for key, value in anchors.items())
    )
    return {
        "BUILD_ROOT": str(root),
        "RELEASE_SHA": sha,
        "RELEASE_TREE": tree,
        "CONTROL_HEAD": control,
        "GITHUB_WORKSPACE": str(tmp_path),
        "GITHUB_WORKFLOW_REF": f"woshixiong/trader-assist-v0/workflow@{control}",
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "GITHUB_STEP_SUMMARY": str(tmp_path / "summary"),
    }


@pytest.mark.parametrize(
    "mutation", ["none", "missing", "duplicate", "extra", "malformed", "sha", "digest"]
)
def test_actual_anchor_capture(bundle_fixture: dict[str, str], mutation: str) -> None:
    env = bundle_fixture
    stdout = Path(env["BUILD_ROOT"]) / "builder-stdout.txt"
    lines = stdout.read_text().splitlines()
    if mutation == "missing":
        lines.pop()
    elif mutation == "duplicate":
        lines.append(lines[-1])
    elif mutation == "extra":
        lines.append("EXPECTED_UNAUTHORIZED=" + "a" * 64)
    elif mutation == "malformed":
        lines[-1] = lines[-1].split("=")[0] + "=bad"
    elif mutation == "sha":
        env["RELEASE_SHA"] = env["CONTROL_HEAD"]
    elif mutation == "digest":
        lines[-1] = lines[-1].split("=")[0] + "=" + "a" * 64
    stdout.write_text("\n".join(lines) + "\n")
    result = python_run("anchors", env)
    if mutation == "none":
        assert_pass(result)
        assert env["RELEASE_SHA"] in (Path(env["BUILD_ROOT"]) / "handoff/anchors.env").read_text()
    else:
        assert result.returncode != 0


def test_real_bundle_archive_round_trip_and_control_separation(
    bundle_fixture: dict[str, str],
) -> None:
    env = bundle_fixture
    assert_pass(shell_run("identity", Path(env["GITHUB_WORKSPACE"]), env))
    assert_pass(python_run("anchors", env))
    assert_pass(python_run("transport", env))
    root = Path(env["BUILD_ROOT"])
    archive = root / "three-setup-release-bundle.tar.gz"
    assert archive.read_bytes()[4:8] == bytes(4)  # gzip mtime is normalized
    with tarfile.open(archive) as tar:
        assert tar.getmember("bundle/remote-qualification.sh").mode == 0o750
        assert not any(".git" in member.name.split("/") for member in tar.getmembers())
        assert (
            sum(
                member.isfile() and member.name.startswith("handoff/")
                for member in tar.getmembers()
            )
            == 2
        )
    original = (root / "bundle/remote-qualification.sh").read_bytes()
    assert (root / "round-trip/bundle/remote-qualification.sh").read_bytes() == original
    archive_bytes = archive.read_bytes()
    archive.unlink()
    shutil.rmtree(root / "round-trip")
    assert_pass(python_run("transport", env))
    assert archive.read_bytes() == archive_bytes
    assert_pass(shell_run("terminal", Path(env["GITHUB_WORKSPACE"]), env))
    summary = Path(env["GITHUB_STEP_SUMMARY"]).read_text()
    assert f"CONTROL_HEAD={env['CONTROL_HEAD']}" in summary
    assert f"EXPECTED_RELEASE_SHA={env['RELEASE_SHA']}" in summary
    assert env["CONTROL_HEAD"] != env["RELEASE_SHA"]
    assert "Artifact PASS grants no deployment/runtime/service authority." in summary
    assert git(Path(env["GITHUB_WORKSPACE"]) / "release", "status", "--porcelain") == ""


@pytest.mark.parametrize(
    "mutation",
    [
        "extra",
        "changed",
        "symlink",
        "mode",
        "enabled",
        "qualified",
        "cost",
        "secret",
        "permit",
        "traversal",
    ],
)
def test_actual_transport_rejects_unsafe_bundle(
    bundle_fixture: dict[str, str], mutation: str
) -> None:
    env = bundle_fixture
    assert_pass(python_run("anchors", env))
    root = Path(env["BUILD_ROOT"])
    bundle = root / "bundle"
    manifest_path = bundle / "bundle-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if mutation == "extra":
        (bundle / "extra").touch()
    elif mutation == "changed":
        (bundle / "remote-qualification.sh").write_text("changed")
    elif mutation == "symlink":
        (bundle / "link").symlink_to(bundle / "remote-qualification.sh")
    elif mutation == "mode":
        (bundle / "remote-qualification.sh").chmod(0o640)
    elif mutation in ("enabled", "qualified", "cost"):
        if mutation == "enabled":
            path = bundle / "config/three-setup-shadow.env"
            path.write_text(path.read_text().replace("ENABLE=0", "ENABLE=1"))
        else:
            path = bundle / "config/three-setup-shadow.json"
            config = json.loads(path.read_bytes())
            config["qualification_digest" if mutation == "qualified" else "cost_model"] = "unsafe"
            path.write_bytes(canonical_json_bytes(config))
        # Rehash to exercise default-off checks rather than only integrity rejection.
        entry = next(
            item
            for item in manifest["files"]
            if item["path"] == path.relative_to(bundle).as_posix()
        )
        entry.update(size=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        manifest_path.write_bytes(canonical_json_bytes(manifest))
    elif mutation == "secret":
        (root / "handoff/provenance.json").write_text('{"api_key":"abcdefghijk"}')
    elif mutation == "permit":
        (bundle / "three-setup-activation-permit").touch()
    elif mutation == "traversal":
        manifest["files"][0]["path"] = "../escape"
        manifest_path.write_bytes(canonical_json_bytes(manifest))
    assert python_run("transport", env).returncode != 0


@pytest.mark.parametrize("mutation", ["extra", "traversal", "symlink", "mode", "bytes"])
def test_actual_archive_member_validation(bundle_fixture: dict[str, str], mutation: str) -> None:
    env = bundle_fixture
    assert_pass(python_run("anchors", env))
    # Inject corruption between writer and reader; execute the real reader unchanged.
    code = python_block("transport")
    injected = (
        "\nwith tarfile.open(archive_path, 'r:gz') as a:\n"
        "    members = [(m, a.extractfile(m).read() if m.isfile() else None) "
        "for m in a.getmembers()]\n"
    )
    if mutation == "extra":
        injected += "m = tarfile.TarInfo('extra'); m.size = 1; members.append((m, b'x'))\n"
    elif mutation == "traversal":
        injected += "members[0][0].name = '../escape'\n"
    elif mutation == "symlink":
        injected += (
            "members[0][0].type = tarfile.SYMTYPE; members[0][0].linkname = '/tmp/outside'\n"
        )
    elif mutation == "bytes":
        injected += (
            "index = next(i for i, (m, _) in enumerate(members) if m.isfile())\n"
            "m, data = members[index]; members[index] = (m, b'x' * len(data))\n"
        )
    else:
        injected += (
            "next(m for m, _ in members if m.name == "
            "'bundle/remote-qualification.sh').mode = 0o640\n"
        )
    injected += (
        "import io\nwith tarfile.open(archive_path, 'w:gz') as a:\n"
        "    for m, data in members:\n"
        "        a.addfile(m, io.BytesIO(data) if data is not None else None)\n"
    )
    code = code.replace(
        "extracted = root / 'round-trip'", injected + "\nextracted = root / 'round-trip'"
    )
    assert python_run("transport", env, code).returncode != 0


def test_only_release_builders_are_called_and_failure_is_not_masked(tmp_path: Path) -> None:
    env = {
        "BUILD_ROOT": str(tmp_path / "build"),
        "GITHUB_WORKSPACE": str(tmp_path),
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
        "RELEASE_SHA": SHA,
        "RELEASE_TREE": TREE,
    }
    root = Path(env["BUILD_ROOT"])
    (root / "venv/bin").mkdir(parents=True)
    (root / "venv/bin/python").symlink_to(sys.executable)
    (root / "wheels").mkdir()
    (root / "wheels/fixture.whl").touch()
    for checkout in ("control", "release"):
        script_dir = tmp_path / checkout / "scripts"
        script_dir.mkdir(parents=True)
        for name in (
            "build_multi_asset_registry_seed.py",
            "build_three_setup_shadow_deployment_bundle.py",
        ):
            script = script_dir / name
            if checkout == "control":
                script.write_text("raise RuntimeError('CONTROL BUILDER MUST NEVER RUN')\n")
            else:
                script.write_text(
                    "import json, os, sys\nfrom pathlib import Path\n"
                    "with (Path(os.environ['BUILD_ROOT'])/'argv.jsonl').open('a') as f:\n"
                    '    f.write(json.dumps(sys.argv) + "\\n")\n'
                )
    assert_pass(shell_run("builders", tmp_path, env))
    calls = [json.loads(line) for line in (root / "argv.jsonl").read_text().splitlines()]
    assert len(calls) == 2 and all("/release/scripts/" in call[0] for call in calls)
    for call in calls:
        assert call[call.index("--expected-sha") + 1] == SHA
        assert call[call.index("--expected-tree") + 1] == TREE
        assert "--bar-type-1m" not in call and "--cost-model-version" not in call
    assert calls[0][calls[0].index("--launch-output") + 1] == str(root / "launch")
    assert calls[1][calls[1].index("--launch-artifacts") + 1] == str(root / "launch")
    (tmp_path / "release/scripts/build_three_setup_shadow_deployment_bundle.py").write_text(
        "raise SystemExit(9)\n"
    )
    assert shell_run("builders", tmp_path, env).returncode == 9


def test_docs_preserve_transport_and_gates() -> None:
    for relative in (
        "docs/operations/THREE_SETUP_SHADOW_DEPLOYMENT.md",
        "governance/FINALSHELL_TARGET_HOST_DEPLOYMENT_WORKFLOW_V1_2026-08-26.md",
    ):
        text = (ROOT / relative).read_text()
        for required in (
            "FinalShell",
            "0750",
            "Artifact PASS grants no deployment/runtime/service authority",
            "Intel Mac",
            "control HEAD",
        ):
            assert required in text
    operations = (ROOT / "docs/operations/THREE_SETUP_SHADOW_DEPLOYMENT.md").read_text()
    for required in (
        SHA,
        TREE,
        "gh run download",
        "NOT_QUALIFIED",
        "cost_model: null",
        "four independent",
        "separate current deployment authorization",
        "separate service-start authorization",
        "3_600_000_000_000",
    ):
        assert required in operations


@pytest.mark.parametrize("source", ["name: first\nname: second\n", "name: &alias forbidden\n"])
def test_restricted_yaml_rejects_duplicate_keys_and_aliases(source: str) -> None:
    with pytest.raises(AssertionError):
        parse_workflow(source)
