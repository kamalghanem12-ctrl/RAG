# ADR-0014 — RAG Authorization Exceptions

**Status:** Proposed — **needs Derayah security approval.** Carries one accepted risk with **no
approver recorded** (open finding)
**Depends on:** `0012-filecloud-acl-authoritative.md`

## Context

Section 12 of the change request requires RAG-specific authorization exceptions that do not modify
the FileCloud source ACL, including one that grants a named user access to **any** document for
testing purposes.

The requirement is legitimate. FileCloud ACLs are managed by document owners across the business;
the RAG platform needs a governed way to grant an auditor, an incident responder, or a test account
access without editing permissions in the system of record and without that edit propagating to
FileCloud's own users.

## Decision

A separate, governed, auditable exception store, evaluated inside the retrieval predicate.

```text
rag_exception
    exception_id
    principal_id       Entra oid; see 0013-principal-mapping.md
    scope              'document' | 'all'
    document_id        NULL when scope = 'all'
    effect             'allow' | 'deny'
    reason             free text, required
    approver           named Derayah approver, required
    created_by
    created_at
    expires_at         required; no open-ended exception
```

### Precedence

As specified in `0012-filecloud-acl-authoritative.md`. First match wins:

| # | Condition | Effect |
|---|---|---|
| 1 | exception `deny`, unexpired | **DENY** |
| 2 | exception `allow`, unexpired | **ALLOW** — overrides FileCloud denial |
| 3 | FileCloud effective allow | ALLOW |
| 4 | otherwise | **DENY** |

`deny` above `allow` is the one non-negotiable ordering. It is what guarantees a revocation path that
works even against a wildcard grant, and it is the property that makes the risk below recoverable
rather than permanent.

### `scope = 'all'` — implemented as requested

A row with `scope = 'all'` and `effect = 'allow'` grants its principal read access to every indexed
document, overriding FileCloud denial.

This was requested explicitly, and it is implemented as requested. The risk is recorded below rather
than mitigated away.

## The accepted risk

**A single row in `rag_exception` defeats document-level authorization for its principal.**

The platform's stated purpose is that authorization is enforced outside the LLM and unauthorized
content can never enter the retrieval context. A wildcard allow makes that statement conditional on
the contents of one table. Specifically:

- Every guarantee in `../architecture/02-authorization-model.md` becomes "…unless a wildcard
  exception exists for this principal."
- The blast radius is the entire indexed corpus, across every department and every classification.
  With no data-classification scheme in place (`0008-regulatory-scope.md`), there is no label that
  could exclude a subset from it.
- It is reachable by anyone who can write to that table — which makes write access to
  `rag_exception` equivalent to read access to the whole corpus, and that equivalence must be
  reflected in database privileges and in change control.
- For a regulated financial institution this is the kind of standing access an auditor or regulator
  would ask to see justified, with dates and names.

| # | Risk accepted | Justification | Approver (name, role) | Date |
|---|---|---|---|---|
| R1 | Wildcard exception grants a principal read access to the entire indexed corpus, overriding FileCloud denial, in all environments including production | Requested by the project owner for testing purposes | *(blank — not approved)* | — |

**Open findings: 1.** Must be zero before production.

The recommendation on record remains what it was when the option was put: per-document, time-boxed
exceptions, with a seeded test corpus covering the testing need. That recommendation was not
adopted. This ADR does not relitigate it — it records what was decided and what it costs.

## What the design does provide

None of these reduce the requested capability. They make its use visible and reversible.

**It is a grant inside the predicate, not a bypass of it.** This matters more than it sounds. The
wildcard is evaluated by the same SQL under the same RLS policy as every other grant. It is not a
superuser connection, not a `BYPASSRLS` role, and not application-layer filtering — so it is
auditable, revocable, and covered by the same tests. A service-account bypass would have none of
those properties.

**`approver` and `expires_at` are `NOT NULL`.** An exception cannot be created without a named person
and an end date. This constrains the record, not the capability.

**Exception-decided retrievals are audit-logged with the `exception_id`.** When a wildcard grant is
what permitted a chunk to reach the context builder, the audit record says so. Without this the
corpus-wide read is indistinguishable from ordinary authorized use, which is the difference between
an answerable and an unanswerable audit question.

**Creation, modification, and use raise alerts.** A wildcard exception coming into existence is a
security event, not a configuration change.

**Expiry is enforced in the predicate, not by a cleanup job.** `expires_at > now()` is evaluated at
query time, so a lapsed exception stops granting access the moment it lapses, whether or not any
reaper has run.

**`effect = 'deny'` is the kill switch.** It outranks every allow including the wildcard, so
revocation never depends on deleting a row in time.

## Tests

- exception allow grants access to a document FileCloud denies
- exception deny overrides exception allow, including `scope = 'all'`
- expired exception grants nothing — asserted against the predicate, not a cleanup job
- wildcard scope reaches every document in the fixture corpus
- exception revocation takes effect on the next request
- an exception cannot be created without `approver` and `expires_at`
- exception use appears in the audit record with its `exception_id`
- a client cannot supply, name, or influence an exception through the API or an MCP tool argument
- retrieved document content cannot cause an exception to be created or matched

→ `tests/authz/test_rag_exceptions.py`

## Open

- Who at Derayah may approve a wildcard exception, and who may write to `rag_exception`? Those are
  the same privilege in effect and should be named as one.
- Maximum permitted `expires_at` horizon for `scope = 'all'`.
- Whether production should permit `scope = 'all'` at all, or whether the schema should differ by
  environment. Recorded as open because the decision taken was "as requested, including
  production"; revisiting it is a security owner's call, not an engineering one.
