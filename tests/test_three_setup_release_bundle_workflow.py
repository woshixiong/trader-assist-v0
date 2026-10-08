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
# Synthetic event identity; never a frozen historical release SHA.
SHA = "a" * 40
TREE = "b" * 40


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
    for name in ("release_sha", "release_tree"):
        assert "default" not in inputs[name]
        assert inputs[name]["required"] is True and inputs[name]["type"] == "string"
    assert set(workflow["jobs"]) == {"build-release-bundle"}
    job = workflow["jobs"]["build-release-bundle"]
    assert job["runs-on"] == "ubuntu-24.04" and job["timeout-minutes"] == 30
    assert set(job) == {"runs-on", "timeout-minutes", "defaults", "env", "steps"}
    assert job["defaults"] == {"run": {"shell": "bash"}}
    assert job["env"]["RELEASE_SHA"] == "${{ inputs.release_sha }}"
    assert job["env"]["RELEASE_TREE"] == "${{ inputs.release_tree }}"
    assert job["env"]["CONTROL_HEAD"] == "${{ github.sha }}"
    assert "/release/src:" in job["env"]["PYTHONPATH"]
    assert "BUILD_ROOT" not in job["env"]
    assert "runner.temp" not in json.dumps(job["env"])
    initializers = [step for step in job["steps"] if step.get("id") == "build_root"]
    assert len(initializers) == 1
    initializer = initializers[0]
    assert set(initializer) == {"name", "id", "run"}
    assert job["steps"][0]["id"] == "inputs"
    assert job["steps"][1] == initializer
    assert job["steps"][2]["name"] == "Checkout exact control HEAD"
    for index, step in enumerate(job["steps"]):
        if step is not initializer and "BUILD_ROOT" in json.dumps(step):
            assert index > 1
    assert not re.search(r"\b(?:mkdir|install|touch)\b", initializer["run"])
    dependencies = steps()["dependencies"]["run"]
    absence = 'test ! -e "$BUILD_ROOT"'
    creation = 'mkdir -p "$BUILD_ROOT/wheels" "$BUILD_ROOT/package-source"'
    assert absence in dependencies and creation in dependencies
    assert dependencies.index(absence) < dependencies.index(creation)
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
        "aws ",
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
    for step in job["steps"]:
        if "run" in step and step.get("id") != "simulation":
            assert "sudo" not in step["run"]
            assert "systemctl" not in step["run"]
            assert "--install" not in step["run"]
    simulation = steps()["simulation"]["run"]
    assert "['systemctl', 'is-active', UNIT]" in simulation
    for command in ("daemon-reload", "start", "restart", "enable", "reboot"):
        assert not re.search(r"systemctl.{0,30}[\"']" + command + r"[\"']", simulation)
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


INVALID_RUN_IDENTIFIERS = [
    None, "", "abc", "-1", "+1", "1.0", " 123", "123 ", "1 23",
    "123\n456", "123\r456", "123\r\n456", "\uff11\uff12\uff13", "\u0661\u0662\u0663",
    "123/../escape", "$(touch injected)", "123; touch injected",
]
RUNTIME_VARIABLES = ("RUNNER_TEMP", "GITHUB_ENV", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")


def runtime_shell_run(
    step_id: str, cwd: Path, env: dict[str, str], *, errexit: bool = True
) -> subprocess.CompletedProcess[str]:
    # Remove runner variables so unset cases cannot inherit ambient CI values.
    clean_env = {
        key: value
        for key, value in os.environ.items()
        if key not in (*RUNTIME_VARIABLES, "BUILD_ROOT")
    }
    code = steps()[step_id]["run"]
    if not errexit:
        assert code.startswith("set -euo pipefail\n")
        code = code.replace("set -euo pipefail\n", "set -uo pipefail\n", 1)
    return subprocess.run(
        ["bash", "-c", code],
        cwd=cwd,
        env={**clean_env, **env},
        capture_output=True,
        text=True,
        check=False,
    )


def initializer_env(tmp_path: Path) -> dict[str, str]:
    runner_temp = tmp_path / "runner temp with spaces"
    runner_temp.mkdir()
    environment = tmp_path / "github-env"
    environment.write_text("UNRELATED=preserved\n")
    return {
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_ENV": str(environment),
        "GITHUB_RUN_ID": "123",
        "GITHUB_RUN_ATTEMPT": "1",
    }


@pytest.mark.parametrize("run_id,attempt", [("123", "1"), ("0", "0"), ("00123", "0001")])
def test_runtime_initializer_assignment_and_propagation(
    tmp_path: Path, run_id: str, attempt: str
) -> None:
    env = initializer_env(tmp_path)
    env.update(GITHUB_RUN_ID=run_id, GITHUB_RUN_ATTEMPT=attempt)
    expected = f"{env['RUNNER_TEMP']}/l0-release-{run_id}-{attempt}"
    assert_pass(runtime_shell_run("build_root", tmp_path, env))
    text = Path(env["GITHUB_ENV"]).read_text()
    assert text == f"UNRELATED=preserved\nBUILD_ROOT={expected}\n"
    assert not Path(expected).exists()
    assert list(Path(env["RUNNER_TEMP"]).iterdir()) == []
    propagated = dict(line.split("=", 1) for line in text.splitlines())
    # Model the next step by supplying parsed data, never sourcing the env file.
    result = subprocess.run(
        [sys.executable, "-B", "-c", "import os; print(os.environ['BUILD_ROOT'])"],
        env={**os.environ, **propagated},
        capture_output=True,
        text=True,
        check=False,
    )
    assert_pass(result)
    assert result.stdout == expected + "\n"


def test_runtime_initializer_per_run_and_attempt_uniqueness(tmp_path: Path) -> None:
    env = initializer_env(tmp_path)
    paths = set()
    for run_id, attempt in [("123", "1"), ("124", "1"), ("123", "2")]:
        Path(env["GITHUB_ENV"]).write_text("")
        env.update(GITHUB_RUN_ID=run_id, GITHUB_RUN_ATTEMPT=attempt)
        assert_pass(runtime_shell_run("build_root", tmp_path, env))
        paths.add(Path(env["GITHUB_ENV"]).read_text().strip().split("=", 1)[1])
    assert len(paths) == 3
    assert list(Path(env["RUNNER_TEMP"]).iterdir()) == []


@pytest.mark.parametrize("variable", ["GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"])
@pytest.mark.parametrize("value", INVALID_RUN_IDENTIFIERS)
@pytest.mark.parametrize("errexit", [True, False])
def test_runtime_initializer_rejects_invalid_identifiers(
    tmp_path: Path, variable: str, value: str | None, errexit: bool
) -> None:
    env = initializer_env(tmp_path)
    if value is None:
        env.pop(variable)
    else:
        env[variable] = value
    result = runtime_shell_run("build_root", tmp_path, env, errexit=errexit)
    assert result.returncode != 0
    assert f"{variable} must contain only ASCII digits" in result.stderr
    assert Path(env["GITHUB_ENV"]).read_text() == "UNRELATED=preserved\n"
    assert list(Path(env["RUNNER_TEMP"]).iterdir()) == []
    assert not (tmp_path / "injected").exists()


@pytest.mark.parametrize("variable", ["RUNNER_TEMP", "GITHUB_ENV"])
@pytest.mark.parametrize("value", [None, ""])
def test_runtime_initializer_requires_runner_paths(
    tmp_path: Path, variable: str, value: str | None
) -> None:
    env = initializer_env(tmp_path)
    original = dict(env)
    if value is None:
        env.pop(variable)
    else:
        env[variable] = value
    result = runtime_shell_run("build_root", tmp_path, env)
    assert result.returncode != 0
    assert f"{variable} must be set and non-empty" in result.stderr
    assert Path(original["GITHUB_ENV"]).read_text() == "UNRELATED=preserved\n"
    assert list(Path(original["RUNNER_TEMP"]).iterdir()) == []


@pytest.mark.parametrize("line_break", ["\n", "\r", "\r\n"])
def test_runtime_initializer_rejects_temp_path_line_breaks(
    tmp_path: Path, line_break: str
) -> None:
    env = initializer_env(tmp_path)
    original_temp = Path(env["RUNNER_TEMP"])
    env["RUNNER_TEMP"] += line_break + "INJECTED=value"
    result = runtime_shell_run("build_root", tmp_path, env)
    assert result.returncode != 0
    assert "RUNNER_TEMP must not contain line breaks" in result.stderr
    assert Path(env["GITHUB_ENV"]).read_text() == "UNRELATED=preserved\n"
    assert list(original_temp.iterdir()) == []
    assert not Path(env["RUNNER_TEMP"]).exists()


def test_runtime_initializer_fails_on_environment_append(tmp_path: Path) -> None:
    env = initializer_env(tmp_path)
    env["GITHUB_ENV"] = str(tmp_path / "environment-directory")
    Path(env["GITHUB_ENV"]).mkdir()
    result = runtime_shell_run("build_root", tmp_path, env, errexit=False)
    assert result.returncode != 0
    assert "Failed to persist BUILD_ROOT through GITHUB_ENV" in result.stderr
    assert list(Path(env["GITHUB_ENV"]).iterdir()) == []
    assert list(Path(env["RUNNER_TEMP"]).iterdir()) == []


def dispatch_env() -> dict[str, str]:
    """Model the main event independently from the required form inputs."""
    return {
        "RELEASE_SHA": SHA,
        "RELEASE_TREE": TREE,
        "INPUT_RELEASE_SHA": SHA,
        "INPUT_RELEASE_TREE": TREE,
        "CONTROL_HEAD": SHA,
        "GITHUB_REF": "refs/heads/main",
    }


def test_dispatch_accepts_only_matching_main_event(tmp_path: Path) -> None:
    assert_pass(shell_run("inputs", tmp_path, dispatch_env()))


@pytest.mark.parametrize(
    "mutation",
    [
        "old_old", "old_new", "new_old", "branch", "tag",
        "missing_ref", "empty_ref", "missing_control", "empty_control",
        "wrong_control", "short_control", "uppercase_control", "nonhex_control",
        "missing_input_sha", "missing_input_tree", "missing_env_sha",
        "missing_env_tree", "short", "uppercase", "nonhex", "wrong_sha",
        "wrong_tree", "short_tree", "uppercase_tree", "malformed_tree", "injection",
    ],
)
def test_dispatch_input_rejection(tmp_path: Path, mutation: str) -> None:
    env = dispatch_env()
    old_sha = "1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b"
    old_tree = "2daee287c155fa33e8af5894f3825d7eddb09e70"
    if mutation in ("old_old", "old_new"):
        env["INPUT_RELEASE_SHA"] = env["RELEASE_SHA"] = old_sha
    if mutation == "old_old":
        env["INPUT_RELEASE_TREE"] = env["RELEASE_TREE"] = old_tree
    elif mutation == "new_old":
        # A mixed new/old input must fail even when the env keeps the new tree.
        env["INPUT_RELEASE_TREE"] = old_tree
    if mutation == "branch":
        env["GITHUB_REF"] = "refs/heads/feature"
    elif mutation == "tag":
        env["GITHUB_REF"] = "refs/tags/main"
    elif mutation == "missing_ref":
        env.pop("GITHUB_REF")
    elif mutation == "empty_ref":
        env["GITHUB_REF"] = ""
    elif mutation == "missing_control":
        env.pop("CONTROL_HEAD")
    elif mutation == "empty_control":
        env["CONTROL_HEAD"] = ""
    elif mutation == "wrong_control":
        env["CONTROL_HEAD"] = "c" * 40
    elif mutation == "short_control":
        env["CONTROL_HEAD"] = SHA[:12]
    elif mutation == "uppercase_control":
        env["CONTROL_HEAD"] = SHA.upper()
    elif mutation == "nonhex_control":
        env["CONTROL_HEAD"] = "z" * 40
    elif mutation == "missing_input_sha":
        env.pop("INPUT_RELEASE_SHA")
    elif mutation == "missing_input_tree":
        env.pop("INPUT_RELEASE_TREE")
    elif mutation == "missing_env_sha":
        env.pop("RELEASE_SHA")
    elif mutation == "missing_env_tree":
        env.pop("RELEASE_TREE")
    elif mutation in ("short", "uppercase", "nonhex", "wrong_sha", "injection"):
        env["INPUT_RELEASE_SHA"] = {
            "short": SHA[:12],
            "uppercase": SHA.upper(),
            "nonhex": "z" * 40,
            "wrong_sha": "c" * 40,
            "injection": "$(touch injected)",
        }[mutation]
    elif mutation in ("wrong_tree", "short_tree", "uppercase_tree", "malformed_tree"):
        env["INPUT_RELEASE_TREE"] = {
            "wrong_tree": "c" * 40,
            "short_tree": TREE[:12],
            "uppercase_tree": TREE.upper(),
            "malformed_tree": "z" * 40,
        }[mutation]
    assert shell_run("inputs", tmp_path, env).returncode != 0
    assert not (tmp_path / "injected").exists()


def twin_checkouts(tmp_path: Path, *, l0: bool = False) -> tuple[str, str]:
    """Two separate clean checkouts of the same exact commit and tree."""
    release = tmp_path / "release"
    sha, tree = _candidate_repo(release, l0=l0)
    subprocess.run(
        ["git", "clone", "-q", "--no-local", str(release), str(tmp_path / "control")],
        check=True, capture_output=True, text=True,
    )
    assert git(tmp_path / "control", "rev-parse", "HEAD") == sha
    assert git(tmp_path / "control", "rev-parse", "HEAD^{tree}") == tree
    assert git(tmp_path / "control", "status", "--porcelain") == ""
    return sha, tree


@pytest.mark.parametrize(
    "mutation",
    ["sha", "tree", "dirty", "untracked", "control", "control_dirty",
     "control_untracked", "control_other_commit"],
)
def test_checkout_drift_rejection(tmp_path: Path, mutation: str) -> None:
    sha, tree = twin_checkouts(tmp_path)
    env = {"RELEASE_SHA": sha, "RELEASE_TREE": tree, "CONTROL_HEAD": sha}
    assert_pass(shell_run("identity", tmp_path, env))
    if mutation == "sha":
        env["RELEASE_SHA"] = "a" * 40 if sha != "a" * 40 else "b" * 40
    elif mutation == "tree":
        env["RELEASE_TREE"] = "b" * 40 if tree != "b" * 40 else "c" * 40
    elif mutation == "control":
        env["CONTROL_HEAD"] = "c" * 40 if sha != "c" * 40 else "d" * 40
    elif mutation == "dirty":
        (tmp_path / "release/src/demo.py").write_text("CHANGED = 1\n")
    elif mutation == "untracked":
        (tmp_path / "release/untracked").touch()
    elif mutation == "control_dirty":
        (tmp_path / "control/src/demo.py").write_text("CHANGED = 1\n")
    elif mutation == "control_untracked":
        (tmp_path / "control/untracked").touch()
    else:
        (tmp_path / "control/control-only").write_text("DIFFERENT\n")
        subprocess.run(["git", "-C", str(tmp_path / "control"), "add", "."], check=True)
        subprocess.run(
            ["git", "-C", str(tmp_path / "control"), "-c", "user.name=Test",
             "-c", "user.email=test@example.invalid", "commit", "-qm", "different control"],
            check=True,
        )
    assert shell_run("identity", tmp_path, env).returncode != 0


@pytest.fixture
def raw_bundle_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    """Use the real L0 builders and existing minimal clean-source fixture."""
    release = tmp_path / "release"
    sha, tree = twin_checkouts(tmp_path, l0=True)
    control = git(tmp_path / "control", "rev-parse", "HEAD")
    assert control == sha
    assert git(tmp_path / "control", "rev-parse", "HEAD^{tree}") == tree
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


@pytest.fixture
def bundle_fixture(raw_bundle_fixture: dict[str, str]) -> dict[str, str]:
    assert_pass(python_run("finalize", raw_bundle_fixture))
    return raw_bundle_fixture


@pytest.mark.parametrize(
    "mutation",
    [
        "none",
        "missing",
        "duplicate",
        "extra",
        "malformed",
        "sha",
        "digest",
        "order",
        "stale",
        "blank",
    ],
)
def test_actual_anchor_capture(bundle_fixture: dict[str, str], mutation: str) -> None:
    env = bundle_fixture
    stdout = Path(env["BUILD_ROOT"]) / "finalized-anchors.env"
    lines = stdout.read_text().splitlines()
    if mutation == "missing":
        lines.pop()
    elif mutation == "duplicate":
        lines.append(lines[-1])
    elif mutation == "extra":
        lines.append("EXPECTED_UNAUTHORIZED=" + "a" * 64)
    elif mutation == "malformed":
        lines[-1] = lines[-1].split("=")[0] + "=bad"
    elif mutation == "order":
        lines.reverse()
    elif mutation == "blank":
        lines.append("")
    elif mutation == "stale":
        lines = (stdout.parent / "builder-stdout.txt").read_text().splitlines()[1:]
    elif mutation == "sha":
        env["RELEASE_SHA"] = "c" * 40 if env["RELEASE_SHA"] != "c" * 40 else "d" * 40
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
    (root / "simulation-archive.sha256").write_text(
        hashlib.sha256(archive_bytes).hexdigest() + "\n"
    )
    assert_pass(shell_run("terminal", Path(env["GITHUB_WORKSPACE"]), env))
    summary = Path(env["GITHUB_STEP_SUMMARY"]).read_text()
    assert f"CONTROL_HEAD={env['CONTROL_HEAD']}" in summary
    assert f"EXPECTED_RELEASE_SHA={env['RELEASE_SHA']}" in summary
    assert env["CONTROL_HEAD"] == env["RELEASE_SHA"]
    assert (Path(env["GITHUB_WORKSPACE"]) / "control").resolve() != (
        Path(env["GITHUB_WORKSPACE"]) / "release"
    ).resolve()
    provenance = json.loads((root / "handoff/provenance.json").read_text())
    assert provenance["control_head"] == env["CONTROL_HEAD"]
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
    recorded_calls = (root / "argv.jsonl").read_bytes()
    for variable in ("GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"):
        for value in INVALID_RUN_IDENTIFIERS:
            invalid_env = dict(env)
            if value is None:
                invalid_env.pop(variable)
            else:
                invalid_env[variable] = value
            result = runtime_shell_run("builders", tmp_path, invalid_env, errexit=False)
            assert result.returncode != 0
            assert f"{variable} must contain only ASCII digits" in result.stderr
            assert (root / "argv.jsonl").read_bytes() == recorded_calls
            assert not (tmp_path / "injected").exists()
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
            "FinalShell", "0750",
            "Artifact PASS grants no deployment/runtime/service authority",
            "Intel Mac", "control HEAD",
        ):
            assert required in text
    operations = (ROOT / "docs/operations/THREE_SETUP_SHADOW_DEPLOYMENT.md").read_text()
    workflow = parse_workflow(WORKFLOW.read_text())
    for field in ("release_sha", "release_tree"):
        assert workflow["on"]["workflow_dispatch"]["inputs"][field]["required"]
        assert "default" not in workflow["on"]["workflow_dispatch"]["inputs"][field]
    for required in (
        "gh api repos/woshixiong/trader-assist-v0/commits/main",
        ".commit.tree.sha", "gh workflow run three-setup-release-bundle.yml",
        "--ref main", "refs/heads/main", "control HEAD",
        "release_sha", "release_tree", "gh run download",
        "EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST",
        "EXPECTED_BUNDLE_MANIFEST_SHA256",
        "EXPECTED_REMOTE_QUALIFICATION_SHA256", "NOT_QUALIFIED",
        "cost_model: null", "NautilusTrader", "2.0.0rc5",
        "20 markets", "40", "four independent",
        "separate current deployment authorization",
        "separate service-start authorization", "2400", "DEFAULT_OFF",
        "UNKNOWN_INSUFFICIENT_ARTIFACTS", "NOT_ACCEPTED",
        "3_600_000_000_000",
    ):
        assert required in operations
    for retired in (
        "## Mandatory retained-log replay before another live qualification",
        "REPLAY_ONLY_ISOLATED_DIAGNOSTIC_DEPLOYMENT",
        "UNAVAILABLE_FACTS_REQUIRE_CONTROL_DISPOSITION",
        "replay-diagnostic.json",
        "release_sha=1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b",
        "release_tree=2daee287c155fa33e8af5894f3825d7eddb09e70",
    ):
        assert retired not in operations
    identity = steps()["identity"]["run"]
    assert "git -C control rev-parse 'HEAD^{tree}'" in identity
    assert "git -C release rev-parse 'HEAD^{tree}'" in identity
    assert "git -C control status --porcelain=v1 --untracked-files=all" in identity
    assert "git -C release status --porcelain=v1 --untracked-files=all" in identity
    validation = steps()["inputs"]["run"]
    assert 'test "${GITHUB_REF:-}" = "refs/heads/main"' in validation
    assert 'test "$RELEASE_SHA" = "$CONTROL_HEAD"' in validation


@pytest.mark.parametrize("source", ["name: first\nname: second\n", "name: &alias forbidden\n"])
def test_restricted_yaml_rejects_duplicate_keys_and_aliases(source: str) -> None:
    with pytest.raises(AssertionError):
        parse_workflow(source)


def bundle_paths(bundle: Path) -> set[str]:
    return {path.relative_to(bundle).as_posix() for path in bundle.rglob("*")}


def test_finalization_rebinds_only_script_and_manifest(raw_bundle_fixture: dict[str, str]) -> None:
    env = raw_bundle_fixture
    root = Path(env["BUILD_ROOT"])
    bundle = root / "bundle"
    before_paths = bundle_paths(bundle)
    before = {
        p.relative_to(bundle).as_posix(): p.read_bytes() for p in bundle.rglob("*") if p.is_file()
    }
    old_anchors = builder.handoff_anchors(bundle)
    historical = (root / "builder-stdout.txt").read_bytes()
    assert_pass(python_run("finalize", env))
    after = {
        p.relative_to(bundle).as_posix(): p.read_bytes() for p in bundle.rglob("*") if p.is_file()
    }
    assert bundle_paths(bundle) == before_paths
    assert {name for name in before if before[name] != after[name]} == {
        "remote-qualification.sh",
        "bundle-manifest.json",
    }
    old_manifest = json.loads(before["bundle-manifest.json"])
    new_manifest = json.loads(after["bundle-manifest.json"])
    assert after["bundle-manifest.json"] == canonical_json_bytes(new_manifest)
    for old, new in zip(old_manifest["files"], new_manifest["files"], strict=True):
        assert old["path"] == new["path"]
        if old["path"] != "remote-qualification.sh":
            assert old == new
        else:
            data = after[old["path"]]
            assert new == {
                "path": old["path"],
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
    old_manifest["files"] = new_manifest["files"]
    assert old_manifest == new_manifest
    final = builder.handoff_anchors(bundle)
    assert len(final) == 5
    assert {key for key in final if final[key] != old_anchors[key]} == {
        "EXPECTED_REMOTE_QUALIFICATION_SHA256",
        "EXPECTED_BUNDLE_MANIFEST_SHA256",
    }
    assert (root / "builder-stdout.txt").read_bytes() == historical
    expected_record = "".join(f"{key}={value}\n" for key, value in final.items())
    assert (root / "finalized-anchors.env").read_text() == expected_record
    # Historical evidence cannot participate in final capture, even when missing.
    (root / "builder-stdout.txt").unlink()
    assert "builder-stdout.txt" not in steps()["anchors"]["run"]
    assert_pass(python_run("anchors", env))
    assert (root / "handoff/anchors.env").read_text() == expected_record
    source = before["remote-qualification.sh"].decode()
    adapted = after["remote-qualification.sh"].decode()
    separator = 'echo "STAGED_RELEASE_VERIFY=PASS"'
    assert source.split(separator, 1)[1] == adapted.split(separator, 1)[1]
    assert stat_mode(bundle / "remote-qualification.sh") == 0o750


def stat_mode(path: Path) -> int:
    return path.stat().st_mode & 0o777


@pytest.mark.parametrize(
    "mutation", ["missing", "duplicate", "unexpected", "entry_missing", "entry_duplicate"]
)
def test_adaptation_fails_closed(raw_bundle_fixture: dict[str, str], mutation: str) -> None:
    env = raw_bundle_fixture
    root = Path(env["BUILD_ROOT"])
    script = root / "bundle/remote-qualification.sh"
    source = script.read_text()
    command = next(
        line for line in source.splitlines() if "payload/scripts/verify_exact_release.py" in line
    )
    manifest_path = root / "bundle/bundle-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    if mutation == "missing":
        script.write_text(source.replace(command, ""))
    elif mutation == "duplicate":
        script.write_text(source + command + "\n")
    elif mutation == "unexpected":
        script.write_text(source.replace("--verify-staged", "--not-staged"))
    else:
        entry = next(
            item for item in manifest["files"] if item["path"] == "remote-qualification.sh"
        )
        if mutation == "entry_missing":
            manifest["files"].remove(entry)
        else:
            manifest["files"].append(dict(entry))
        manifest_path.write_bytes(canonical_json_bytes(manifest))
    before = script.read_bytes(), manifest_path.read_bytes()
    assert python_run("finalize", env).returncode != 0
    assert (script.read_bytes(), manifest_path.read_bytes()) == before
    assert not (root / "finalized-anchors.env").exists()


# Process fixtures record orchestration; only stdlib integrity/path checks run here.
# CPython 3.12 + historical dependency compatibility remains the Ubuntu Actions gate.
TARGET_PROCESS_FIXTURE = r"""
import json, os, shutil, signal, subprocess, sys, tempfile
from pathlib import Path
args = sys.argv[1:]
name = Path(sys.argv[0]).name
with open(os.environ['PROCESS_RECORD'], 'a') as record:
    record.write(json.dumps({'name': name, 'argv': args, 'executable': sys.argv[0],
        'pythonpath': os.environ.get('PYTHONPATH'),
        'no_bytecode': os.environ.get('PYTHONDONTWRITEBYTECODE')}) + '\n')
failure = os.environ.get('PROCESS_FAILURE', '')
if name == 'mktemp':
    assert args[:1] == ['-d'] and len(args) == 2
    if failure == 'mktemp':
        raise SystemExit(37)
    template = Path(args[1])
    parent = template.parent
    if failure == 'parent_identity':
        parent.rename(parent.with_name(parent.name + '-old'))
        parent.mkdir()
    if failure == 'allocation_parent':
        parent = Path(os.environ['ALTERNATE_TEMP'])
    result = tempfile.mkdtemp(prefix='trade-os-verify.', dir=parent)
    if failure == 'allocation_symlink':
        link = parent / 'trade-os-verify.link'
        link.symlink_to(result, target_is_directory=True)
        result = str(link)
    print(result)
elif name == 'rm':
    assert args[:2] == ['-rf', '--'] and len(args) == 3
    if failure in ('cleanup', 'verifier_cleanup'):
        raise SystemExit(41)
    path = Path(args[2])
    if path.is_symlink():
        target = path.resolve()
        path.unlink()
        shutil.rmtree(target)
    else:
        shutil.rmtree(path)
elif name == 'systemctl':
    assert args == ['is-active', 'trader-assist-v0-three-setup.service']
    print('inactive')
elif name == 'python3.12' and '-' in args:
    code = sys.stdin.read()
    version = '(3, 11)' if failure == 'python_identity' else '(3, 12)'
    if 'sys.version_info[:2]' in code:
        code = 'import sys; sys.version_info = ' + version + '\n' + code
    forwarded = args[args.index('-') + 1:]
    code = 'import sys; sys.argv = ' + repr(['-', *forwarded]) + '\n' + code
    raise SystemExit(subprocess.run([sys.executable, '-I', '-B', '-c', code]).returncode)
elif name == 'python3.12' and 'venv' in args:
    venv = Path(args[-1])
    (venv / 'bin').mkdir(parents=True)
    if failure == 'venv':
        raise SystemExit(31)
    shutil.copyfile(sys.argv[0], venv / 'bin/python')
    (venv / 'bin/python').chmod(0o750)
elif name == 'python' and 'pip' in args:
    if failure == 'signal':
        os.kill(os.getppid(), signal.SIGTERM)
    if failure == 'pip':
        raise SystemExit(32)
elif name == 'python' and any('verify_exact_release.py' in arg for arg in args):
    if failure in ('verifier', 'verifier_cleanup'):
        raise SystemExit(33)
elif name == 'python3.12' and any('three_setup_shadow_preflight.py' in arg for arg in args):
    assert '--host-only' in args and '--host-wheel' in args
else:
    raise SystemExit('unexpected target process: ' + repr(args))
"""


@pytest.fixture
def target_fixture(bundle_fixture: dict[str, str], tmp_path: Path) -> dict[str, str]:
    env = dict(bundle_fixture)
    binaries = tmp_path / "target-bin"
    binaries.mkdir()
    for name in ("python3.12", "mktemp", "rm", "systemctl"):
        path = binaries / name
        path.write_text(f"#!{sys.executable}\n" + TARGET_PROCESS_FIXTURE)
        path.chmod(0o750)
    parent = tmp_path / "verification parent"
    parent.mkdir()
    alternate = tmp_path / "alternate"
    alternate.mkdir()
    env.update(
        PATH=f"{binaries}:{os.environ['PATH']}",
        TMPDIR=str(parent),
        ALTERNATE_TEMP=str(alternate),
        PROCESS_RECORD=str(tmp_path / "processes.jsonl"),
        TRADER_ASSIST_V0_DEPLOYMENT_AUTHORIZED="NO",
    )
    return env


def target_run(env: dict[str, str], mode: str = "--verify") -> subprocess.CompletedProcess[str]:
    bundle = Path(env["BUILD_ROOT"]) / "bundle"
    anchors = builder.handoff_anchors(bundle)
    return subprocess.run(
        [
            "bash",
            str(bundle / "remote-qualification.sh"),
            mode,
            anchors["EXPECTED_RELEASE_SHA"],
            anchors["EXPECTED_RELEASE_TREE"],
            anchors["EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"],
            anchors["EXPECTED_BUNDLE_MANIFEST_SHA256"],
        ],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )


def process_records(env: dict[str, str]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(env["PROCESS_RECORD"]).read_text().splitlines()]


@pytest.mark.parametrize(
    "location", ["equal", "beneath", "symlink", "absent", "file", "broken_link", "newline"]
)
def test_temp_parent_rejected_without_bundle_creation(
    target_fixture: dict[str, str], location: str
) -> None:
    env = target_fixture
    bundle = Path(env["BUILD_ROOT"]) / "bundle"
    outside = Path(env["TMPDIR"])
    if location == "equal":
        env["TMPDIR"] = str(bundle)
    elif location == "beneath":
        env["TMPDIR"] = str(bundle / "payload")
    elif location == "symlink":
        link = outside / "link"
        link.symlink_to(bundle / "payload", target_is_directory=True)
        env["TMPDIR"] = str(link)
    elif location == "file":
        env["TMPDIR"] = str(bundle / "bundle-manifest.json")
    elif location == "broken_link":
        link = outside / "broken"
        link.symlink_to(outside / "missing")
        env["TMPDIR"] = str(link)
    elif location == "newline":
        invalid = outside / "bad\nparent"
        invalid.mkdir()
        env["TMPDIR"] = str(invalid)
    else:
        env["TMPDIR"] = str(outside / "absent")
    before = bundle_paths(bundle)
    assert target_run(env).returncode != 0
    assert bundle_paths(bundle) == before
    records = process_records(env)
    assert all(item["name"] != "mktemp" for item in records)
    assert not any("venv" in item["argv"] or "pip" in item["argv"] for item in records)


@pytest.mark.parametrize(
    "failure, status",
    [
        ("", 0),
        ("venv", 31),
        ("pip", 32),
        ("verifier", 33),
        ("signal", 143),
        ("cleanup", 1),
        ("verifier_cleanup", 33),
        ("parent_identity", 1),
        ("allocation_parent", 1),
        ("allocation_symlink", 1),
        ("python_identity", 1),
    ],
)
def test_transient_runtime_orchestration_and_status(
    target_fixture: dict[str, str], failure: str, status: int
) -> None:
    env = target_fixture
    env["PROCESS_FAILURE"] = failure
    bundle = Path(env["BUILD_ROOT"]) / "bundle"
    before = bundle_paths(bundle)
    result = target_run(env)
    assert result.returncode == status, result.stdout + result.stderr
    assert bundle_paths(bundle) == before
    records = process_records(env)
    allocations = [item for item in records if item["name"] == "mktemp"]
    if failure == "python_identity":
        assert not allocations
        return
    assert len(allocations) == 1
    assert allocations[0]["argv"] == [
        "-d",
        str(Path(env["TMPDIR"]).resolve() / "trade-os-verify.XXXXXXXXXX"),
    ]
    cleanups = [item for item in records if item["name"] == "rm"]
    assert len(cleanups) == 1
    allocated = Path(cleanups[0]["argv"][-1])
    assert allocated.exists() == (failure in ("cleanup", "verifier_cleanup"))
    venv_calls = [item for item in records if "venv" in item["argv"]]
    pip_calls = [item for item in records if "pip" in item["argv"]]
    verifier_calls = [
        item for item in records if any("verify_exact_release.py" in arg for arg in item["argv"])
    ]
    if failure in ("parent_identity", "allocation_parent", "allocation_symlink"):
        assert not venv_calls and not pip_calls and not verifier_calls
        return
    assert venv_calls[0]["argv"] == ["-I", "-B", "-m", "venv", str(allocated / "venv")]
    if failure == "venv":
        assert not pip_calls and not verifier_calls
        return
    pip = pip_calls[0]
    assert len(pip_calls) == 1
    assert pip["executable"] == str(allocated / "venv/bin/python")
    assert pip["argv"] == [
        "-I",
        "-m",
        "pip",
        "--isolated",
        "install",
        "--require-hashes",
        "--no-cache-dir",
        "-r",
        str(bundle / "payload/requirements-runtime.lock"),
    ]
    if failure in ("pip", "signal"):
        assert not verifier_calls
        return
    verifier = verifier_calls[0]
    assert len(verifier_calls) == 1
    assert verifier["executable"] == pip["executable"]
    assert verifier["argv"] == [
        "-B",
        str(bundle / "payload/scripts/verify_exact_release.py"),
        "--root",
        str(bundle / "payload"),
        "--verify-staged",
        str(bundle / "release-manifest.json"),
        "--expected-release-sha",
        env["RELEASE_SHA"],
        "--expected-release-tree",
        env["RELEASE_TREE"],
        "--expected-manifest-digest",
        builder.handoff_anchors(bundle)["EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST"],
    ]
    assert verifier["pythonpath"] == f"{bundle}/payload/src:{bundle}/payload"
    assert verifier["no_bytecode"] == "1"
    assert (
        records.index(allocations[0])
        < records.index(venv_calls[0])
        < records.index(pip)
        < records.index(verifier)
        < records.index(cleanups[0])
    )
    if not failure:
        preflight = next(item for item in records if "--host-only" in item["argv"])
        assert preflight["name"] == "python3.12"
        assert records.index(cleanups[0]) < records.index(preflight)


@pytest.mark.parametrize("mutation", ["file", "sha", "tree", "digest"])
def test_independent_checks_precede_bootstrap(
    target_fixture: dict[str, str], mutation: str
) -> None:
    env = target_fixture
    bundle = Path(env["BUILD_ROOT"]) / "bundle"
    if mutation == "file":
        with (bundle / "payload/requirements-runtime.lock").open("a") as lock:
            lock.write("CORRUPTION\n")
    else:
        path = bundle / "bundle-manifest.json"
        manifest = json.loads(path.read_bytes())
        manifest[
            {"sha": "release_sha", "tree": "release_tree", "digest": "release_manifest_digest"}[
                mutation
            ]
        ] = "a" * (64 if mutation == "digest" else 40)
        path.write_bytes(canonical_json_bytes(manifest))
    assert target_run(env).returncode != 0
    records = process_records(env)
    assert len(records) == 1 and records[0]["name"] == "python3.12"


def test_install_authority_refusal_after_transient_cleanup(target_fixture: dict[str, str]) -> None:
    result = target_run(target_fixture, "--install")
    assert result.returncode == 2
    assert "current deployment authorization is required" in result.stderr
    records = process_records(target_fixture)
    cleanup = next(item for item in records if item["name"] == "rm")
    assert not Path(cleanup["argv"][-1]).exists()
    assert not any("/opt/trader-assist-v0/venv" in item["argv"] for item in records)


@pytest.mark.parametrize("value", [None, ""])
def test_unset_or_empty_temp_parent_uses_explicit_fallback(
    target_fixture: dict[str, str], monkeypatch: pytest.MonkeyPatch, value: str | None
) -> None:
    env = target_fixture
    monkeypatch.delenv("TMPDIR", raising=False)
    if value is None:
        env.pop("TMPDIR")
    else:
        env["TMPDIR"] = value
    assert_pass(target_run(env))
    records = process_records(env)
    allocation = next(item for item in records if item["name"] == "mktemp")
    assert allocation["argv"] == ["-d", str(Path("/tmp").resolve() / "trade-os-verify.XXXXXXXXXX")]
    cleanup = next(item for item in records if item["name"] == "rm")
    assert not Path(cleanup["argv"][-1]).exists()


def test_allocation_failure_precedes_runtime_work(target_fixture: dict[str, str]) -> None:
    env = target_fixture
    env["PROCESS_FAILURE"] = "mktemp"
    parent = Path(env["TMPDIR"])
    before = set(parent.iterdir())
    result = target_run(env)
    assert result.returncode == 37
    assert set(parent.iterdir()) == before
    records = process_records(env)
    assert records[-1]["name"] == "mktemp"
    assert not any(item["name"] == "rm" or "venv" in item["argv"] for item in records)



def simulation_namespace() -> dict[str, Any]:
    code = python_block("simulation")
    assert code.endswith("main()")
    namespace: dict[str, Any] = {}
    exec(compile(code.removesuffix("main()"), "simulation-functions", "exec"), namespace)
    return namespace


def test_disposable_simulation_composition() -> None:
    job = parse_workflow(WORKFLOW.read_text())["jobs"]["build-release-bundle"]
    ids = [step.get("id") for step in job["steps"]]
    assert ids.index("transport") < ids.index("simulation") < ids.index("terminal")
    assert ids.index("simulation") < len(ids) - 1
    code = python_block("simulation")
    for required in (
        "root / 'three-setup-release-bundle.tar.gz'", "'--same-permissions'",
        "'--no-same-owner'", "len(lines) == 5", "mode) == 0o750",
        "digest(script) == anchors[KEYS[4]]", "digest(bundle / 'bundle-manifest.json')",
        "provenance['control_head']", "execute('--verify')", "execute('--install')",
        "env['TMPDIR'] = str(temp)", "temp.glob('trade-os-verify.*')",
        "identity('passwd') is None and identity('group') is None",
        "'groupadd', '--system'", "'useradd', '--system', '--no-create-home'",
        "TRADER_ASSIST_V0_DEPLOYMENT_AUTHORIZED=YES", "--verify-target-runtime-installed",
        "--expected-release-sha", "--expected-release-tree", "--expected-manifest-digest",
        "cost_model", "NOT_QUALIFIED", "three-setup-activation-permit",
        "TRADER_ASSIST_V0_THREE_SETUP_ENABLE", "TRADER_ASSIST_V0_THREE_SETUP_MODE",
        "== '0'", "== 'DISABLED'", "finally:", "status = status or 1",
        "assert digest(archive) == original_digest", "simulation-archive.sha256",
        "include-system-site-packages = false", "--pip-check-with",
    ):
        assert required in code
    assert code.index("try:\n        scratch") < code.index("'groupadd', '--system'")
    assert code.index("execute('--verify')") < code.index("'groupadd', '--system'")
    assert code.index("execute('--install')") < code.index("errors = cleanup(")
    assert "root / 'bundle'" not in code and "builder-stdout" not in code
    assert "apt-get" not in code and "brew install" not in code
    assert code.count("TRADER_ASSIST_V0_DEPLOYMENT_AUTHORIZED=YES") == 1
    assert "record.is_file()" in steps()["terminal"]["run"]


@pytest.mark.parametrize("mutation", ["none", "hash", "anchors", "unsafe_member"])
def test_simulation_final_archive_preflight(
    bundle_fixture: dict[str, str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    env = bundle_fixture
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    assert_pass(python_run("anchors", env))
    assert_pass(python_run("transport", env))
    root = Path(env["BUILD_ROOT"])
    archive = root / "three-setup-release-bundle.tar.gz"
    original = archive.read_bytes()
    if mutation != "none":
        with tarfile.open(archive, "r:gz") as source:
            members = [(member, source.extractfile(member).read() if member.isfile() else None)
                       for member in source.getmembers()]
        import io
        with tarfile.open(archive, "w:gz") as target:
            for member, data in members:
                if mutation == "hash" and member.name == "bundle/remote-qualification.sh":
                    data += b"\n# changed\n"
                    member.size = len(data)
                if mutation == "anchors" and member.name == "handoff/anchors.env":
                    data += b"EXTRA=bad\n"
                    member.size = len(data)
                target.addfile(member, io.BytesIO(data) if data is not None else None)
            if mutation == "unsafe_member":
                member = tarfile.TarInfo("../escape")
                member.size = 1
                target.addfile(member, io.BytesIO(b"x"))
    # Execution authority must survive removal of the mutable builder bundle.
    shutil.rmtree(root / "bundle")
    stage = tmp_path / "simulation staging"
    stage.mkdir()
    namespace = simulation_namespace()
    if mutation == "none":
        anchors = namespace["extract"](archive, stage)
        assert len(anchors) == 5
        assert stat_mode(stage / "bundle/remote-qualification.sh") == 0o750
        assert archive.read_bytes() == original
    else:
        with pytest.raises(AssertionError):
            namespace["extract"](archive, stage)
        if mutation == "unsafe_member":
            assert not list(stage.iterdir())


def test_simulation_cleanup_owned_inventory(tmp_path: Path) -> None:
    namespace = simulation_namespace()
    created = tmp_path / "created"
    created.mkdir()
    sentinel = tmp_path / "preexisting"
    sentinel.write_text("preserve")
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    namespace["DESTINATIONS"] = (created,)
    calls = []
    records = {"passwd": "user-record", "group": "group-record"}
    namespace["identity"] = lambda kind: records[kind]
    def fake_run(args: list[str]) -> None:
        calls.append(args)
        assert args[:2] == ["sudo", "-n"]
        if args[2] == "rm":
            path = Path(args[-1])
            assert path in (created, scratch)
            shutil.rmtree(path)
        else:
            records["passwd" if args[2] == "userdel" else "group"] = None
    namespace["run"] = fake_run
    assert namespace["cleanup"](True, "user-record", "group-record", scratch) == []
    assert not created.exists() and not scratch.exists()
    assert sentinel.read_text() == "preserve"
    assert [call[2] for call in calls] == ["rm", "userdel", "groupdel", "rm"]
    calls.clear()
    assert namespace["cleanup"](False, None, None, None) == []
    assert not calls
    def failed_run(args: list[str]) -> None:
        raise OSError("cleanup failed")
    namespace["run"] = failed_run
    assert namespace["cleanup"](True, None, None, None)


@pytest.mark.parametrize("original_status", [0, 37])
def test_simulation_cleanup_failure_preserves_original_status(original_status: int) -> None:
    namespace = simulation_namespace()
    tree = ast.parse(python_block("simulation"))
    main = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    guarded = next(node for node in main.body if isinstance(node, ast.Try))
    # Execute the actual finally status logic, excluding its signal-handler teardown.
    namespace.update(
        status=original_status, install_owned=False, user_record=None, group_record=None,
        scratch=None, archive=None, original_digest="unchanged",
        cleanup=lambda *args: ["cleanup failed"], digest=lambda path: "unchanged",
    )
    block = ast.Module(body=guarded.finalbody[1:], type_ignores=[])
    exec(compile(ast.fix_missing_locations(block), "simulation-cleanup-status", "exec"), namespace)
    assert namespace["status"] == (original_status or 1)


def test_generated_installer_pipless_target_contract_and_all_guards() -> None:
    script = builder._remote_script("exact-rc5.whl")
    first_write = script.index("install -d -m 0750 -g traderassist /opt/trader-assist-v0")
    provider = script.index("PIP_SCRATCH_RECORD=")
    bootstrap = script.index('python3.12 -I -B -m venv "$PIP_PROVIDER_SCRATCH/pip-provider"')
    original_guards = (
        "BUNDLE_HASH_VERIFY=PASS", "STAGED_RELEASE_VERIFY=PASS",
        "SERVICE_STATE=", "activation permit exists",
        "PREINSTALL_VERIFY=PASS", "current deployment authorization is required",
        "existing install requires separate rollback handling",
        "existing config requires separate rollback handling",
        "existing env requires separate rollback handling",
        "existing traderassist service identity is required",
        "existing traderassist group is required",
        "existing durable state requires separately reviewed replacement",
    )
    assert all(script.index(gate) < provider for gate in original_guards)
    assert provider < bootstrap < first_write
    assert script.index('"$PIP_PROVIDER_SCRATCH/pip-provider/bin/python" -I -m pip --version') < first_write
    target = "/opt/trader-assist-v0/venv/bin/python"
    assert f"python3.12 -m venv --without-pip /opt/trader-assist-v0/venv" in script
    assert script.count(
        f'"$PIP_PROVIDER_SCRATCH/pip-provider/bin/python" -m pip --python {target} install --require-hashes'
    ) == 2
    assert "python3.12 -m pip" not in script
    assert "get-pip.py" not in script and "apt-get" not in script
    assert "--no-deps --only-binary=:all: --no-index --find-links" in script
    assert '--pip-check-with "$PIP_PROVIDER_SCRATCH/pip-provider/bin/python"' in script
    assert "shutil.rmtree(scratch.name, dir_fd=parent_fd)" in script
    assert "os.O_NOFOLLOW" in script and "owned.st_ino" in script
    assert script.count('echo "INSTALL_VERIFIED=PASS; SERVICE=STOPPED; ACTIVATION=DEFAULT_OFF"') == 1
    assert script.index("pip_provider_exit()") < first_write
    assert script.index('[[ "1" == "--install" ]] || exit 0') < provider


@pytest.mark.skipif(sys.platform != "linux", reason="authoritative Linux CPython3.12 only")
@pytest.mark.parametrize(
    "failure", ["success", "no_venv", "no_pip", "bad_parent", "changed_mode", "symlink_swap"]
)
def test_provider_bootstrap_owns_only_scratch_and_fails_before_app_write(
    tmp_path: Path, failure: str,
) -> None:
    """Run exactly the generated bootstrap+cleanup region, without /opt or /etc."""
    assert sys.version_info[:2] == (3, 12)
    import shlex

    script = builder._remote_script("exact-rc5.whl")
    start = script.index("# One verified, exclusively owned scratch venv")
    stop = script.index("install -d -m 0750 -g traderassist /opt/trader-assist-v0")
    isolated = script[start:stop]
    bindir = tmp_path / "bin"
    bindir.mkdir()
    system = bindir / "python3.12"
    system.write_text(
        "#!/bin/sh\n"
        "if [ \"$1\" = -m ] && [ \"$2\" = pip ]; then exit 97; fi\n"
        "if [ \"$1\" = -I ] && [ \"$2\" = -B ] && [ \"$3\" = -m ] "
        "&& [ \"$4\" = venv ]; then\n"
        + ("  exit 42\n" if failure == "no_venv" else
           "  exit 0\n" if failure == "no_pip" else "  :\n")
        + "fi\n"
        + f"exec {shlex.quote(sys.executable)} \"$@\"\n"
    )
    system.chmod(0o700)
    parent = tmp_path / "scratch"
    parent.mkdir()
    if failure == "bad_parent":
        swapped = tmp_path / "real-parent"
        swapped.mkdir()
        parent.rmdir()
        parent.symlink_to(swapped, target_is_directory=True)
    probe = tmp_path / "durable-write-marker"
    if failure == "changed_mode":
        isolated += '\nchmod 0777 "$PIP_PROVIDER_SCRATCH"\n'
    if failure == "symlink_swap":
        isolated += (
            '\nmv "$PIP_PROVIDER_SCRATCH" "$PIP_PROVIDER_SCRATCH-original"\n'
            'ln -s "$PIP_PROVIDER_SCRATCH-original" "$PIP_PROVIDER_SCRATCH"\n'
        )
    isolated += '\nprintf "WRITE" > "$PROBE_WRITE"\n'
    result = subprocess.run(
        ["bash", "-c", "set -euo pipefail\n" + isolated],
        env={**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}",
             "TMPDIR": str(parent), "PROBE_WRITE": str(probe)},
        capture_output=True, text=True, timeout=80,
    )
    if failure == "success":
        assert result.returncode == 0, result.stdout + result.stderr
        assert probe.read_text() == "WRITE"
        assert "INSTALL_VERIFIED=PASS" in result.stdout
        assert not list(parent.iterdir())
    else:
        assert result.returncode != 0, result.stdout + result.stderr
        assert "INSTALL_VERIFIED=PASS" not in result.stdout
        if failure in ("no_venv", "no_pip", "bad_parent"):
            assert not probe.exists() and not list(parent.iterdir())
        else:
            assert "PIP_PROVIDER_CLEANUP_FAILED" in result.stderr
            assert probe.read_text() == "WRITE"
            assert list(parent.iterdir())
