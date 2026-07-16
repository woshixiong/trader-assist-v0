from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "control" / "tooling_preflight.py"
SCHEMA_PATH = ROOT / "schemas" / "control" / "execution-launch-packet-v1.schema.json"
SPEC = importlib.util.spec_from_file_location("tooling_preflight", SCRIPT)
assert SPEC and SPEC.loader
tooling = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tooling)


def completed(argv: list[str], **_: object) -> subprocess.CompletedProcess[str]:
    if "config" in argv:
        stdout = "https://github.com/woshixiong/trader-assist-v0.git\n"
    elif "branch" in argv:
        stdout = "codex/test\n"
    elif "rev-parse" in argv:
        stdout = "a" * 40 + "\n"
    elif "status" in argv:
        stdout = ""
    else:
        stdout = "ok\n"
    return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr="")


def args(*extra: str) -> object:
    return tooling.parser().parse_args(
        [
            "--repository",
            str(ROOT),
            "--expected-origin",
            "https://github.com/woshixiong/trader-assist-v0.git",
            "--expected-branch",
            "codex/test",
            "--expected-head",
            "a" * 40,
            "--target-role",
            "WRITER",
            "--capability",
            "LOCAL_EXECUTION",
            "--codex-quota-state",
            "GE_30",
            "--available-route",
            "CODEX",
            "--required-tool",
            "python",
            *extra,
        ]
    )


def validate(packet: dict[str, object]) -> None:
    schema = json.loads(SCHEMA_PATH.read_text())
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(packet)


def test_schema_self_validation_and_packet_contract() -> None:
    packet = tooling.build_packet(args(), runner=completed)
    validate(packet)
    for field in ("PACKET_VERSION", "TARGET_ROLE", "SIDE_EFFECTS"):
        broken = dict(packet)
        broken.pop(field)
        with pytest.raises(ValidationError):
            validate(broken)
    extra = dict(packet)
    extra["EXTRA"] = True
    with pytest.raises(ValidationError):
        validate(extra)
    invalid = dict(packet)
    invalid["SELECTED_ROUTE"] = "BAD"
    with pytest.raises(ValidationError):
        validate(invalid)


def test_text_order_json_output_and_equivalence(capsys: pytest.CaptureFixture[str]) -> None:
    packet = tooling.build_packet(args(), runner=completed)
    tooling.main(
        [
            "--repository",
            str(ROOT),
            "--expected-origin",
            "https://github.com/woshixiong/trader-assist-v0.git",
            "--expected-branch",
            "",
            "--expected-head",
            "",
            "--target-role",
            "WRITER",
            "--capability",
            "X",
            "--codex-quota-state",
            "GE_30",
            "--deterministic-complete",
        ]
    )
    assert [line.split(":", 1)[0] for line in capsys.readouterr().out.splitlines()] == list(
        tooling.TEXT_FIELDS
    )
    tooling.main(
        [
            "--repository",
            str(ROOT),
            "--expected-origin",
            "",
            "--expected-branch",
            "",
            "--expected-head",
            "",
            "--target-role",
            "WRITER",
            "--capability",
            "X",
            "--codex-quota-state",
            "GE_30",
            "--deterministic-complete",
            "--output",
            "json",
        ]
    )
    validate(json.loads(capsys.readouterr().out))
    assert tooling.build_packet(args(), runner=completed) == packet
    validate(packet)


@pytest.mark.parametrize(
    ("role", "quota", "available", "flags", "selected"),
    [
        ("WRITER", "GE_30", ["CODEX"], [], "CODEX"),
        ("WRITER", "LT_30_GE_10", ["DEEPSEEK_CLAUDE_CODE"], [], "DEEPSEEK_CLAUDE_CODE"),
        ("WRITER", "LT_10", ["CODEX"], [], "NONE"),
        ("WRITER", "LT_10", ["CODEX"], ["--critical-blocker"], "CODEX"),
        ("WRITER", "UNKNOWN", ["CODEX"], [], "NONE"),
        ("PROJECT_CONTROL", "UNKNOWN", ["CHATGPT"], ["--connector-sufficient"], "CHATGPT"),
        ("REVIEWER", "GE_30", ["CHATGPT"], ["--connector-sufficient"], "CHATGPT"),
        (
            "REVIEWER",
            "GE_30",
            ["CODEX"],
            ["--connector-sufficient", "--checkout-required"],
            "CODEX",
        ),
        ("WRITER", "GE_30", ["TRAE"], ["--complex-environment-failure"], "TRAE"),
    ],
)
def test_routing(
    role: str, quota: str, available: list[str], flags: list[str], selected: str
) -> None:
    available_flags = [item for route in available for item in ("--available-route", route)]
    packet = tooling.build_packet(
        args(
            "--target-role",
            role,
            "--codex-quota-state",
            quota,
            *available_flags,
            *flags,
        ),
        runner=completed,
    )
    assert packet["SELECTED_ROUTE"] == selected
    assert selected in packet["CANDIDATE_ROUTES"]
    assert packet["REVIEWER_ISOLATION"] == (
        "REQUIRED_NEW_READ_ONLY_CONTEXT" if role == "REVIEWER" else "NOT_APPLICABLE"
    )


def test_deterministic_route_and_no_unavailable_selection() -> None:
    candidates, selected, _ = tooling.select_route(
        "WRITER", "UNKNOWN", [], True, False, False, False, False, False, False
    )
    assert (candidates, selected) == (["DETERMINISTIC_SCRIPT"], "DETERMINISTIC_SCRIPT")
    candidates, selected, _ = tooling.select_route(
        "WRITER", "GE_30", [], False, False, False, False, False, False, False
    )
    assert (candidates, selected) == (["NONE"], "NONE")


def test_tooling_failures_are_shell_free_bounded_and_sanitized() -> None:
    def failed(argv: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        assert kwargs["shell"] is False
        if argv[0] in {"missing", "/missing"}:
            raise OSError("token=very-secret")
        return completed(argv, **kwargs)

    reuse, failures = tooling.tooling_preflight(["python"], "/missing", ROOT, runner=failed)
    assert reuse and failures[0]["COMMAND_ARGV"] == ["/missing", "--version"]
    assert failures[0]["EXIT_CODE"] == -1
    code, stderr = tooling.run_readonly(["missing", "--version"], runner=failed)
    assert code == -1 and "very-secret" not in stderr and "[REDACTED]" in stderr
    assert len(stderr) <= 1000


def test_object_drift_and_actions_routes() -> None:
    packet = tooling.build_packet(args("--expected-head", "b" * 40), runner=completed)
    assert packet["PREFLIGHT_STATUS"] == "OBJECT_DRIFT"
    assert tooling.action_evidence("o", "r", "123", None, True, False) == (
        "CONNECTOR_KNOWN_RUN_ID",
        "123",
    )
    assert tooling.action_evidence(
        "o", "r", None, "https://github.com/o/r/actions/runs/456", True, False
    ) == ("CONNECTOR_RUN_URL", "456")
    for bad in (
        "https://github.com/o/r/actions/runs/x",
        "https://evil.github.com/o/r/actions/runs/1",
        "https://github.com/o/r/actions/runs/1/extra",
        "https://github.com/x/r/actions/runs/1#f",
    ):
        assert tooling.action_evidence("o", "r", None, bad, True, True) == ("UNAVAILABLE", None)
    assert tooling.action_evidence("o", "r", None, None, False, True) == ("GH_FALLBACK", None)
    assert tooling.action_evidence("o", "r", None, None, False, False) == ("UNAVAILABLE", None)


def test_no_prohibited_side_effect_commands() -> None:
    source = SCRIPT.read_text()
    forbidden = (
        "git fetch",
        "git pull",
        "git checkout",
        "git switch",
        "git reset",
        "git commit",
        "git push",
        "pip install",
        "gh pr create",
        "gh pr merge",
        "gh run rerun",
    )
    assert not any(command in source for command in forbidden)
