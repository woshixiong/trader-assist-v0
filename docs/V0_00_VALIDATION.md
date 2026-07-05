# V0-00 Local Validation Evidence

Validation environment:

- observed date: 2026-07-06;
- Python: 3.13 local validation environment;
- install: fresh virtual environment with `python -m pip install -e '.[dev]'`;
- credential state: `ABSENT_BY_DESIGN`;
- exchange/network execution: none.

Observed passing commands:

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q
```

Observed results:

```text
secret scan: clean
All checks passed!
Success: no issues found in 12 source files
18 passed
```

GitHub Actions CI is not yet observed because the target repository does not exist. The bundled workflow targets Python 3.12 and must pass on the future pull request before merge.
