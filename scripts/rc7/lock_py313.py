"""Resolve compatible wheel hashes, preserving all accepted dev versions.

Run only in an isolated Linux CPython 3.13 environment. Resolution downloads
wheels; it does not install them or change the Python 3.12 environment.
"""

from __future__ import annotations

import hashlib
import platform
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    assert sys.version_info[:2] == (3, 13)
    assert platform.system() == "Linux" and platform.machine() == "x86_64"
    root = Path(__file__).resolve().parents[2]
    pins = [
        line.split(" --hash=")[0]
        for line in (root / "requirements-dev.lock").read_text().splitlines()
        if line and not line.startswith("#")
    ]
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        requirements = folder / "pins.txt"
        requirements.write_text("\n".join(pins) + "\n")
        subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--only-binary=:all:",
                "--no-deps",
                "--dest",
                str(folder),
                "-r",
                str(requirements),
            ],
            check=True,
        )
        hashes = {}
        for wheel in folder.glob("*.whl"):
            name, version, *_ = wheel.name.split("-")
            hashes[f"{name.replace('_', '-').lower()}=={version}"] = hashlib.sha256(
                wheel.read_bytes()
            ).hexdigest()
        assert set(hashes) == {pin.lower().replace("_", "-") for pin in pins}
        lines = [f"{pin} --hash=sha256:{hashes[pin.lower().replace('_', '-')]}" for pin in pins]
        (root / "requirements-dev-py313.lock").write_text(
            "# Platform lock: CPython 3.13 / Linux x86_64\n"
            "# Exact accepted dev versions; native-compatible official wheel hashes.\n"
            + "\n".join(lines)
            + "\n"
        )


if __name__ == "__main__":
    main()
