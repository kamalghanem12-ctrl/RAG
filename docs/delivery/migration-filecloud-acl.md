# Migration — FileCloud ACL as the Authoritative Authorization Source

> Requested change: see `../adr/0012-filecloud-acl-authoritative.md`.
> This document satisfies steps 1–10 of the change request's section 16. Steps 1–8 (current state)
> are complete below. The migration plan and rollback strategy are gated on two open decisions,
> named at the end.

## 1–8. Current state

### The single most important fact

**There is no authorization implementation to migrate.** The platform is at Phase 0. `src/` does not
exist. Every authorization artifact in this repository is a document or a test written against an
interface that has never been built.

`tests/authz/` holds 15 modules, all `xfail` against `NotImplementedError` with `xfail_strict`. The
placeholder predicate lives in `tests/authz/conftest.py:29` and raises rather than deciding.

The change therefore costs **documents and tests**, not a rewrite, a data migration, or a
re-embedding pass. This is the cheapest moment it will ever be, and the difference is not marginal:
the same change after Phase 7 would mean re-deriving authorization metadata across the entire
indexed corpus.

### Existing Entra department/group-based authorization (step 2)

| Location | What it asserts |
|---|---|
| `docs/architecture/02-authorization-model.md` | The canonical prose rule and the SQL predicate over `(department, sub_department, security_tier)` |
| `docs/architecture/02a-authentication-flows.md` | Three authentication flows; token validation claims |
| `docs/adr/0009-entitlement-claims.md` | How `restricted_entitlements` is carried from Entra — app roles vs. security groups |
| `docs/adr/0010-entitlement-invariants.md` | Whether a Restricted entitlement may exist without its parent department |
| `CLAUDE.md` rules 2, 3 | Predicate lives in one place; client-supplied authorization values are refused |

### All authorization predicates (step 3)

Exactly one, stated in `02-authorization-model.md:42` and duplicated as a docstring in
`tests/authz/conftest.py:34`:

```sql
document.department IN user.departments
AND (
      document.security_tier = 'Internal'
   OR (
          document.security_tier = 'Restricted'
      AND (document.department, document.sub_department)
          IN user.restricted_entitlements
      )
)
```

Nothing else in the repository expresses an authorization decision. That single-expression property
is what makes this change tractable.

### Existing PostgreSQL RLS policies (step 4)

**None exist.** `docs/architecture/03-data-model.md` specifies the constraints RLS must satisfy but
defines no policy:

- `SET LOCAL` inside an explicit transaction, never session-scoped `SET` (`../adr/0004-rls-and-pooling.md`)
- The application role must not be superuser, must not hold `BYPASSRLS`, and **must not own the
  tables** — an owner bypasses RLS unless the table is `FORCE ROW LEVEL SECURITY`
- A request that cannot establish an authorization context fails closed

All three constraints survive this change unchanged. They are about *how* RLS is wired, not *what*
it decides.

### MCP authorization logic (step 5)

None. By design — `docs/architecture/06-mcp.md` states the MCP server "never bypasses the API
authorization layer." It exposes `search_knowledge`, `retrieve_document_context`,
`get_source_reference` and delegates every decision. Unaffected by this change.

Track B (`09-filecloud-mcp.md`) is separate and also unaffected: it inherits FileCloud's
authorization live, per user, and holds no projection.

### API authorization logic (step 6)

None implemented. `docs/architecture/07-api.md` specifies that the API is the Policy Enforcement
Point and enumerates the request fields that must never be honored: `department`, `sub_department`,
`security_tier`, `allowed_groups`, `allowed_users`, `roles`, `permissions`. Enforced by
`.claude/hookify.client-supplied-authz.local.md`. **That field list changes under this migration** —
see the open items.

### Current FileCloud ingestion and ACL handling (step 7)

Specified, not built. `docs/architecture/04-ingestion.md`:

- Dedicated **read-only** FileCloud service identity, scoped to the approved knowledge-base tree,
  credentials from Delinea PAM at runtime (authentication Flow 3)
- Change types already include **ACL-only changes**, document movement, and periodic reconciliation
- **"ACL-only changes must not trigger re-embedding"** — already correct, and load-bearing under this
  change rather than merely efficient
- `document_acl` already appears in the table list in `03-data-model.md`, and
  `filecloud_acl_reference` is already stored on every chunk — **but never evaluated in the
  decision.** That gap is precisely what ADR-0002 was raised to resolve

### Test modules and their fate (step 8)

| Module | Fate |
|---|---|
| `test_token_validation.py` | **Survives unchanged** — Entra remains the identity authority |
| `test_parameter_manipulation.py` | **Survives, field list changes** |
| `test_revocation.py`, `test_acl_change.py`, `test_deletion.py` | **Survive, become central** — projection staleness is now the primary risk |
| `test_restricted_access.py`, `test_internal_inheritance.py` | **Rewritten** — reframed onto ACL grants |
| `test_department_isolation.py`, `test_cross_subdepartment.py`, `test_multi_department.py`, `test_department_level_internal.py`, `test_entitlement_qualification.py`, `test_entitlement_invariants.py` | **Retired** — they test a model being replaced |
| `test_groups_overage.py` | **Retained, re-aimed** — see the open items; the failure mode may relocate rather than disappear |
| `test_filecloud_mcp_isolation.py` | Unaffected (Track B) |

### Hookify rules affected

| Rule | Change |
|---|---|
| `hardcoded-departments` | Re-scope — departments stop being an authorization concept |
| `naive-groups-claim` | **Keep and re-aim.** Still the right shape, possibly still the right target |
| `client-supplied-authz` | Field list changes |
| `post-retrieval-filtering`, `session-scoped-db-context`, `unvalidated-token-claims` | Unchanged |

### ADR impact

| ADR | Effect |
|---|---|
| 0002 — ACL vs. path-derived tier | **Resolved as Option B.** Superseded by ADR-0012 |
| 0009 — entitlement claims | Largely **dissolved** — Entra no longer carries document entitlements |
| 0010 — entitlement invariants | **Moot** — no department/sub-department entitlements remain |
| 0005 — ANN recall under selective ACL filters | **Escalates sharply.** Was a Phase 7 question; becomes a first-order design risk |
| 0006 — deny vs. not-found | Unchanged and now more relevant |
| 0004 — RLS and pooling | Unchanged |

## The two gating decisions, now taken

1. **Group membership is pre-expanded during synchronization** — not read from the Entra `groups`
   claim, and not resolved by a live FileCloud call. The request path needs one value: the caller's
   `oid`. Recorded in `../adr/0013-principal-mapping.md`, which also states plainly that the
   overage failure mode **relocated to the expansion step** rather than disappearing.
2. **The wildcard exception is implemented as requested**, including in production. Recorded in
   `../adr/0014-rag-exceptions.md` as accepted risk **R1 with no approver** — an open finding. The
   recommendation on record was per-document, time-boxed exceptions with a seeded test corpus; it
   was not adopted, and the ADR records what was decided and what it costs rather than relitigating.

## 9. Migration plan

Phase 0 work — documents, decisions, and tests — is complete. The steps below are implementation
work and are gated on ratification.

| # | Step | Depends on |
|---|---|---|
| 1 | Ratify ADR-0012 (security + information governance), ADR-0013 (identity), ADR-0014 (security) | Derayah owners |
| 2 | Resolve the `VERIFY` markers: FileCloud ACL model, explicit-deny semantics, inheritance rules, whether effective permissions are exposed by the API or must be computed; whether ACL change events exist or reconciliation must poll | Deployed FileCloud version |
| 3 | Re-do `../baselines/filecloud.md` against the pinned version — currently provisional with 3 open findings | Step 2 |
| 4 | Answer ADR-0013's open questions: principal types in the deployed instance, authoritative source of group membership, handling of FileCloud-local accounts | Identity owners |
| 5 | Define the freshness SLA: maximum staleness, sync interval, retry policy, reconciliation frequency, failure handling, emergency revocation path | Steps 1–2 |
| 6 | Phase 2 — `principal_map`, projection schema, expansion, exception store, RLS policies, and `pytest tests/authz` from `xfail` to green | Steps 1–5 |
| 7 | Phase 3 — ACL synchronization service on its own cadence, decoupled from the content pipeline | Step 6 |
| 8 | **Phase 6 — settle ADR-0005 during index design**, not during Phase 7 evaluation. Measure the real distribution of distinct principal sets across the corpus first | Step 7 |

Step 8 is the one most likely to be deferred and least safe to defer. Per-user ACL filters are far
more selective than department filters, and the filtered-ANN behaviour has to be measured against
Derayah's actual ACL shape before the index design is fixed.

## 10. Rollback

**Now:** `git revert`. No `src/` exists, no RLS policy exists, no projection holds data, and no
index needs rebuilding. The full cost of reversing this change today is a revert commit.

**After Phase 2 lands:** rollback additionally requires dropping `document_grant`,
`document_acl_raw`, `group_membership`, `principal_map`, and `rag_exception`, and reverting the RLS
policies. No re-embedding is needed in either direction — the change never touches chunk content or
vectors, only authorization metadata. This is the property that keeps the change cheap, and it is a
direct consequence of the existing rule that ACL-only changes must not trigger re-embedding.

**After Phase 7:** rollback would mean re-deriving `(department, sub_department, security_tier)`
authorization for the entire indexed corpus and rebuilding whatever index strategy step 8 chose.
Reversal stops being practical here, which is the argument for taking the decision now rather than
later.

**Reverting is not the same as being safe.** If a wildcard exception has been used in production
before a rollback, the corpus-wide reads it permitted already happened. Audit records survive the
revert; the disclosure does not un-happen. That is what makes the `exception_id` in the audit trail
load-bearing rather than nice to have.
