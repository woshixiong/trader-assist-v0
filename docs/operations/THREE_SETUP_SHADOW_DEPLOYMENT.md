# Three Setup Shadow exact-release handoff

This procedure prepares and qualifies a public-data-only, NOT_SUBMITTED candidate.
It grants no deployment, service, credential, exchange, or trading authority. Obtain
current Operations and human authorization before any target installation or start.

1. Engineering records the reviewed full release SHA and tree, exact-head CI, and
   the authorized E4/PIT/Registry identity. Use the accepted rc5 Linux CPython 3.12
   wheel whose bytes match `requirements-nautilus-pilot.lock`. The operator provides
   reviewed exact 1m/5m external LAST bar types and cost-model version. Generate
   one folder locally with `scripts/build_three_setup_shadow_deployment_bundle.py`
   using `--expected-sha`, `--expected-tree`, `--rc5-wheel`, `--bar-type-1m`,
   `--bar-type-5m`, `--cost-model-version`, and an empty `--output` path outside
   the repository. The generator requires a clean exact Git candidate.
2. Upload that single folder unchanged through FinalShell SFTP to the unique
   `upload_path` in `bundle-manifest.json`. Do not mix it with a prior folder.
3. In the already-connected FinalShell terminal, run `remote-qualification.sh
   --verify` from that folder. It verifies all transferred hashes, exact SHA/tree,
   stopped service, absent activation permit, Linux/x86_64/Python 3.12, glibc
   compatibility and the locked rc5 wheel hash before installation.
4. Only after a separate current deployment authorization, run that same script
   with `--install` and the explicit authorization setting described in the
   generated script. It refuses an existing `/opt/trader-assist-v0` install;
   replacement requires a separately reviewed rollback plan. Installation uses
   the runtime lock with hashes, the pilot lock with hashes, `--no-deps` and
   `--only-binary`, and `PYTHONPATH` source rather than project installation.
   The service and activation permit remain off/absent. A failed install must
   leave the service stopped; record cleanup or rollback evidence before retry.
5. Operations supplies matching E4 durable run manifest/PIT snapshot and a
   validated Registry through their existing authority. Before any service
   start, run `three_setup_shadow_preflight.py` with the exact staged root,
   retained release manifest, concrete config, and independently expected SHA
   and tree. Run `run_three_setup_shadow_runtime.py --validate-only` with the
   same identity arguments; it needs no notification secret. Record the actual
   target venv closure, `pip check`, import origin and preflight result.
6. A later, separately authorized activation provides external permit,
   enable/mode and a systemd notification credential file. The unchanged unit
   invokes only the wrapper and retains `Restart=no`. The wrapper repeats the
   candidate preflight before normal runtime. A failure keeps the service
   stopped/default-off; do not create a permit or restart automatically.

Copy the non-secret qualification evidence schema in
`deploy/p4a/evidence/three-setup-shadow-qualification-manifest-v1.json.example`.
Record exact release and bundle hashes, service/permit state before and after,
host and venv proof, validate-only result, and rollback result. Never include
credential values, private data, tokens, keys, production DBs or raw logs.
After merge, Q1 separately observes the public Nautilus probe, bounded
NOT_SUBMITTED process, readiness and cohort behavior, recovery, outbox and
SQLite integrity. A local or CI PASS is not target-host or Q1 evidence.
