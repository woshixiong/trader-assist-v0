# V0-00 Validation Evidence

## Local validation

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

Observed local results:

```text
secret scan: clean
All checks passed!
Success: no issues found in 12 source files
18 passed
```

## Remote validation

The GitHub Actions workflow targets Python 3.12 and runs the same compile, schema-drift, secret, lint, type and test gates. Remote CI must pass on the exact pull-request head before merge. Local results do not substitute for GitHub CI or independent review.
