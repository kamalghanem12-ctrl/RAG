# Data Model and Row-Level Security

> Source: original specification §14, §15. The RLS section carries the explicit pooling rule from
> `../adr/0004-rls-and-pooling.md`.
> **Revised** by `../adr/0012-filecloud-acl-authoritative.md`: the authorization tables are now a
> synchronized projection of FileCloud ACL state rather than path-derived metadata.

## Tables

PostgreSQL + pgvector is the fixed initial vector/data platform. At minimum:

```text
documents                chunks                  embedding_versions
document_acl_raw         document_grant          principal_map
group_membership         rag_exception           sync_state
ingestion_jobs           audit metadata
```

### The authorization tables

**`document_acl_raw`** — FileCloud ACL entries as extracted, before interpretation. Off the decision
path entirely; it exists for audit, drift detection, and answering "why does this grant exist".

```text
document_id  principal_id  principal_type  permission  effect        -- allow | deny
inheritance_source         source_version  sync_timestamp
```

**`document_grant`** — the effective, expanded, user-level allow set. **This is what the predicate
reads.**

```text
document_id  principal_id            -- always a USER after expansion
origin_principal                     -- the group or user the grant came from
grant_source                         -- direct | group | inherited
inheritance_source                   -- the folder or document that conferred it
source_version  sync_timestamp
```

Explicit FileCloud denies are resolved *here*, during synchronization: a denied user has no row.
Storing denies on the decision path would create two sources of truth for one question.
`origin_principal` and `inheritance_source` are what make a grant explainable after expansion has
flattened it.

**`group_membership`** — expanded transitively, cycles terminated. Membership is an authorization
input in its own right: a user joining a group gains documents with no document or ACL changing.

**`principal_map`** — Entra `oid` ↔ FileCloud principal. See `../adr/0013-principal-mapping.md`. An
identity with no active mapping resolves to zero grants.

**`rag_exception`** — governed exceptions, evaluated inside the predicate. See
`../adr/0014-rag-exceptions.md`. `approver` and `expires_at` are `NOT NULL`.

> **Write access to `rag_exception` is equivalent to read access to the entire corpus**, because a
> single `scope = 'all'` row grants it. Database privileges and change control must reflect that
> equivalence rather than treating it as an ordinary configuration table.

### Expected fan-out

One group grant on a folder inherited by 10,000 documents, expanded across 200 members, is
2,000,000 `document_grant` rows. That is the **normal** case, not the pathological one. Index
strategy, sync batching, and the retrieval predicate must all be designed for that shape from the
start — see `05-retrieval.md` on filtered-ANN selectivity.

## Chunk metadata

Every indexed document and chunk supports at minimum:

```text
document_id            filecloud_document_id      document_version
chunk_id               filecloud_path             last_modified
department             classification             ingestion_timestamp
sub_department         owner                      embedding_model
security_tier          acl_version                embedding_version
```

**`department`, `sub_department`, and `security_tier` are metadata, not authorization.** They remain
useful for business filtering, ranking, and reporting, and a client may supply them as *narrowing*
filters. They are no longer read by the predicate. `security_tier` remains one of `Internal`,
`Restricted`; `sub_department` remains nullable, but nothing about the authorization decision now
depends on that NULL.

`acl_version` replaces the old `filecloud_acl_reference`. The old column was stored on every chunk
and never evaluated — precisely the gap ADR-0002 was raised about. The new column is a projection
generation marker, used to detect chunks whose authorization state predates the current sync.

Folder paths are metadata and organizational structure, **never the authorization control**.

## Row-Level Security

RLS is a database-level defense-in-depth control. It is not the only control — retrieval-time
filtering applies the same predicate independently — but it is the one that survives an application
bug.

```text
Validated User Identity
        |
        v
Authorization Context
        |
        v
Request-Scoped DB Context
        |
        v
RLS + Retrieval Predicates
        |
        v
Authorized Rows Only
```

### The pooling rule

Two failure modes, both silent when wrong. Both are blocked patterns.

**Use `SET LOCAL` inside an explicit transaction.** Never session-scoped `SET`, never
`set_config(..., false)`. On a pooled connection, session-scoped context survives the request that
set it and leaks into whichever request next borrows that connection — one user's authorization
context silently applied to another user's query.

**The application role must not be able to bypass RLS.** It must not be superuser, must not hold
`BYPASSRLS`, and **must not own the tables** — table owners bypass RLS unless the table is declared
`FORCE ROW LEVEL SECURITY`. Ownership and application access are separate roles.

### Still to design

RLS policies · secure database roles · request/session context propagation · connection pooling
behavior · transaction boundaries · privilege separation · bypass prevention · failure behavior.

Failure behavior in particular must be explicit: a request that cannot establish an authorization
context must fail closed, not fall through to an unfiltered query. Under the ACL model the context is
a single value — `rag.principal_id` — which makes the failure mode simpler to reason about and
simpler to get wrong: an unset setting must yield zero rows, never all rows.

### Sync-time writes versus request-time reads

The projection tables are written by the ACL synchronization service and read by retrieval. These are
**different database roles**. The sync role writes `document_grant` and `group_membership`; the
application role reads them and can write neither. Otherwise an application-layer bug becomes a
privilege-escalation path — the request that reads the grants could also mint one.

Sync must be **transactional and complete-or-fail per document**. A partially expanded group commits
an authorization state that is silently narrower or wider than FileCloud's, with nothing in the data
to indicate it.

## Never

Never retrieve unauthorized rows and remove them later in application memory. The window between
fetch and filter is the vulnerability, and it is a blocked pattern — not a style preference.
