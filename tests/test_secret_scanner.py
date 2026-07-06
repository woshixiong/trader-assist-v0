from pathlib import Path

from scripts.scan_secrets import scan


def test_secret_scanner_detects_private_key(tmp_path: Path):
    (tmp_path / "bad.txt").write_text("-----BEGIN " + "PRIVATE KEY-----\n", encoding="utf-8")
    assert scan(tmp_path)


def test_secret_scanner_ignores_normal_security_prose(tmp_path: Path):
    (tmp_path / "ok.txt").write_text("Never commit a private key or API key.", encoding="utf-8")
    assert scan(tmp_path) == []
