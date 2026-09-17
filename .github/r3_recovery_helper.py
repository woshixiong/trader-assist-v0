from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

REPO_SLUG = "woshixiong/trader-assist-v0"
EXPECTED_MAIN = "7da5575cdb26db253ddadcf3bb16b34feede661f"
TARGET_BRANCH = "engineering/ordinary-vnext-formal-g4-20260917"
EXPECTED_OLD_HEAD = "01e724112e048bc5b9762389da66a65729da3916"
EXPECTED_LOCAL_HEAD = "8efb04251bdf1c30dfd2ebadbdf944d66dbb0f48"
EXPECTED_TREE = "8d49830a398b3f157fb0b58936a977314040a348"
EXPECTED_PARENT_TREE = "58485b4d417bd237a98718574649250b6e72b0ef"
CHECKPOINT_BLOB = "ac32a16da18bdc4569785260dbb4a81d143cc556"
CHECKPOINT_TAR_SHA256 = "576e67437a147c0b89ca703a4b60494502d4c3b4f0e25b090649c2256eb6c9c8"
GOVERNANCE_BRANCH = "governance/local-git-transport-fallback-20260917"
TOKEN = os.environ["GH_TOKEN"]


def api(method: str, path: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload, separators=(",", ":")).encode()
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO_SLUG}/{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(archive: Path, destination: Path) -> None:
    with tarfile.open(archive, "r:gz") as tf:
        dest = destination.resolve()
        for member in tf.getmembers():
            candidate = (destination / member.name).resolve()
            if candidate != dest and dest not in candidate.parents:
                raise RuntimeError(f"unsafe tar member: {member.name}")
        tf.extractall(destination)


def verify_hash_file(root: Path, hash_file: str) -> None:
    for line in (root / hash_file).read_text().splitlines():
        expected, rel = line.split("  ", 1)
        actual = sha256(root / rel)
        if actual != expected:
            raise RuntimeError(f"hash mismatch {rel}: {actual} != {expected}")


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text()
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"anchor count for {path}: {count}")
    p.write_text(text.replace(old, new, 1))


def recreate_r3_objects(root: Path) -> str:
    main = api("GET", "git/ref/heads/main")["object"]["sha"]  # type: ignore[index]
    remote_head = api("GET", f"git/ref/heads/{TARGET_BRANCH}")["object"]["sha"]  # type: ignore[index]
    parent_tree = api("GET", f"git/commits/{EXPECTED_OLD_HEAD}")["tree"]["sha"]  # type: ignore[index]
    assert main == EXPECTED_MAIN, (main, EXPECTED_MAIN)
    assert remote_head == EXPECTED_OLD_HEAD, (remote_head, EXPECTED_OLD_HEAD)
    assert parent_tree == EXPECTED_PARENT_TREE, (parent_tree, EXPECTED_PARENT_TREE)

    expected_blob: dict[str, tuple[str, str]] = {}
    for line in (root / "git-ls-tree.txt").read_text().splitlines():
        meta, path = line.split("\t", 1)
        mode, typ, object_sha = meta.split()
        assert typ == "blob"
        expected_blob[path] = (mode, object_sha)

    entries: list[dict[str, str]] = []
    for path in (root / "paths.txt").read_text().splitlines():
        raw = (root / "files" / path).read_bytes()
        created = api(
            "POST",
            "git/blobs",
            {"content": base64.b64encode(raw).decode(), "encoding": "base64"},
        )["sha"]
        mode, wanted = expected_blob[path]
        assert created == wanted, (path, created, wanted)
        entries.append({"path": path, "mode": mode, "type": "blob", "sha": str(created)})
        print(f"R3_BLOB_OK={path}:{created}")

    tree = api("POST", "git/trees", {"base_tree": EXPECTED_PARENT_TREE, "tree": entries})["sha"]
    assert tree == EXPECTED_TREE, (tree, EXPECTED_TREE)
    print(f"R3_REMOTE_TREE={tree}")

    metadata: dict[str, str] = {}
    for line in (root / "commit-metadata.txt").read_text().splitlines():
        key, value = line.split("=", 1)
        metadata[key] = value
    message = (root / "commit-message.txt").read_text().rstrip("\n")
    commit = api(
        "POST",
        "git/commits",
        {
            "message": message,
            "tree": EXPECTED_TREE,
            "parents": [EXPECTED_OLD_HEAD],
            "author": {
                "name": metadata["author_name"],
                "email": metadata["author_email"],
                "date": metadata["author_date"],
            },
            "committer": {
                "name": metadata["committer_name"],
                "email": metadata["committer_email"],
                "date": metadata["committer_date"],
            },
        },
    )
    assert commit["tree"]["sha"] == EXPECTED_TREE  # type: ignore[index]
    assert commit["parents"][0]["sha"] == EXPECTED_OLD_HEAD  # type: ignore[index]
    commit_sha = str(commit["sha"])
    print(f"REMOTE_R3_COMMIT={commit_sha}")
    print(f"REMOTE_R3_COMMIT_MATCHES_LOCAL={str(commit_sha == EXPECTED_LOCAL_HEAD).upper()}")
    print("R3_TARGET_REF_MUTATED=NO")
    return commit_sha


def amend_governance() -> None:
    transport = "governance/GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md"
    preflight = "governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md"
    command = "governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md"

    hard_gate = '''### 1.0 Mandatory applicability and transport-health gate

Before delivering or executing any nontrivial user-local GitHub publication command for this repository, load this procedure explicitly and record:

```text
LOCAL_GIT_PUBLICATION_APPLICABLE=YES
LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED=YES
LOCAL_GIT_TRANSPORT_GATE=PASS
KNOWN_LOCAL_GIT_TRANSPORT_INCIDENTS_REVIEWED=YES
AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES
CHECKPOINT_AWARE_PUBLICATION_FALLBACK_PLAN=PASS
```

If user-local Git publication is applicable and this gate is not `PASS`, command delivery is prohibited. A Writer/implementation preflight PASS does not substitute for this transport gate.

The default route below remains HTTPS + GitHub CLI browser OAuth. The gate exists to prove that the selected transport is fit for the current environment and checkpoint, not to force redundant lower-reliability network probes after authoritative remote identity is already available.

'''
    replace_once(transport, "### 1.1 Credential handling\n", hard_gate + "### 1.1 Credential handling\n")

    fallback = '''### 1.3 Checkpoint-aware transport failure and fallback ladder

A local transport failure must be classified against the semantic checkpoint before another publication attempt:

```text
DEFAULT_LOCAL_ROUTE
-> HTTPS + GitHub CLI browser OAuth + secure credential helper

IF LOCAL_TRANSPORT_FAILS BEFORE SEMANTIC_ACTION
-> classify environment/auth/transport failure
-> select the simplest accepted reliable route
-> do not consume application semantic repair budget

IF SEMANTIC_ACTION_COMPLETED
AND EXACT_CHECKPOINT_EXISTS
AND LOCAL_GITHUB_HTTPS_OR_API_PATH_IS_UNHEALTHY
-> SEMANTIC_RERUN=NO
-> LOCAL_PUSH_OR_API_RETRY_LOOP=PROHIBITED
-> CHECKPOINT_RESUME=REQUIRED
-> preserve exact artifact/tree/parent/scope evidence
-> prefer offline deterministic checkpoint export plus an already-authorized authoritative GitHub connector/provider-native remote publication surface when it provides equal or higher fidelity and requires no credential-scope expansion
```

A fallback publication must retain fresh remote identity/race protection, exact artifact or tree verification, non-force fast-forward semantics where applicable, and the normal exact-head CI/review gates. A local TLS/proxy/TUN incident does not by itself replace the project-wide HTTPS default or revive SSH-over-443 as the default.

'''
    replace_once(
        transport,
        "\n---\n\n## 2. Reviewed Pull Request terminal-disposition discipline",
        "\n" + fallback + "---\n\n## 2. Reviewed Pull Request terminal-disposition discipline",
    )

    replace_once(
        preflight,
        "COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION|NOT_APPLICABLE\n```",
        '''COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION|NOT_APPLICABLE
LOCAL_GIT_PUBLICATION_APPLICABLE=YES|NO|NOT_APPLICABLE
LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED=YES|NO|NOT_APPLICABLE
LOCAL_GIT_TRANSPORT_GATE=PASS|FAIL|NOT_APPLICABLE
KNOWN_LOCAL_GIT_TRANSPORT_INCIDENTS_REVIEWED=YES|NO|NOT_APPLICABLE
AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES|NO|NOT_APPLICABLE
CHECKPOINT_AWARE_PUBLICATION_FALLBACK_PLAN=PASS|FAIL|NOT_APPLICABLE
```''',
    )
    replace_once(
        preflight,
        "COMMAND_IS_WRITER_LAUNCH_PATH\nAND COMMAND_DELIVERY=PROHIBITED",
        '''LOCAL_GIT_PUBLICATION_APPLICABLE=YES
AND (
  LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED != YES
  OR LOCAL_GIT_TRANSPORT_GATE != PASS
  OR KNOWN_LOCAL_GIT_TRANSPORT_INCIDENTS_REVIEWED != YES
  OR AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED != YES
  OR CHECKPOINT_AWARE_PUBLICATION_FALLBACK_PLAN != PASS
)
=> COMMAND_DELIVERY=PROHIBITED

COMMAND_IS_WRITER_LAUNCH_PATH
AND COMMAND_DELIVERY=PROHIBITED''',
    )

    replace_once(
        command,
        "COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION\n```",
        '''COMMAND_REPAIR_STAGE=INITIAL|BOUNDED_CORRECTION|HOLISTIC_REGENERATION
APPLICABLE_SPECIALIZED_PROCEDURES=
LOCAL_GIT_PUBLICATION_ROUTE=LOCAL_HTTPS|AUTHORITATIVE_REMOTE_CONNECTOR|NOT_APPLICABLE
LOCAL_GIT_TRANSPORT_GATE=PASS|FAIL|NOT_APPLICABLE
CHECKPOINT_AWARE_PUBLICATION_FALLBACK_PLAN=PASS|FAIL|NOT_APPLICABLE
```''',
    )
    checkpoint_section = '''### 7.2 Checkpoint-aware GitHub publication transport

When publication follows a completed semantic Writer/action, treat the completed exact artifact/tree as the authoritative resume checkpoint. Do not couple semantic retry accounting to a later local Git/TLS failure.

```text
SEMANTIC_ACTION_COMPLETED=YES
AND EXACT_CHECKPOINT_PROVABLE=YES
AND LOCAL_GITHUB_TRANSPORT_UNHEALTHY=YES
=> RERUN_SEMANTIC_ACTION=NO
=> LOCAL_TRANSPORT_RETRY_LOOP=NO
=> LOAD_GITHUB_LOCAL_TRANSPORT_PROCEDURE=YES
=> CHECK_AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE=YES
=> IF equal-or-higher fidelity + no scope expansion:
     OFFLINE_EXACT_CHECKPOINT_EXPORT
     -> AUTHORITATIVE_REMOTE_PUBLICATION
     -> EXACT_REMOTE_TREE/HEAD_READBACK
     -> AUTHORITATIVE_CI
```

This route is checkpoint resume, not a silent transport substitution. The publication surface must preserve the exact accepted content identity and normal branch/ref/race protections. Authentication or permission expansion remains separately gated.

'''
    replace_once(command, "## 8. Command repair budget\n", checkpoint_section + "## 8. Command repair budget\n")
    incident_anchor = "| --- | --- | --- |\n"
    incident_row = "| R3 Formal G4 semantic Writer completed, then local `git push` hit LibreSSL `SSL_ERROR_SYSCALL` and local `gh api` hit EOF while an authorized GitHub connector write surface remained available | environment capability mismatch + specialized-transport applicability miss | preserve the exact checkpoint; stop local push/API retry loops; use offline deterministic export + authoritative remote publication; user-local Git publication must load the local-transport procedure as a hard pre-delivery gate |\n"
    replace_once(command, incident_anchor, incident_anchor + incident_row)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="r3-recovery-") as td:
        work = Path(td)
        blob = api("GET", f"git/blobs/{CHECKPOINT_BLOB}")
        archive = work / "checkpoint.tar.gz"
        archive.write_bytes(base64.b64decode(str(blob["content"])))
        assert sha256(archive) == CHECKPOINT_TAR_SHA256
        safe_extract(archive, work)
        root = work / "trade_os_r3_checkpoint_export_8efb04251bdf"
        verify_hash_file(root, "manifest.sha256")
        verify_hash_file(root, "file-sha256.txt")
        metadata = json.loads((root / "metadata.json").read_text())
        assert metadata["local_commit"] == EXPECTED_LOCAL_HEAD
        assert metadata["local_tree"] == EXPECTED_TREE
        assert metadata["parent"] == EXPECTED_OLD_HEAD
        assert metadata["parent_tree"] == EXPECTED_PARENT_TREE
        assert metadata["expected_changed_path_count"] == 10
        assert metadata["semantic_writer_rerun"] is False
        assert (root / "paths.txt").read_text() == (root / "actual-paths.txt").read_text()
        recreate_r3_objects(root)

    amend_governance()
    Path(".github/workflows/r3-connector-recovery.yml").unlink()
    Path(".github/r3_recovery_helper.py").unlink()
    subprocess.run(["git", "diff", "--check"], check=True)
    changed = subprocess.check_output(["git", "diff", "--name-only", EXPECTED_MAIN], text=True).splitlines()
    changed = sorted(changed)
    expected = sorted([
        "governance/GITHUB_LOCAL_TRANSPORT_AND_REVIEWED_PR_CLOSEOUT_PROCEDURE_V1_2026-09-16.md",
        "governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md",
        "governance/GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md",
    ])
    assert changed == expected, (changed, expected)
    print("GOVERNANCE_CHANGED_PATHS=PASS_EXACT_3")
    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(["git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", "-A"], check=True)
    subprocess.run(["git", "commit", "-m", "[transport-helper-finalize] Governance: harden GitHub publication fallback"], check=True)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    subprocess.run(["git", "push", "origin", f"HEAD:refs/heads/{GOVERNANCE_BRANCH}"], check=True)
    print(f"GOVERNANCE_BRANCH_HEAD={head}")
    print("R3_TARGET_REF_MUTATED=NO")


if __name__ == "__main__":
    main()
