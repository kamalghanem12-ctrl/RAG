# Authorization Test Matrix

> Source: original specification §23, extended during architecture review, and **rewritten for
> `../adr/0012-filecloud-acl-authoritative.md`** — Entra authenticates, FileCloud decides document
> access, PostgreSQL holds a synchronized projection enforced under RLS.
>
> This document is mirrored 1:1 by `tests/authz/`. **The tests are the gate — this file is the
> explanation.** If they disagree, fix the tests; do not soften the document.

Run it: `pytest tests/authz -v`

## What the matrix has to prove

```text
Unauthorized principal
        X
        |
        └──▶ RAG context
```

No unauthorized content reaches the reranker, the context builder, the prompt, or Claude — and the
failure of any single mechanism does not change that, because the API and RLS apply the predicate
independently.

## Identity

### Token validation → `test_token_validation.py`
`aud`, `iss`, `tid`, `exp`, signature. Critically: **a token validly minted for a different audience
must be rejected.** Without this the API accepts any token from the tenant, including one issued to
an unrelated application. Unchanged by ADR-0012 — Entra remains the identity authority.

### Principal mapping → `test_principal_mapping.py`
The `oid` is the canonical key. **Email is never an authorization key** — it is mutable,
reassignable after a departure, and one person can present several aliases; any of those turns a
mapping into a mis-grant. An identity with no active `principal_map` entry resolves to **zero
grants**, and an ACL naming an unmapped principal fails loudly rather than being silently skipped.
→ `../adr/0013-principal-mapping.md`

## The authorization decision

### Effective permissions → `test_effective_permissions.py`
Explicit FileCloud deny is resolved **during sync**: a denied user has no `document_grant` row rather
than a stored deny. Resolution must not depend on the order entries were extracted in. Default deny
when no entry exists.

### Group expansion → `test_group_expansion.py`
Group grants expand transitively into user-level rows; nested groups are flattened; cycles
terminate. **Partial expansion must not commit** — a failed sync is visible, a partial one is not.
An expanded grant must still record its origin, or nobody can answer "why does this person have
access" after flattening.

### Membership change → `test_membership_change.py`
A user joining a group gains documents with **no document and no ACL changing**. Membership is an
authorization input in its own right, with its own change detection — not something resolved once at
ingestion. Leaving revokes.

### Missing context → `test_missing_context.py`
An unset or empty `rag.principal_id` yields **zero rows, never all rows**, and a context must not
survive into the next request on a pooled connection. This is what RLS exists to catch: if the
predicate degenerates to TRUE against an empty principal, every user reads everything and no
happy-path test notices. → `../adr/0004-rls-and-pooling.md`

### Group membership truncation → `test_groups_overage.py`
**Retained and re-aimed.** ADR-0009 largely dissolves, but its failure mode moved from the request
path to the expansion step. A truncated or partial membership list silently narrows access exactly
as a truncated `groups` claim would have, and the request path must not read that claim at all.

## Change propagation

### ACL change → `test_acl_change.py`
An ACL-only change is now the most common authorization event in the system. It must propagate
without re-embedding, must deny via absence of a row, and must not disturb neighbouring documents.

### Revocation → `test_revocation.py`
Four independent paths, each able to fail on its own: grant removed · group left · mapping
deactivated · exception deny added. The fourth exists because the first three all wait for a
synchronization cycle, and emergency revocation must not.

### Deletion → `test_deletion.py`
Deletion reaches the chunks, the vectors, **and** the grant rows. An orphaned grant is not a leak by
itself, but a re-created document reusing the id would inherit it.

## Exceptions

### RAG exceptions → `test_rag_exceptions.py`
Precedence, first match wins: exception `deny` → exception `allow` → `document_grant` → default
deny. Covers the corpus-wide `scope = 'all'` grant implemented per ADR-0014, the `deny` kill switch
that outranks it, predicate-enforced expiry, non-leakage to other principals, and the requirement
that neither a client nor retrieved document content can name an exception into existence.

> **ADR-0014 carries accepted risk R1 with no approver recorded** — a wildcard exception granting
> read access to the entire indexed corpus, in all environments including production. Open finding;
> must be zero before production.

## Manipulation

### Parameter manipulation → `test_parameter_manipulation.py`
Bypass attempts via MCP parameters · API parameters · `document_id` · FileCloud path · principal
identity · exception fields · prompt injection. **All must fail.**

The elevation surface changed under ADR-0012. `principal_id`, `filecloud_principal_id`, grant
fields, and any `exception_*` field must never be read off a request. **`department`,
`sub_department`, and `security_tier` are now metadata** — legitimate as *narrowing* business
filters, and the assertion for them is that applying one can only reduce the authorized set, never
add to it.

### Track B isolation → `test_filecloud_mcp_isolation.py`
Separate capability, separate ADR. The FileCloud MCP acts as the signed-in user and never a service
account. Unaffected by ADR-0012. → `../adr/0011-filecloud-mcp-scope.md`

## Retired with the old model

`test_department_isolation.py` · `test_internal_inheritance.py` · `test_restricted_access.py` ·
`test_cross_subdepartment.py` · `test_multi_department.py` ·
`test_department_level_internal.py` · `test_entitlement_qualification.py` ·
`test_entitlement_invariants.py`

These tested the `(department, sub_department, security_tier)` predicate, which ADR-0012 retires as
an access control. They are recorded here rather than merely deleted, because two of them found real
defects and the *class* of defect outlives the model:

- **Entitlement qualification** caught bare-name matching — an entitlement for `Sales` granting
  access across a department boundary wherever a folder name was reused. The equivalent property
  under the new model is that grants are per-document, asserted in
  `test_parameter_manipulation.py` using a deliberate `Commercial/Sales` versus `Investments/Sales`
  path collision in the fixture corpus.
- **Entitlement invariants** caught a reachable state nobody would write a test for, because nobody
  writes a test for a case they assume cannot happen. The equivalent under the new model — a grant
  for a principal with no valid mapping — is asserted in `test_principal_mapping.py`.

## Status

All modules are scaffolded and marked `xfail` until Phase 2 lands the authorization core, with
`xfail_strict` set in `pyproject.toml`. **An `xpass` is a failure signal** — it means a test is
asserting something weaker than it should. That mechanism caught two tests during this rewrite:
both used `pytest.raises((SpecificError, Exception))`, which swallows `NotImplementedError` and
passes while asserting nothing.
