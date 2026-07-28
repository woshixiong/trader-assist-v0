from __future__ import annotations

import importlib.util
import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from trader_assist_v0.first_launch.configuration import ConfigurationError, RiskConfiguration

_RUNTIME_SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "scripts"
    / "run_first_launch_public_runtime.py"
)
_RUNTIME_SPEC = importlib.util.spec_from_file_location(
    "test_first_launch_configuration_runtime_script",
    _RUNTIME_SCRIPT,
)
assert _RUNTIME_SPEC is not None
assert _RUNTIME_SPEC.loader is not None
_RUNTIME_MODULE = importlib.util.module_from_spec(_RUNTIME_SPEC)
sys.modules[_RUNTIME_SPEC.name] = _RUNTIME_MODULE
_RUNTIME_SPEC.loader.exec_module(_RUNTIME_MODULE)


def test_strict_external_configuration_and_hard_cap() -> None:
    config = RiskConfiguration.from_json(
        '{"CONFIGURATION_VERSION":"r3.0","ACCOUNT_EQUITY_USD":"100.00",'
        '"RISK_PER_TRADE_PCT":"0.2500","MAX_NOTIONAL_USD":null}'
    )
    assert config.effective_max_notional == Decimal("2500.00")
    assert config.configuration_hash == RiskConfiguration.digest(
        "r3.0", Decimal("100.00"), Decimal("0.2500"), None
    )


@pytest.mark.parametrize(
    "raw",
    (
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":100,"RISK_PER_TRADE_PCT":"0.25","MAX_NOTIONAL_USD":null}',
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":"100.00","RISK_PER_TRADE_PCT":"2e-1","MAX_NOTIONAL_USD":null}',
        '{"CONFIGURATION_VERSION":"r","ACCOUNT_EQUITY_USD":"100.00","RISK_PER_TRADE_PCT":"0.25","MAX_NOTIONAL_USD":"10.00","extra":null}',
    ),
)
def test_configuration_rejects_coercion_and_extra_keys(raw: str) -> None:
    with pytest.raises(ConfigurationError):
        RiskConfiguration.from_json(raw)


def _write_notification_credential(
    path: Path,
    *,
    mode: int = 0o600,
    webhook_url: str = "https://hooks.example.com/notify",
) -> Path:
    path.write_text(
        json.dumps(
            {
                "version": 1,
                "webhook_url": webhook_url,
                "authorization_header": None,
            }
        ),
        encoding="utf-8",
    )
    path.chmod(mode)
    return path


def _load_notification_credential(path: Path) -> Any:
    return _RUNTIME_MODULE._load_credential_file(path, 10.0)


def _set_systemd_credential_context(
    monkeypatch: pytest.MonkeyPatch,
    directory: Path,
    *,
    acl_present: bool = True,
) -> None:
    monkeypatch.setenv("CREDENTIALS_DIRECTORY", str(directory))
    monkeypatch.setattr(
        _RUNTIME_MODULE,
        "_credential_has_posix_access_acl",
        lambda _path: acl_present,
    )


def test_static_notification_credential_0600_remains_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    credential = _write_notification_credential(tmp_path / "notification.json")
    config = _load_notification_credential(credential)
    assert config.webhook_url == "https://hooks.example.com/notify"


def test_static_group_read_notification_credential_remains_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    monkeypatch.setattr(
        _RUNTIME_MODULE,
        "_credential_has_posix_access_acl",
        lambda _path: True,
    )
    credential = _write_notification_credential(
        tmp_path / "notification.json", mode=0o640
    )
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


def test_exact_systemd_credential_acl_mask_group_read_is_accepted(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    credential = _write_notification_credential(
        credentials_directory / "notification.json", mode=0o440
    )
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    config = _load_notification_credential(credential)
    assert config.webhook_url == "https://hooks.example.com/notify"


@pytest.mark.parametrize("mode", (0o460, 0o450))
def test_systemd_credential_group_write_or_execute_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: int,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    credential = _write_notification_credential(
        credentials_directory / "notification.json", mode=mode
    )
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


@pytest.mark.parametrize("mode", (0o444, 0o442, 0o441))
def test_systemd_credential_any_other_access_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mode: int,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    credential = _write_notification_credential(
        credentials_directory / "notification.json", mode=mode
    )
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


def test_systemd_credential_wrong_parent_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    wrong_directory = tmp_path / "wrong"
    wrong_directory.mkdir()
    credential = _write_notification_credential(
        wrong_directory / "notification.json", mode=0o440
    )
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


def test_systemd_credential_wrong_basename_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    credential = _write_notification_credential(
        credentials_directory / "other.json", mode=0o440
    )
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


def test_systemd_credential_without_posix_acl_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    credential = _write_notification_credential(
        credentials_directory / "notification.json", mode=0o440
    )
    _set_systemd_credential_context(
        monkeypatch,
        credentials_directory,
        acl_present=False,
    )
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="group or other access bits",
    ):
        _load_notification_credential(credential)


def test_systemd_credential_symlink_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credentials_directory = tmp_path / "credentials"
    credentials_directory.mkdir()
    target = _write_notification_credential(
        credentials_directory / "target.json", mode=0o600
    )
    credential = credentials_directory / "notification.json"
    credential.symlink_to(target)
    _set_systemd_credential_context(monkeypatch, credentials_directory)
    with pytest.raises(_RUNTIME_MODULE.CredentialFileError, match="symlink"):
        _load_notification_credential(credential)


def test_notification_credential_wrong_owner_remains_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential = _write_notification_credential(tmp_path / "notification.json")
    real_fstat = os.fstat
    wrong_uid = next(
        candidate
        for candidate in (1, 2, 3)
        if candidate not in {0, os.geteuid()}
    )

    def wrong_owner_fstat(fd: int) -> os.stat_result:
        result = real_fstat(fd)
        return os.stat_result(
            (
                result.st_mode,
                result.st_ino,
                result.st_dev,
                result.st_nlink,
                wrong_uid,
                result.st_gid,
                result.st_size,
                result.st_atime,
                result.st_mtime,
                result.st_ctime,
            )
        )

    monkeypatch.setattr(_RUNTIME_MODULE.os, "fstat", wrong_owner_fstat)
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="owner is not root or effective user",
    ):
        _load_notification_credential(credential)


def test_notification_credential_oversize_remains_rejected(
    tmp_path: Path,
) -> None:
    credential = _write_notification_credential(
        tmp_path / "notification.json",
        webhook_url="https://hooks.example.com/" + "x" * 5000,
    )
    with pytest.raises(
        _RUNTIME_MODULE.CredentialFileError,
        match="bounded size",
    ):
        _load_notification_credential(credential)


def test_credential_acl_detection_requires_named_posix_access_acl(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential = _write_notification_credential(tmp_path / "notification.json")
    monkeypatch.setattr(
        _RUNTIME_MODULE.os,
        "listxattr",
        lambda _path, *, follow_symlinks: ["system.posix_acl_access"],
    )
    assert _RUNTIME_MODULE._credential_has_posix_access_acl(credential) is True


def test_credential_acl_detection_rejects_unrelated_xattr(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    credential = _write_notification_credential(tmp_path / "notification.json")
    monkeypatch.setattr(
        _RUNTIME_MODULE.os,
        "listxattr",
        lambda _path, *, follow_symlinks: ["user.example"],
    )
    assert _RUNTIME_MODULE._credential_has_posix_access_acl(credential) is False


def test_notification_credential_error_does_not_expose_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret_url = "https://secret.example.com/private-token"
    monkeypatch.delenv("CREDENTIALS_DIRECTORY", raising=False)
    credential = _write_notification_credential(
        tmp_path / "notification.json",
        mode=0o640,
        webhook_url=secret_url,
    )
    with pytest.raises(_RUNTIME_MODULE.CredentialFileError) as exc_info:
        _load_notification_credential(credential)
    assert secret_url not in str(exc_info.value)
