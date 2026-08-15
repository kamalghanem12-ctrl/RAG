# Authorization Model

> Source: original specification §6, §7, §16.
> **§16's predicate has been corrected** — see "Correction record" at the end for what changed and why.

## The rule, in prose

> Every Sub-department may contain both Internal and Restricted content. All Internal content is
> accessible to everyone authorized for the parent Department, while Restricted content is
> accessible only to users explicitly authorized for that specific Sub-department.

This sentence is canonical. If the SQL below and this paragraph ever disagree, the paragraph is
right and the SQL is a bug.

## Knowledge hierarchy

```text
Department
|
+-- Internal                     <- sub_department IS NULL
|
+-- Sub-department A
|     +-- Internal
|     +-- Restricted
|
+-- Sub-department B
|     +-- Internal
|     +-- Restricted
```

Folder paths are **metadata and organizational structure**, not the authorization control. The
control is the `(department, sub_department, security_tier)` triple stored on every chunk, enforced
by the predicate below under Row-Level Security.

`security_tier` is exactly one of: `Internal`, `Restricted`.

## The retrieval predicate

Expressed once, in `src/derayah_rag/authz/`, as SQL, enforced under RLS. Never reimplemented in
Python. Never expressed in a prompt.

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

Three properties of this predicate carry the whole model, and each has a dedicated test:

**Entitlements are fully-qualified `(department, sub_department)` pairs.** Never bare
sub-department names. If two departments each own a sub-department named `Sales` — or `Operations`,
or `Analytics` — a bare-name match would grant Restricted access *across a department boundary*.
→ `tests/authz/test_entitlement_qualification.py`

**Department-level Internal has no sub-department.** `Commercial/Internal` is stored with
`sub_department IS NULL`. The Internal branch must never reference `sub_department`. Note that
`NULL IN (...)` evaluates to NULL rather than false, which excludes the row under RLS — fail-closed
and therefore safe, but it must be deliberate rather than incidental.
→ `tests/authz/test_department_level_internal.py`

**`departments` is a set, not a scalar.** A user may legitimately hold more than one department.
Multi-department access must not create unintended Restricted access in any of them.
→ `tests/authz/test_multi_department.py`

## Worked example

```text
Commercial/
├── Internal/
├── Sales/
│   ├── Internal/
│   └── Restricted/
├── Sales_Analytics/
│   ├── Internal/
│   └── Restricted/
└── Marketing/
    ├── Internal/
    └── Restricted/
```

A user holding:

```text
departments             = [Commercial]
restricted_entitlements = [(Commercial, Sales)]
```

resolves to:

| Path | Decision |
|---|---|
| `Commercial/Internal` | ALLOW |
| `Commercial/Sales/Internal` | ALLOW |
| `Commercial/Sales/Restricted` | ALLOW |
| `Commercial/Sales_Analytics/Internal` | ALLOW |
| `Commercial/Sales_Analytics/Restricted` | DENY |
| `Commercial/Marketing/Internal` | ALLOW |
| `Commercial/Marketing/Restricted` | DENY |
| `HR/Internal` | DENY |
| `Investments/Sales/Restricted` | DENY — the entitlement is `(Commercial, Sales)`, not `Sales` |

## Authorization context

Constructed per request from trusted identity sources only:

```text
user_id
departments             set
groups                  set, validated
roles                   set, validated
restricted_entitlements set of (department, sub_department) pairs
```

Derived from:

```text
Entra ID identity
      +
validated groups / roles
      +
approved enterprise authorization mapping
```

**The client may never define or override any of these.** A request may carry a search query and
legitimate business filters; it may never carry `department`, `sub_department`, `security_tier`,
`allowed_groups`, `allowed_users`, `role`, or `permission`. Supplied authorization parameters are
ignored or rejected — never honored. See `07-api.md`.

How `restricted_entitlements` is carried in the token is an open decision — Entra app roles are
recommended over security groups. See `../adr/0009-entitlement-claims.md`.

## Reconciliation

```text
user authorization  +  document authorization  =  effective retrieval authorization
```

FileCloud remains authoritative for document ACLs; Entra ID remains authoritative for user identity
and group membership; the RAG index is a **derived, synchronized representation** and never an
independent source of truth. Which of the two authorization sources wins when they disagree is an
open decision — see `../adr/0002-acl-source-of-truth.md`.

## Enforcement point

The predicate is enforced **before** unauthorized chunks reach:

- the reranker
- the context builder
- the prompt
- Claude

Never retrieve unauthorized rows and filter them afterwards in application memory. That is a
blocked pattern, not a style preference — the window between fetch and filter is the vulnerability.

Defense in depth: the predicate is applied as a retrieval-time filter **and** independently by
PostgreSQL RLS. See `03-data-model.md` and `../adr/0004-rls-and-pooling.md`.

## Open decisions

| ADR | Question |
|---|---|
| `0002-acl-source-of-truth.md` | FileCloud ACL vs. path-derived tier — which is authoritative on conflict? |
| `0009-entitlement-claims.md` | Entra app roles vs. security groups for `restricted_entitlements` |
| `0010-entitlement-invariants.md` | May a user hold Restricted for `(Commercial, Sales)` without Commercial department authorization? |

## Correction record

The original §16 read:

```text
ALLOW Internal     IF document.department == user.department

ALLOW Restricted   IF document.department == user.department
                   AND document.security_tier == Restricted
                   AND document.sub_department IN user.restricted_entitlements
```

Three defects, all fixed above:

1. **The Internal clause had no `security_tier` guard.** Read literally it allowed *every* document
   in the user's department including Restricted ones, making the second clause redundant and
   collapsing the Restricted model entirely.
2. **`user.department` was a scalar** while §7 and the multi-department test case both require a
   set.
3. **`restricted_entitlements` held bare sub-department names**, permitting cross-department grants
   wherever a sub-department name is reused.

The prose rule at the top of this file was never ambiguous. Only the SQL was.
