# Configuration Baseline — PostgreSQL

> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.
>
> Scope: the PostgreSQL server hosting the RAG corpus, the ACL projection, and the RLS policies
> that enforce the retrieval predicate. Read alongside `pgvector.md` (the extension) and
> `rhel.md` (the host).
>
> **This is the security core's datastore.** Rule 2 puts the retrieval predicate in SQL under RLS;
> the settings here are what make that enforcement real rather than nominal.

## Status

**PROVISIONAL — not yet installed.** This baseline precedes installation, which is the order rule
R1 requires.

**It closes the first open VERIFY marker in `../adr/0004-rls-and-pooling.md`** (RLS and FORCE
semantics for table owners) and **partially closes the second** (pooler behaviour) — see F5, which
is honest about what the vendor documentation does and does not say.

## Object

| Field | Value |
|---|---|
| Component | PostgreSQL Server |
| Version pinned | **16.15** — current minor of the 16 series at baseline date |
| Major-version EOL | **9 November 2028** |
| Where deployed | RHEL 9.8, **native installation** (not containerised) — see `rhel.md` |
| Install source | **NOT ESTABLISHED — open finding #1.** RHEL AppStream vs. the PGDG repository. Decides which minor versions are available and who ships security patches |
| Environments | Test server first; production server exists but is out of scope until the test baseline is verified |
| Owner | **UNNAMED — open finding #2** |
| Baseline date | 2026-08-21 |

## Sources consulted

Most authoritative last. Documentation recalled from memory is not a valid source.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | PostgreSQL 16 documentation — Row Security Policies | https://www.postgresql.org/docs/16/ddl-rowsecurity.html | 16 | 2026-08-21 |
| 2 | PostgreSQL versioning and support policy | https://www.postgresql.org/support/versioning/ | current | 2026-08-21 |
| 3 | pgbouncer feature documentation | https://www.pgbouncer.org/features.html | current | 2026-08-21 |
| 4 | Vendor security / hardening guide | **NOT RETRIEVED** — PostgreSQL publishes security documentation within the main manual rather than as a separate hardening guide | — | — |
| 5 | CIS Benchmark for PostgreSQL 16 | **NOT CONSULTED** — a CIS Benchmark for PostgreSQL is expected to exist and is the reference a regulated financial institution should apply. **Open finding #3** | — | — |
| 6 | Derayah internal standard | **NOT RETRIEVED** — none supplied | — | — |

> Derayah internal standards override all external guidance wherever they are stricter.

## Findings that drive the design

### Row-level security — closes ADR-0004 marker 1

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| **F1** | **Table owners bypass RLS by default.** Verbatim: *"Table owners normally bypass row security as well, though a table owner can choose to be subject to row security with `ALTER TABLE ... FORCE ROW LEVEL SECURITY`."* | 1 | **If the application role owns its tables, RLS is silently inert.** No error, no warning — every policy is simply not applied. The predicate exists, the tests may even pass against a non-owner role, and production runs wide open |
| **F2** | `FORCE ROW LEVEL SECURITY` makes the owner subject to policies, reversing F1 | 1 | Either the application role must not own the tables, **or** every table must carry `FORCE`. Belt and braces: do both |
| **F3** | **Superusers and `BYPASSRLS` roles always bypass RLS**, regardless of `FORCE`. Verbatim: *"Superusers and roles with the `BYPASSRLS` attribute always bypass the row security system when accessing a table."* | 1 | `FORCE` does **not** save you here. The application role must never be a superuser and must never hold `BYPASSRLS`. This is a hard invariant and belongs in the authorization test matrix, not only in this file |
| **F4** | Enabling/disabling RLS and adding policies is the table owner's privilege alone | 1 | Ownership separation is a security control, not a tidiness preference. The migration role owns and defines; the application role only reads under policy |

**The ownership model this implies** — to be reflected in `../architecture/03-data-model.md` and the
Alembic migrations:

```
migration/DDL role   owns the tables, defines policies, NOT used at request time
application role     NOT owner, NOT superuser, NOT BYPASSRLS, reads under RLS
                     tables additionally marked FORCE ROW LEVEL SECURITY
```

Three independent things must all hold. Any one of them alone is insufficient: a non-owner
application role still bypasses everything if it has `BYPASSRLS` (F3); `FORCE` alone does not stop
a superuser (F3); ownership separation alone is undone the day someone runs a migration as the
application role (F1).

### Connection pooling — partially closes ADR-0004 marker 2

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| **F5** | pgbouncer's feature table marks **`SET`/`RESET` as "Never"** supported in transaction pooling mode, along with `PREPARE`/`DEALLOCATE`, `LISTEN`, and session-level advisory locks. The documentation states transaction pooling *"breaks a few session-based features of PostgreSQL"*. **`SET LOCAL` does not appear in that table at all** | 3 | Confirms the prohibition in rule 5 — session-scoped `SET` genuinely does not survive transaction pooling, and would leak one user's authorization context onto a pooled connection. **But the vendor does not explicitly document `SET LOCAL` as safe.** The architectural reasoning is sound — `SET LOCAL` is transaction-scoped, and transaction pooling holds a server connection for the life of a transaction, so the setting cannot outlive its transaction or be reassigned mid-transaction — and it is *consistent with* the documentation rather than *stated by* it |

**ADR-0004's second marker is therefore not fully closed.** The inference above is recorded as an
inference. It must be confirmed empirically on the test server before code depends on it — the
check is in the Verification section, and it is cheap. Do not treat the reasoning as verification.

### Version currency

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| F6 | PostgreSQL 16's current minor is **16.15**; the series reaches EOL **9 November 2028** | 2 | Roughly two years of support remains at baseline date. Adequate for this project's delivery, but a major-version upgrade path should be a known item before production, not a surprise in 2028 |
| F7 | Upstream policy: *always run the current minor release*. Minor releases carry only bug fixes, security fixes, and data-corruption fixes; they need no dump/restore — stop, replace binaries, restart | 2 | Minor-version patching is low-risk and expected. The re-review trigger below treats a minor bump as routine rather than as a re-baseline |

## Settings applied

None yet — PostgreSQL is not installed. Intended settings, to be verified on the running system
before this section is treated as real:

| Setting | Intended value | Rationale | Source # |
|---|---|---|---|
| Table ownership | Application role is **not** the owner | F1, F4 | 1 |
| `FORCE ROW LEVEL SECURITY` | Enabled on every table carrying an ACL predicate | F2 | 1 |
| Application role attributes | `NOSUPERUSER`, `NOBYPASSRLS` | F3 | 1 |
| Pooling mode | Transaction mode, with `SET LOCAL` inside an explicit transaction | F5, rule 5 | 3 |
| `ssl` | `on` | Encryption in transit. Derayah standard expected to require it | — |
| `password_encryption` | `scram-sha-256` | Current standard; MD5 is obsolete | — |
| `pg_hba.conf` auth methods | No `trust`, anywhere | — | — |
| `log_connections` / `log_disconnections` | `on` | Audit trail for a regulated environment | — |

The last four rows are **stated without a retrieved source** and are marked as such: they reflect
ordinary practice, not consulted guidance. They must be confirmed against the CIS Benchmark
(open finding #3) and any Derayah standard before this baseline stops being provisional.

## Deviations from baseline

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| D1 | CIS Benchmark for PostgreSQL not consulted | Not retrieved at baseline time | Hardening settings below the benchmark may be missing; four intended settings currently rest on practice rather than a cited source | *(blank — not approved)* | — |
| D2 | ADR-0004's `SET LOCAL` premise rests on inference from pgbouncer's documentation, not an explicit vendor statement | The vendor's feature table omits `SET LOCAL` | If the inference is wrong, request-scoped authorization context is unsound — the highest-severity failure in the platform | *(blank — not approved)* | — |

**Open findings: 5** — must be zero before production.

1. Install source not established (AppStream vs. PGDG).
2. No named Derayah owner for this configuration.
3. CIS Benchmark not consulted (deviation D1).
4. Deviation D2 has no approver, and the empirical check has not been run.
5. Nothing installed; no setting verified on a running system.

## Re-review trigger

- [ ] Major version change (16 → 17 or later)
- [x] Minor version bump — routine per F7; update the pinned version, no re-baseline
- [ ] CIS Benchmark obtained or revised
- [ ] Derayah standard issued or revised
- [ ] Pooler introduced, replaced, or its mode changed
- [ ] **Approaching 9 November 2028** — major-version upgrade planning
- [ ] Fixed interval: annually

## Verification

Nothing installed, nothing verified. Checks to run on the **test server** once installed:

```
-- Version
SELECT version();                  -- expect 16.15

-- F1/F2 — is RLS actually forced, and who owns the tables?
SELECT relname, relrowsecurity, relforcerowsecurity, pg_get_userbyid(relowner) AS owner
FROM pg_class WHERE relkind = 'r' AND relnamespace = 'public'::regnamespace;
-- expect: relrowsecurity = t, relforcerowsecurity = t, owner <> the application role

-- F3 — the application role must hold neither attribute
SELECT rolname, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = '<app role>';
-- expect: f | f

-- Transport and auth
SHOW ssl;                          -- expect on
SHOW password_encryption;          -- expect scram-sha-256
-- and: no `trust` lines in pg_hba.conf

-- F5 / D2 — the empirical check that closes ADR-0004 marker 2.
-- Through the pooler in transaction mode, in one transaction:
--   BEGIN; SET LOCAL app.principal_id = 'A'; SELECT current_setting('app.principal_id'); COMMIT;
-- then on a NEW pooled connection, without setting it:
--   BEGIN; SELECT current_setting('app.principal_id', true); COMMIT;
-- expect: NULL on the second. A non-null value means context leaked across
-- requests and rule 5's premise is broken. Run this under concurrency, not once.
```

The final check is the important one. It is the difference between believing the pooling model is
safe and knowing it. Automate it into `tests/authz/` rather than running it by hand.
