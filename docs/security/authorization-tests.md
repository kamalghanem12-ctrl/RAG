# Authorization Test Matrix

> Source: original specification §23, extended with five cases found during architecture review.
>
> This document is mirrored 1:1 by `tests/authz/`. **The tests are the gate — this file is the
> explanation.** If they disagree, fix the tests; do not soften the document.

Run it: `pytest tests/authz -v`

## The original nine

### Department isolation → `test_department_isolation.py`
```text
Commercial user -> Commercial/Internal = ALLOW
Commercial user -> HR/Internal         = DENY
```

### Internal inheritance → `test_internal_inheritance.py`
```text
Commercial user -> Commercial/Sales/Internal     = ALLOW
Commercial user -> Commercial/Marketing/Internal = ALLOW
```
Sub-department membership is not required for Internal content.

### Restricted access → `test_restricted_access.py`
```text
Commercial user without Sales entitlement -> Commercial/Sales/Restricted = DENY
Commercial user with    Sales entitlement -> Commercial/Sales/Restricted = ALLOW
```

### Cross-subdepartment isolation → `test_cross_subdepartment.py`
```text
Sales Restricted user -> Sales/Restricted     = ALLOW
Sales Restricted user -> Marketing/Restricted = DENY
```

### Multi-department user → `test_multi_department.py`
Legitimate multi-department access must not create unintended Restricted access in any of them.

### Revocation → `test_revocation.py`
Remove an entitlement; subsequent retrieval is denied.

### ACL change → `test_acl_change.py`
Change a document Internal → Restricted; authorization changes accordingly.

### Deletion → `test_deletion.py`
Delete the source document; it is no longer retrievable.

### Manipulation → `test_parameter_manipulation.py`
Attempt bypass via MCP parameters · API parameters · `document_id` · FileCloud path · `department` ·
`sub_department` · `security_tier` · natural-language prompt manipulation. **All must fail.**

## Five added during review

Each closes a gap the original matrix could not have caught.

### Token validation → `test_token_validation.py`
`aud`, `iss`, `tid`, `exp`, signature. Critically: **a token validly minted for a different
audience must be rejected.** Without this the API accepts any token from the tenant, including one
issued to an unrelated application.

### Groups overage → `test_groups_overage.py`
A claim carrying the `_claim_names` overage indicator must resolve full membership via Graph, or
fail closed loudly. It must never silently under-grant — that failure looks like a permissions bug
and gets "fixed" by widening something.
→ `../architecture/02a-authentication-flows.md`

### Entitlement qualification → `test_entitlement_qualification.py`
Two departments each own a sub-department named `Sales`. An entitlement for `(Commercial, Sales)`
must **not** grant `Investments/Sales/Restricted`. Catches the bare-name matching bug.

### Department-level Internal → `test_department_level_internal.py`
`Commercial/Internal` (`sub_department IS NULL`) is reachable by any Commercial user, and the NULL
never leaks into the Restricted branch of the predicate.

### Entitlement invariants → `test_entitlement_invariants.py`
The unpaired state: Restricted entitlement for `(Commercial, Sales)` held *without* Commercial
department authorization. Behavior per `../adr/0010-entitlement-invariants.md` — either the context
builder rejects it, or Restricted implies parent access. Currently undecided, so this test is the
one that will change when the ADR is ratified.

## Status

All fourteen are scaffolded and marked `xfail` until Phase 2 lands the authorization core. An
`xpass` is a failure signal — it means a test is asserting something weaker than it should.
