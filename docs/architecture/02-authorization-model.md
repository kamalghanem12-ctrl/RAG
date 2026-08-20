# Authorization Model

> **Revised** by `../adr/0012-filecloud-acl-authoritative.md`, which supersedes ADR-0002 and retires
> the department/sub-department/security-tier model as an access control. See "Change record" at the
> end for what was replaced and why.
> Depends on `../adr/0013-principal-mapping.md` and `../adr/0014-rag-exceptions.md`.

## The rule, in prose

> A user may retrieve a chunk if and only if FileCloud's effective permissions on that chunk's
> parent document grant read access to that user, **or** a governed, unexpired RAG exception grants
> it — and no unexpired RAG exception denies it.

This sentence is canonical. If the SQL below and this paragraph ever disagree, the paragraph is right
and the SQL is a bug.

## Two questions, two authorities

The architecture keeps these strictly separate, and conflating them is the failure this model exists
to prevent.

| Question | Answered by |
|---|---|
| **Who is this?** | Microsoft Entra ID — authentication, identity, MFA |
| **What may this identity read?** | FileCloud — effective document permissions |

Entra establishes identity. It no longer carries document entitlements. FileCloud decides access.
PostgreSQL holds a synchronized projection of that decision so retrieval is fast, and enforces it
under RLS so an application bug cannot leak past it.

| Domain | Source of truth |
|---|---|
| User identity, authentication | Microsoft Entra ID |
| Document content | FileCloud |
| **Document permissions** | **FileCloud** |
| Search index | PostgreSQL + pgvector |
| Authorization projection | PostgreSQL — **a cache, never an authority** |
| RAG exceptions | Separate governed store |

**The projection is never an independent authorization authority.** It is a synchronized
representation of FileCloud state. When the two disagree, FileCloud is right and the projection is
stale — which is a defect to detect and alarm on, not a decision to honor.

## FileCloud is not in the query path

A normal semantic query does not call FileCloud:

```text
Claude Desktop → MCP Shim → MCP Server → API → ACL projection → pgvector → authorized chunks
```

Synchronization is a separate, periodic path:

```text
FileCloud → ACL Sync Service → normalize + expand → PostgreSQL projection
```

This keeps FileCloud latency off every query, keeps FileCloud availability from becoming a hard
runtime dependency, and keeps API load proportional to *change* volume rather than *query* volume.

The cost is stated plainly in the staleness section below, because it is the price of this design and
not an implementation detail.

## The document is the authorization object

```text
FileCloud Document  ──effective ACL──▶  Chunk 1
                                       Chunk 2
                                       Chunk 3
```

All chunks inherit their parent document's effective authorization. **There is no per-chunk
permission system.** Chunks carry enough denormalized security metadata to enforce the parent's
authorization without a join back to `documents` on the hot path.

## The retrieval predicate

Expressed once, in `src/derayah_rag/authz/`, as SQL, enforced under RLS. Never reimplemented in
Python. Never expressed in a prompt.

Group membership is pre-expanded during synchronization (ADR-0013), so every row in
`document_grant` names a **user**. Request-time evaluation needs only the caller's stable Entra
`oid` — no groups claim, no Graph call, no live FileCloud lookup.

```sql
-- rag.principal_id is set with SET LOCAL inside the request transaction.
-- See ../adr/0004-rls-and-pooling.md for why never session-scoped SET.

NOT EXISTS (
    SELECT 1 FROM rag_exception e
    WHERE  e.principal_id = current_setting('rag.principal_id')
      AND  e.effect       = 'deny'
      AND  e.expires_at   > now()
      AND  (e.scope = 'all' OR e.document_id = chunk.document_id)
)
AND (
    EXISTS (
        SELECT 1 FROM rag_exception e
        WHERE  e.principal_id = current_setting('rag.principal_id')
          AND  e.effect       = 'allow'
          AND  e.expires_at   > now()
          AND  (e.scope = 'all' OR e.document_id = chunk.document_id)
    )
    OR EXISTS (
        SELECT 1 FROM document_grant g
        WHERE  g.document_id  = chunk.document_id
          AND  g.principal_id = current_setting('rag.principal_id')
    )
)
```

### Precedence

First match wins:

| # | Condition | Effect |
|---|---|---|
| 1 | RAG exception `deny`, unexpired | **DENY** |
| 2 | RAG exception `allow`, unexpired | **ALLOW** — overrides FileCloud denial |
| 3 | `document_grant` row present | ALLOW |
| 4 | otherwise | **DENY** — default deny |

`deny` outranks `allow` so that a revocation path always exists, including against a wildcard grant.

### Properties that carry the model

Each has a dedicated test.

**Deny needs no row.** FileCloud explicit-deny entries are resolved during synchronization when
effective permissions are computed — a denied user simply has no `document_grant` row. Raw ACL
entries are retained for audit and drift detection but are not on the decision path. A projection
that stored grants *and* denies on the hot path would be two sources of truth for one question.
→ `tests/authz/test_effective_permissions.py`

**Grants are user-level after expansion.** A group grant on a folder inherited by many documents
expands to one row per (document, member). The schema is designed for that fan-out because it is the
normal case. → `tests/authz/test_group_expansion.py`

**Group membership is itself an authorization input.** A user added to a group gains documents
without any document or ACL changing. Membership is a first-class synchronized object with its own
change detection. → `tests/authz/test_membership_change.py`

**An unmapped principal grants nothing.** An Entra identity with no confirmed FileCloud principal
mapping resolves to zero grants, never a best-effort email match. → `tests/authz/test_principal_mapping.py`

**Absence of authorization context yields nothing, never everything.** A request that cannot
establish `rag.principal_id` must fail closed. → `tests/authz/test_missing_context.py`

## Worked example — denied

```text
User            Kamal, valid Entra identity
FileCloud       HR/Policy.pdf — no read grant for Kamal
RAG exception   none
```

Kamal asks *"Show me the HR policy."*

```text
Kamal → Claude Desktop → MCP Shim → MCP Server → API
   API validates the Entra token                      ✓ authenticated
   API resolves the FileCloud principal               ✓ mapped
   API queries the projection for HR/Policy.pdf       ✗ no grant
   ↓
   No results returned
```

The pipeline stops before pgvector, the reranker, the context builder, and Claude.

**The response is "no results", not "access denied".** An error naming the document would disclose
that it exists. Deny is indistinguishable from not-found — see `../adr/0006-deny-vs-notfound.md`.

If a coding or policy error let an unauthorized query reach the database anyway, RLS returns zero
rows. That is the point of having two boundaries.

## Worked example — authorized

```text
User            Sara, valid Entra identity
FileCloud       HR/Policy.pdf — READ granted, via HR group membership on the parent folder
```

```text
Sara → … → API
   Token validated, principal mapped
   Projection: grant row present for (HR/Policy.pdf, Sara)
       — written by sync, expanded from the HR group grant inherited from the folder
   ↓
   pgvector query under RLS + ACL predicate
   ↓
   Authorized chunks → Reranker → Context Builder → Claude
```

Sara's grant exists because sync expanded a *group* grant on a *folder* into a *user* grant on a
*document*. All three of those translations are places the projection can be wrong, which is why
expansion must be complete-or-fail rather than best-effort.

## Authorization context

Constructed per request from trusted identity sources only:

```text
principal_id            Entra oid — the canonical key
filecloud_principal_id  resolved via principal_map
```

That is the whole context. It is deliberately much smaller than its predecessor: under this model
the API resolves *who you are* and the database resolves *what that entitles you to*. There are no
department sets or entitlement pairs to assemble, and therefore none to assemble wrongly.

**The client may never define or override the principal.** A request may carry a search query and
legitimate business filters — including `department` or `classification`, which are now metadata. It
may never carry `principal_id`, `filecloud_principal_id`, or any exception field. Supplied
authorization parameters are rejected, never honored. See `07-api.md`.

## Permission freshness

Authorization is now a **cache of a decision made in another system**, and the cache can be wrong in
the direction that matters: a user whose FileCloud access was revoked keeps reading until the next
sync completes.

```text
FileCloud ACL change → detection → sync → projection updated → new requests respect it
                       └────────── staleness window ──────────┘
```

The architecture must define, and has not yet: maximum acceptable staleness, sync interval, retry
policy, reconciliation frequency, failure handling, and an **emergency revocation path** that does
not wait for the next scheduled sync.

Two rules already hold and matter more under this model:

- **ACL-only changes must not trigger re-embedding** (`04-ingestion.md`). Permissions change far
  more often than content; coupling them makes revocation slow exactly when it must be fast.
- **A failed sync is a security state, not an operational one.** Stale authorization must alarm, and
  a partially applied sync must not commit — a partial expansion silently narrows or widens access
  with nothing to indicate it.

For high-sensitivity documents, a live FileCloud check at request time should be evaluated as an
option for that subset, accepting the dependency it reintroduces.

## Enforcement point

The predicate is enforced **before** unauthorized chunks reach:

- the reranker
- the context builder
- the prompt
- Claude

Never retrieve unauthorized rows and filter them afterwards in application memory. That is a blocked
pattern, not a style preference — the window between fetch and filter is the vulnerability.

Defense in depth, unchanged by this revision:

```text
API Authorization  →  primary policy decision
PostgreSQL RLS     →  database enforcement, final data boundary
```

The API is the Policy Enforcement Point. RLS is what survives an application bug. Both apply the
same predicate independently. See `03-data-model.md` and `../adr/0004-rls-and-pooling.md`.

## Open decisions

| ADR | Question |
|---|---|
| `0012-filecloud-acl-authoritative.md` | The change itself — needs security and information-governance ratification |
| `0013-principal-mapping.md` | Entra-to-FileCloud principal mapping; where group membership is authoritative |
| `0014-rag-exceptions.md` | Exception model — carries one accepted risk with no approver recorded |
| `0005-ann-recall-under-acl.md` | **Escalated.** Per-user ACL filters are far more selective than department filters; filtered-ANN recall becomes a first-order design risk |
| `0006-deny-vs-notfound.md` | Deny indistinguishable from not-found |

## Change record

### What this revision replaced

The previous model derived authorization from the FileCloud **folder path** at ingestion, into a
`(department, sub_department, security_tier)` triple, with this predicate:

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

It was retired because it could only express organizational shape. It could not express a grant to
one named person, an inherited folder permission, a group grant, or a documented exception — all
ordinary requirements in a document estate. `filecloud_acl_reference` was already stored on every
chunk and never evaluated, which is the gap ADR-0002 was raised to resolve and ADR-0012 resolves.

`department`, `sub_department`, and `security_tier` remain on the chunk as **metadata** — useful for
filtering, ranking, and reporting, and permissible as client-supplied *business* filters. They are no
longer authorization inputs.

### Defects fixed in the previous model, retained here as a record

The original specification's §16 predicate had three defects, all corrected before retirement:

1. **The Internal clause had no `security_tier` guard** — read literally it allowed every document in
   the user's department, including Restricted ones, collapsing the Restricted model entirely.
2. **`user.department` was a scalar** while the multi-department requirement needed a set.
3. **`restricted_entitlements` held bare sub-department names**, permitting cross-department grants
   wherever a sub-department name was reused — `Commercial/Sales` versus `Investments/Sales`.

Recorded because the class of error matters more than the specific model: in all three cases the
prose rule was unambiguous and only the SQL was wrong. That is why the prose remains canonical at
the top of this file.
