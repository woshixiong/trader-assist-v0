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
2. Preserve the generator's five `EXPECTED_*` values in the canonical reviewed
   Engineering/Operations handoff, independently of the transfer folder. They
   are the expected release SHA, tree, release-manifest canonical digest,
   bundle-manifest raw SHA256 and remote-qualification script raw SHA256. Never
   obtain expected values from the uploaded folder. Upload that single folder
   unchanged through FinalShell SFTP to the reviewed unique upload path. Do not
   mix it with a prior folder.
3. In the already-connected FinalShell terminal, use the five values copied
   from the canonical reviewed handoff in this bounded pre-execution block.
   Substitute the reviewed absolute upload path; keep the values outside the
   uploaded folder. No uploaded code runs until both raw hashes match:

   ```bash
   set -euo pipefail
   BUNDLE_ROOT=/tmp/trade-os-deploy-ts7-REVIEWED_SHA_PREFIX
   EXPECTED_RELEASE_SHA=REVIEWED_40_LOWERCASE_SHA
   EXPECTED_RELEASE_TREE=REVIEWED_40_LOWERCASE_TREE
   EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST=REVIEWED_64_LOWERCASE_DIGEST
   EXPECTED_BUNDLE_MANIFEST_SHA256=REVIEWED_64_LOWERCASE_DIGEST
   EXPECTED_REMOTE_QUALIFICATION_SHA256=REVIEWED_64_LOWERCASE_DIGEST
   test "$(sha256sum "$BUNDLE_ROOT/bundle-manifest.json" | cut -d ' ' -f 1)" = "$EXPECTED_BUNDLE_MANIFEST_SHA256"
   test "$(sha256sum "$BUNDLE_ROOT/remote-qualification.sh" | cut -d ' ' -f 1)" = "$EXPECTED_REMOTE_QUALIFICATION_SHA256"
   bash "$BUNDLE_ROOT/remote-qualification.sh" --verify "$EXPECTED_RELEASE_SHA" "$EXPECTED_RELEASE_TREE" "$EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST" "$EXPECTED_BUNDLE_MANIFEST_SHA256"
   ```

   The anchored script recomputes the release-manifest canonical digest from
   actual bytes, checks the exact regular-file transfer path set and each file
   hash/size, and invokes the existing no-Git staged release verifier before
   host preflight or installation. Host preflight checks stopped/default-off
   state and exact wheel bytes; compatibility comes from the wheel's intrinsic
   `WHEEL` `Tag:` metadata. Target Python 3.12 must have the staged verifier's
   import prerequisites available before this read-only verification; absence
   fails closed. Record that prerequisite separately from the target runtime
   and pilot venv closure.
4. Only after a separate current deployment authorization, repeat the exact
   pre-execution hash block and pass the same four independent release/bundle
   arguments to the script with `--install` and the explicit authorization
   setting described in the generated script. It refuses an existing `/opt/trader-assist-v0` install;
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
Record the canonical independent anchors, exact release and bundle hashes,
transfer path-set proof, service/permit state before and after,
host and venv proof, validate-only result, and rollback result. Never include
credential values, private data, tokens, keys, production DBs or raw logs.
After merge, Q1 separately observes the public Nautilus probe, bounded
NOT_SUBMITTED process, readiness and cohort behavior, recovery, outbox and
SQLite integrity. A local or CI PASS is not target-host or Q1 evidence.
