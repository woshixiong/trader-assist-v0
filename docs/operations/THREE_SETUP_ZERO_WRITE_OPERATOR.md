# Three Setup zero-write operator

TS8 is source and test work only. The example unit and configuration do not authorize installation, credential placement, TLS ingress, service start, or exchange action.

The runtime alone writes `/var/lib/trader-assist-v0/three-setup-shadow/evidence.sqlite`. The operator reads it with SQLite `mode=ro` and `query_only`, closing each short source snapshot before writing to `/var/lib/trader-assist-v0/three-setup-operator/operator.sqlite`. The second file holds only the evolved HumanApprovalLedger package, action, state, and audit evidence. Operator failure must not stop or lock the runtime writer.

The example config deliberately leaves `reference_scenario` null. With no explicit ZERO_WRITE scenario, exact-risk review is blocked. Setting `1pct` or `2pct` selects retained *reference* sizing only; it never grants live risk or submission authority. Missing current executable/health/threshold proof also results in NO_SUBMIT. Every package and disposition remains NOT_SUBMITTED.

Use a future separately authorized external credential file with independent random access-token and session-signing values. Browser authority requires HTTPS, exact Host and Origin, a signed strict session, and CSRF. The provided runner binds loopback and disables forwarded proxy headers. Any trusted ingress design and service start require later human authorization.

The direct-TLS runner refuses to start without both external certificate and key paths. The example deliberately leaves them null. Later trusted ingress is a separate protected configuration decision. The separate operator process starts one internal approval reconciler. It reads only pending preauthorizations, checks exact retained Activation evidence, and records a zero-write terminal result. Browser GET and SSE cannot drive it. A failed guard consumes the package; a new trigger requires a new package and Human approval.
