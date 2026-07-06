# V0-00 Validation Evidence

## Validation environment

- target interpreter: CPython 3.12;
- locked platform: Linux x86_64;
- credential state: `ABSENT_BY_DESIGN`;
- exchange/network execution: none;
- PR CI must fetch and detach-checkout the exact pull-request head SHA.

## Dependency integrity

The repository freezes two platform-specific, wheel-hashed closures:

- `requirements-runtime.lock`: complete runtime closure;
- `requirements-dev.lock`: complete CI/dev/build closure and exact superset of runtime.

CI creates a clean virtual environment and installs the CI/dev/build closure with
`pip install --require-hashes`. `scripts/check_dependency_lock.py --verify-installed`
then verifies:

- every lock entry is exactly pinned and carries one SHA-256 wheel hash;
- all direct project, development and build dependencies match `pyproject.toml`;
- the runtime lock is an exact hashed subset of the CI/dev/build lock;
- the installed distribution names and versions equal the locked closure plus the
  editable `trader-assist-v0` package;
- no unlocked distribution remains in the validation environment.

The runtime lock is separately checked with strict `pip-audit`.

## Authority-boundary validation

Execution authority does not trust a caller-provided Pydantic instance merely because
its Python type is correct. Authority consumers serialize and revalidate the exact
concrete class, recompute its canonical self-hash and reassert permission invariants.
Adversarial regressions cover explicit `BaseModel` and `super()` copy/construct paths,
TypeAdapter validation and JSON round trips.

A raw `PromotionRecordV0` never grants execution authority. Its compatibility
`execution_enabled_at()` method fails closed. Execution authority is derived only from
a complete, exact-class-revalidated promotion history whose predecessor links, subject,
legal transitions and terminal time window all validate.

## Decimal wire contract

Order-critical Decimal fields serialize as strings. Generated Draft 2020-12 schemas
use distinct positive and nonnegative decimal-string patterns matching runtime sign and
zero semantics. Dynamic tick/lot alignment remains a runtime cross-field invariant and
fails closed on invalid decimal arithmetic.

## Required gates

```text
python -m compileall -q src scripts tests
python scripts/export_schemas.py --check
python scripts/scan_secrets.py .
ruff check .
mypy src scripts
pytest -q
git diff --check
```

Remote CI success on the exact current PR head is required before external independent
review. Local or same-workstream results never substitute for that review, do not
authorize merge and do not authorize V0-01.
