#!/usr/bin/env python3
"""Prepare one non-secret, exact-release FinalShell transfer folder; never deploy it."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import cast

from scripts.check_dependency_lock import PILOT_WHEEL_SHA256
from scripts.verify_exact_release import (
    build_release_manifest,
    exact_clean_head,
    exact_clean_tree,
    release_paths,
)
from trader_assist_v0.contracts.common import canonical_json_bytes
from trader_assist_v0.multi_asset_shadow.production import (
    THREE_SETUP_E4_CONFIG_SCHEMA,
    THREE_SETUP_L0_CONFIG_SCHEMA,
    ThreeSetupProductionConfig,
)


class BundleError(ValueError):
    """The transfer folder cannot represent one safe exact candidate."""


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


SECRET_VALUE = re.compile(
    rb"(?i)(?:api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"\r\n]{8,}['\"]"
)


def _reject_secret(path: Path) -> None:
    if path.suffix in {".py", ".sh", ".json", ".example", ".md", ".toml"}:
        data = path.read_bytes()
        if (
            (b"-----BEGIN " + b"PRIVATE KEY-----\n") in data
            or (b"https://discord.com/api/" + b"webhooks/") in data
            or SECRET_VALUE.search(data)
        ):
            raise BundleError(f"secret-shaped content in release file: {path.name}")


def _remote_script(wheel_name: str) -> str:
    script = '''#!/usr/bin/env bash
set -euo pipefail
[[ "${1:-}" == "--verify" || "${1:-}" == "--install" ]] || {
  echo "Use --verify or --install" >&2; exit 2;
}
[[ "$#" == 5 ]] || { echo "four independent anchors are required" >&2; exit 2; }
export EXPECTED_RELEASE_SHA="$2"
export EXPECTED_RELEASE_TREE="$3"
export EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST="$4"
export EXPECTED_BUNDLE_MANIFEST_SHA256="$5"
BUNDLE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
export BUNDLE_ROOT
python3.12 -I -B - <<'PY_VERIFY'
import hashlib, json, os, re, stat
from pathlib import Path
from typing import cast
root = Path(os.environ['BUNDLE_ROOT'])
sha = os.environ['EXPECTED_RELEASE_SHA']
tree = os.environ['EXPECTED_RELEASE_TREE']
release_digest = os.environ['EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST']
bundle_digest = os.environ['EXPECTED_BUNDLE_MANIFEST_SHA256']
if not all(re.fullmatch(r'[0-9a-f]{40}', value) for value in (sha, tree)) or not all(
    re.fullmatch(r'[0-9a-f]{64}', value) for value in (release_digest, bundle_digest)
):
    raise SystemExit('invalid independent anchor format')
def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
def regular(path):
    if not stat.S_ISREG(path.lstat().st_mode):
        raise SystemExit('non-regular transfer file')
    return path.read_bytes()
manifest_bytes = regular(root / 'bundle-manifest.json')
if hashlib.sha256(manifest_bytes).hexdigest() != bundle_digest:
    raise SystemExit('independent bundle-manifest digest mismatch')
manifest = json.loads(manifest_bytes)
if (manifest['release_sha'] != sha or manifest['release_tree'] != tree
        or manifest['release_manifest_digest'] != release_digest):
    raise SystemExit('independent release identity mismatch')
release_bytes = regular(root / 'release-manifest.json')
release = json.loads(release_bytes)
if canonical(release) != release_bytes:
    raise SystemExit('release manifest is not canonical')
actual_digest = hashlib.sha256(canonical({
    key: value for key, value in release.items() if key != 'manifest_sha256'
})).hexdigest()
if actual_digest != release_digest or release.get('manifest_sha256') != release_digest:
    raise SystemExit('independent release-manifest canonical digest mismatch')
if release.get('release_sha') != sha or release.get('release_tree') != tree:
    raise SystemExit('release manifest SHA/TREE mismatch')
listed = set()
for entry in manifest['files']:
    if set(entry) != {'path', 'sha256', 'size'} or not isinstance(entry['path'], str):
        raise SystemExit('invalid bundle entry')
    name = entry['path']
    if (not name or name.startswith('/') or chr(92) in name
            or any(part in ('', '.', '..') for part in name.split('/'))
            or name in listed or name == 'bundle-manifest.json'):
        raise SystemExit('unsafe or duplicate bundle path')
    listed.add(name)
    path = root / name
    data = regular(path)
    if (type(entry['size']) is not int or len(data) != entry['size']
            or not re.fullmatch(r'[0-9a-f]{64}', entry['sha256'])
            or hashlib.sha256(data).hexdigest() != entry['sha256']):
        raise SystemExit('bundle file hash or size mismatch')
actual = set()
def walk_error(error):
    raise SystemExit(f'cannot traverse transfer: {error}')
for directory, dirs, files in os.walk(root, followlinks=False, onerror=walk_error):
    for name in dirs:
        if not stat.S_ISDIR((Path(directory) / name).lstat().st_mode):
            raise SystemExit('symlink or non-directory in transfer')
    for name in files:
        path = Path(directory) / name
        regular(path)
        actual.add(path.relative_to(root).as_posix())
if actual != listed | {'bundle-manifest.json'}:
    raise SystemExit('transfer path set mismatch')
print('BUNDLE_HASH_VERIFY=PASS')
PY_VERIFY
PYTHONPATH="$BUNDLE_ROOT/payload/src:$BUNDLE_ROOT/payload" python3.12 -B \
  "$BUNDLE_ROOT/payload/scripts/verify_exact_release.py" \
  --root "$BUNDLE_ROOT/payload" --verify-staged "$BUNDLE_ROOT/release-manifest.json" \
  --expected-release-sha "$EXPECTED_RELEASE_SHA" \
  --expected-release-tree "$EXPECTED_RELEASE_TREE" \
  --expected-manifest-digest "$EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"
echo "STAGED_RELEASE_VERIFY=PASS"
SERVICE_STATE="$(systemctl is-active trader-assist-v0-three-setup.service 2>/dev/null || true)"
[[ "$SERVICE_STATE" != "active" ]] || {
  echo "Three Setup service is active" >&2; exit 2;
}
[[ ! -e /etc/trader-assist-v0/three-setup-activation-permit ]] || {
  echo "activation permit exists" >&2; exit 2;
}
PYTHONPATH="$BUNDLE_ROOT/payload/src:$BUNDLE_ROOT/payload" python3.12 -B \
  "$BUNDLE_ROOT/payload/scripts/three_setup_shadow_preflight.py" --host-only \
  --host-wheel "$BUNDLE_ROOT/__WHEEL_NAME__"
echo "PREINSTALL_VERIFY=PASS; SERVICE=STOPPED; ACTIVATION=DEFAULT_OFF"
[[ "${1}" == "--install" ]] || exit 0
[[ "${TRADER_ASSIST_V0_DEPLOYMENT_AUTHORIZED:-}" == "YES" ]] || {
  echo "current deployment authorization is required" >&2; exit 2;
}
[[ ! -e /opt/trader-assist-v0 ]] || {
  echo "existing install requires separate rollback handling" >&2; exit 2;
}
[[ ! -e /etc/trader-assist-v0/three-setup-shadow.json ]] || {
  echo "existing config requires separate rollback handling" >&2; exit 2;
}
[[ ! -e /etc/trader-assist-v0/three-setup-shadow.env ]] || {
  echo "existing env requires separate rollback handling" >&2; exit 2;
}
id traderassist >/dev/null 2>&1 || {
  echo "existing traderassist service identity is required" >&2; exit 2;
}
getent group traderassist >/dev/null || {
  echo "existing traderassist group is required" >&2; exit 2;
}
if [[ -d "$BUNDLE_ROOT/identity" ]]; then
  [[ ! -e /var/lib/trader-assist-v0/three-setup-shadow ]] || {
    echo "existing durable state requires separately reviewed replacement" >&2; exit 2;
  }
fi
install -d -m 0750 -g traderassist /opt/trader-assist-v0
cp -a "$BUNDLE_ROOT/payload/." /opt/trader-assist-v0/
cp "$BUNDLE_ROOT/release-manifest.json" /opt/trader-assist-v0/three-setup-release-manifest.json
install -d -m 0750 -g traderassist /etc/trader-assist-v0
install -m 0640 -g traderassist "$BUNDLE_ROOT/config/three-setup-shadow.json" \
  /etc/trader-assist-v0/three-setup-shadow.json
install -m 0640 -g traderassist "$BUNDLE_ROOT/config/three-setup-shadow.env" \
  /etc/trader-assist-v0/three-setup-shadow.env
python3.12 -m venv --without-pip /opt/trader-assist-v0/venv
python3.12 -m pip --python /opt/trader-assist-v0/venv install --require-hashes \
  -r /opt/trader-assist-v0/requirements-runtime.lock
python3.12 -m pip --python /opt/trader-assist-v0/venv install --require-hashes \
  --no-deps --only-binary=:all: --no-index --find-links "$BUNDLE_ROOT" \
  -r /opt/trader-assist-v0/requirements-nautilus-pilot.lock
chgrp -R traderassist /opt/trader-assist-v0
chmod -R g+rX /opt/trader-assist-v0
if [[ -d "$BUNDLE_ROOT/identity" ]]; then
  install -d -m 0750 -o traderassist -g traderassist \
    /var/lib/trader-assist-v0/three-setup-shadow
  cp -a "$BUNDLE_ROOT/identity/." /var/lib/trader-assist-v0/three-setup-shadow/
  chown -R traderassist:traderassist /var/lib/trader-assist-v0/three-setup-shadow
fi
install -m 0644 /opt/trader-assist-v0/deploy/p4a/systemd/trader-assist-v0-three-setup.service \
  /etc/systemd/system/trader-assist-v0-three-setup.service
# Unit installation does not reload, start, restart or enable the service.
export PYTHONPATH=/opt/trader-assist-v0/src:/opt/trader-assist-v0
/opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/check_dependency_lock.py \
  --verify-target-runtime-installed --staged-source /opt/trader-assist-v0/src \
  --pip-check-with "$(command -v python3.12)"
echo "INSTALL_VERIFIED=PASS; SERVICE=STOPPED; ACTIVATION=DEFAULT_OFF"
'''
    return script.replace('__WHEEL_NAME__', wheel_name)


def handoff_anchors(output: Path) -> dict[str, str]:
    manifest = json.loads((output / 'bundle-manifest.json').read_bytes())
    return {
        'EXPECTED_RELEASE_SHA': str(manifest['release_sha']),
        'EXPECTED_RELEASE_TREE': str(manifest['release_tree']),
        'EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST': str(manifest['release_manifest_digest']),
        'EXPECTED_BUNDLE_MANIFEST_SHA256': _digest(output / 'bundle-manifest.json'),
        'EXPECTED_REMOTE_QUALIFICATION_SHA256': _digest(output / 'remote-qualification.sh'),
    }


def build_bundle(
    *,
    root: Path,
    output: Path,
    sha: str,
    tree: str,
    wheel: Path,
    bar_1m: str,
    bar_5m: str,
    cost_version: str = "",
    launch_artifacts: Path | None = None,
) -> Path:
    exact_clean_head(root, expected_head=sha)
    exact_clean_tree(root, expected_tree=tree)
    if not re.fullmatch(r"[A-Za-z0-9_.+-]+\.whl", wheel.name):
        raise BundleError("rc5 wheel filename is unsafe")
    if _digest(wheel) != PILOT_WHEEL_SHA256:
        raise BundleError("rc5 wheel differs from exact pilot lock hash")
    if output.exists():
        raise BundleError("bundle destination already exists")
    release = build_release_manifest(root, release_sha=sha, release_tree=tree)
    example = json.loads((root / "deploy/p4a/config/three-setup-shadow.json.example").read_text())
    launch = None
    if example.get("schema") == THREE_SETUP_L0_CONFIG_SCHEMA:
        if launch_artifacts is None:
            raise BundleError("L0 requires complete generated launch artifacts")
        from scripts.e4_nautilus_public_data_probe import validate_launch
        from trader_assist_v0.multi_asset_shadow.models import RegistryVersion
        from trader_assist_v0.nautilus_e4.contracts import PitUniverseSnapshot, RunManifest

        def regular(relative: str) -> bytes:
            path = launch_artifacts / relative
            if not path.is_file() or path.is_symlink():
                raise BundleError("launch artifact is absent or non-regular")
            _reject_secret(path)
            return path.read_bytes()

        seed = RegistryVersion.model_validate_json(regular("registry-seed.json"))
        snapshot = PitUniverseSnapshot.model_validate_json(regular("e4/pit-universe-snapshot.json"))
        manifest = RunManifest.model_validate_json(regular("e4/run-manifest.json"))
        bars = tuple(json.loads(regular("bar-types.json")))
        validate_launch(seed, snapshot, manifest, bars)
        if manifest.git_sha != sha or manifest.git_tree != tree:
            raise BundleError("launch artifacts differ from exact candidate SHA/tree")
        if cost_version or bar_1m or bar_5m:
            raise BundleError("L0 does not accept legacy bar-pair/cost overrides")
        example["e4_bar_types"] = list(bars)
        example["cost_model"] = None
        launch = (seed, snapshot, manifest)
    elif example.get("schema") == THREE_SETUP_E4_CONFIG_SCHEMA:
        # Retained explicit v2 reader/fixtures; the real L0 example never enters this route.
        if not bar_1m.endswith("-1-MINUTE-LAST-EXTERNAL") or not bar_5m.endswith(
            "-5-MINUTE-LAST-EXTERNAL"
        ):
            raise BundleError("exact external 1m and 5m bar types are required")
        example["e4_bar_types"] = [bar_1m, bar_5m]
        example["cost_model"]["version"] = cost_version
    else:
        raise BundleError("release example is not an accepted E4 schema")
    example["release_sha"] = sha
    try:
        payload = output / "payload"
        for path in release_paths(root):
            _reject_secret(path)
            target = payload / path.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
        if launch is not None:
            from trader_assist_v0.multi_asset_shadow.registry import MarketRegistryManager
            from trader_assist_v0.nautilus_e4.storage import EvidenceStore

            seed, snapshot, manifest = launch
            identity_root = output / "identity"
            EvidenceStore(identity_root / "e4").initialize(manifest, snapshot)
            registry = MarketRegistryManager(
                identity_root / "registry", metadata_validator=lambda market: market in seed.markets
            )
            registry.stage(seed)
            registry.request_apply(seed.version)
            assert launch_artifacts is not None
            qualification = launch_artifacts / "qualification.json"
            if qualification.exists():
                from types import SimpleNamespace

                from trader_assist_v0.multi_asset_shadow.production import validate_l0_qualification

                regular("qualification.json")
                report = json.loads(qualification.read_bytes())
                digest = report.get("digest")
                validate_l0_qualification(cast(ThreeSetupProductionConfig, SimpleNamespace(
                    data_collection_only=True, qualification_path=qualification,
                    qualification_digest=digest,
                    e4_manifest_path=identity_root / "e4/run-manifest.json",
                )))
                example["qualification_digest"] = digest
                shutil.copyfile(qualification, identity_root / "qualification.json")
        (output / "config").mkdir(parents=True)
        (output / "config/three-setup-shadow.json").write_bytes(canonical_json_bytes(example))
        (output / "config/three-setup-shadow.env").write_text(
            "TRADER_ASSIST_V0_THREE_SETUP_ENABLE=0\n"
            "TRADER_ASSIST_V0_THREE_SETUP_MODE=DISABLED\n"
            "TRADER_ASSIST_V0_THREE_SETUP_CONFIG_PATH=/etc/trader-assist-v0/three-setup-shadow.json\n"
            f"TRADER_ASSIST_V0_THREE_SETUP_RELEASE_SHA={sha}\n"
            f"TRADER_ASSIST_V0_THREE_SETUP_RELEASE_TREE={tree}\n"
            f"TRADER_ASSIST_V0_THREE_SETUP_MANIFEST_DIGEST={release['manifest_sha256']}\n",
            encoding="utf-8",
        )
        (output / "release-manifest.json").write_bytes(canonical_json_bytes(release))
        shutil.copy2(wheel, output / wheel.name)
        remote = output / "remote-qualification.sh"
        remote.write_text(
            _remote_script(wheel.name),
            encoding="utf-8",
        )
        remote.chmod(0o750)
        selected = sorted(path for path in output.rglob("*") if path.is_file())
        files = [
            {
                "path": path.relative_to(output).as_posix(),
                "sha256": _digest(path),
                "size": path.stat().st_size,
            }
            for path in selected
        ]
        (output / "bundle-manifest.json").write_bytes(
            canonical_json_bytes(
                {
                    "schema": "trader-assist-v0/three-setup-deployment-bundle/v1",
                    "release_sha": sha,
                    "release_tree": tree,
                    "files": files,
                    "release_manifest_digest": release["manifest_sha256"],
                    "upload_path": f"/tmp/trade-os-deploy-ts7-{sha[:12]}",
                    "activation": "DEFAULT_OFF",
                    "service": "STOPPED",
                }
            )
        )
    except Exception:
        shutil.rmtree(output, ignore_errors=True)
        raise
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--expected-tree", required=True)
    parser.add_argument("--rc5-wheel", type=Path, required=True)
    parser.add_argument("--bar-type-1m", default="")
    parser.add_argument("--bar-type-5m", default="")
    parser.add_argument("--cost-model-version", default="")
    parser.add_argument("--launch-artifacts", type=Path)
    args = parser.parse_args()
    path = build_bundle(
        root=args.root.resolve(),
        output=args.output.resolve(),
        sha=args.expected_sha,
        tree=args.expected_tree,
        wheel=args.rc5_wheel,
        bar_1m=args.bar_type_1m,
        bar_5m=args.bar_type_5m,
        cost_version=args.cost_model_version,
        launch_artifacts=args.launch_artifacts,
    )
    print(f"THREE_SETUP_BUNDLE={path}")
    for key, value in handoff_anchors(path).items():
        print(f"{key}={value}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
