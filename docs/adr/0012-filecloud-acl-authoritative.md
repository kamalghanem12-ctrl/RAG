# ADR-0012 — FileCloud ACL Is the Authoritative Source of Document Authorization

**Status:** Proposed — decision requested by the project owner; **needs Derayah security and
information-governance ratification**
**Supersedes:** `0002-acl-source-of-truth.md` (resolves it as Option B)
**Blocks:** Phase 2, 3, 6, 7
**Depends on:** `0013-principal-mapping.md`, `0014-rag-exceptions.md`

## Context

ADR-0002 asked which of two disagreeing sources is authoritative for document permissions: the
FileCloud ACL, or the `(department, sub_department, security_tier)` triple derived from the folder
path at ingestion. It recommended Option A — path-derived tier authoritative, ACL able only to
revoke — and stated that the choice is a security-policy question belonging to Derayah's security
and information-governance owners.

**This ADR selects Option B.** FileCloud ACLs become authoritative. The path-derived tier model is
retired as an access-control mechanism.

The driver is capability, not correctness of the old model: the department/sub-department model can
only express organizational shape. It cannot express a grant to one named person, an inherited
folder permission, a group grant, or a documented exception. Those are ordinary requirements in a
document estate, and the old model could satisfy none of them.

### What this ADR does not change

- **Entra ID remains authoritative for user identity and authentication.** Nothing about the three
  authentication flows changes.
- **Authorization is still enforced outside the LLM**, before the reranker, the context builder, the
  prompt, and Claude.
- **The predicate still lives in exactly one place**, expressed as SQL, enforced under RLS.
- **Never retrieve-then-filter.**
- **RLS pooling constraints are untouched** — `SET LOCAL` in an explicit transaction, application
  role not owner, not superuser, no `BYPASSRLS`.

What changes is *what the predicate reads*, not where it lives or when it runs.

## Decision

| Domain | Source of truth |
|---|---|
| User identity, authentication | Microsoft Entra ID |
| Document content | FileCloud |
| **Document permissions** | **FileCloud** |
| Search index | PostgreSQL + pgvector |
| Authorization projection | PostgreSQL — **a synchronized cache, never an authority** |
| RAG exceptions | Separate governed store (`0014-rag-exceptions.md`) |

FileCloud is **not** in the normal query path. A synchronization service periodically projects
FileCloud ACL state into PostgreSQL; retrieval reads the projection. This keeps FileCloud latency,
availability, and API load off every semantic query.

### The new predicate

Group membership is pre-expanded during synchronization (`0013-principal-mapping.md`), so every row
in the projection names a **user**. Request-time evaluation therefore needs only the caller's stable
identifier — no group claim, no live FileCloud call:

```sql
-- Effective authorization for one chunk, evaluated under RLS.
-- rag.principal_id is set with SET LOCAL inside the request transaction.
EXISTS (
    SELECT 1 FROM rag_exception e
    WHERE  e.principal_id = current_setting('rag.principal_id')
      AND  e.effect = 'deny'
      AND  e.expires_at > now()
      AND  (e.scope = 'all' OR e.document_id = chunk.document_id)
) IS NOT TRUE
AND (
    EXISTS (
        SELECT 1 FROM rag_exception e
        WHERE  e.principal_id = current_setting('rag.principal_id')
          AND  e.effect = 'allow'
          AND  e.expires_at > now()
          AND  (e.scope = 'all' OR e.document_id = chunk.document_id)
    )
    OR EXISTS (
        SELECT 1 FROM document_grant g
        WHERE  g.document_id = chunk.document_id
          AND  g.principal_id = current_setting('rag.principal_id')
    )
)
```

### Precedence

Section 12 of the change request asked for explicit precedence. In order, first match wins:

| # | Condition | Effect |
|---|---|---|
| 1 | RAG exception `deny` | **DENY** |
| 2 | RAG exception `allow` | **ALLOW** — overrides FileCloud denial, as requested |
| 3 | FileCloud effective allow (`document_grant` row present) | ALLOW |
| 4 | Anything else | **DENY** — default deny |

Exception `deny` sits above exception `allow` deliberately: a revocation path must always win,
including over a wildcard grant. That is the only property that makes the wildcard in ADR-0014
survivable at all.

**FileCloud DENY needs no row.** Explicit deny entries are resolved during synchronization when
effective permissions are computed; a denied user simply has no `document_grant` row. Raw ACL
entries are still stored for audit and drift detection, but they are not on the decision path.

### The document is the authorization object

All chunks inherit their parent document's effective authorization. There is no per-chunk permission
system. Chunks carry enough denormalized metadata to enforce the parent's authorization without a
join back to `documents`.

## Consequences

### The projection's staleness is now a security control

Under the old model, authorization was a property of the folder path, captured at ingestion.
Under this one, authorization is a **cache of a decision made elsewhere**, and the cache can be
wrong in the direction that matters: a user whose FileCloud access was revoked keeps reading until
the next sync.

This makes `04-ingestion.md`'s existing rule — *ACL-only changes must not trigger re-embedding* —
load-bearing rather than merely efficient. Permission changes must propagate on their own path, at
their own cadence, decoupled from content.

Required and not yet defined: maximum acceptable staleness, sync interval, retry policy,
reconciliation frequency, failure handling, and an **emergency revocation path** that does not wait
for the next scheduled sync. For high-sensitivity documents, a live FileCloud check at request time
should be evaluated as an option — accepting that it reintroduces a FileCloud dependency for that
subset only.

### ADR-0005 escalates from a Phase 7 question to a first-order design risk

This is the largest technical risk in the change.

Department filters partition the corpus into roughly as many buckets as there are departments. A
per-user ACL filter can match a handful of documents out of hundreds of thousands. HNSW under a
filter that selective either loses recall badly or degrades to something close to a sequential
scan — the classic filtered-ANN failure.

`0005-ann-recall-under-acl.md` must be resolved during Phase 6 index design rather than discovered
during Phase 7 evaluation. Candidate directions, to be evaluated there and not decided here:
a materialized `allowed_principals` array on the chunk with a GIN index; partitioning by principal
set; pre-filtering into a candidate set before the vector search; or accepting a higher `ef_search`
with measured recall floors.

### ADRs that dissolve

- **0009 (entitlement claims)** — Entra no longer carries document entitlements, so app-roles-vs-
  groups stops being an authorization question. The groups-overage failure mode does **not** simply
  vanish, however; it relocates to group expansion during sync. See `0013-principal-mapping.md`.
- **0010 (entitlement invariants)** — moot. There are no department/sub-department entitlement pairs
  left to be unpaired.

### Denial semantics unchanged, and now more load-bearing

Section 10 of the change request described an unauthorized request as "rejected." It must not be.
A rejection discloses that the document exists. Deny must remain indistinguishable from not-found
per `0006-deny-vs-notfound.md` — the API returns no results, not an error naming a document.

### What `department`, `sub_department`, and `security_tier` become

Metadata. They stay on the chunk for filtering, ranking, and reporting, and they may still be
supplied by a client as a *business* filter. They are no longer authorization inputs, so the
prohibition on client-supplied values narrows to the fields that now carry authorization —
principal identity and exception state. See `../architecture/07-api.md`.

## VERIFY before ratification

```
VERIFY: FileCloud ACL model at the deployed version — principal types, explicit deny semantics,
        inheritance rules, and whether effective permissions are exposed by the API or must be
        computed from raw entries
        — against FileCloud official documentation and the deployed instance
VERIFY: whether FileCloud exposes ACL change events, or whether reconciliation must poll
        — against FileCloud official documentation
```

The second marker is inherited from ADR-0002 and is now more consequential: it determines whether
the staleness window is bounded by an event latency or by a polling interval.

`../baselines/filecloud.md` remains provisional with three open findings, the first being that the
deployed version is unknown. An unresolved marker blocks ratification.

## Status note

This ADR records a decision **requested by the project owner**. ADR-0002 stated that the choice of
system of record for document permissions belongs to Derayah's security and information-governance
owners. That ratification has **not** been given, and nothing here should be read as recording it.
