# Data Model and Row-Level Security

> Source: original specification §14, §15. Content moved unchanged; the RLS section gains the
> explicit pooling rule from `../adr/0004-rls-and-pooling.md`.

## Tables

PostgreSQL + pgvector is the fixed initial vector/data platform. At minimum:

```text
documents
chunks
document_acl
authorization_metadata
ingestion_jobs
sync_state
embedding_versions
audit metadata
```

## Chunk metadata

Every indexed document and chunk supports at minimum:

```text
document_id            filecloud_document_id      document_version
chunk_id               filecloud_path             last_modified
department             filecloud_acl_reference    ingestion_timestamp
sub_department         classification             embedding_model
security_tier          owner                      embedding_version
```

`security_tier` is exactly one of `Internal`, `Restricted`.

`sub_department` is **nullable** — department-level Internal content has no sub-department. See
`02-authorization-model.md` for why that NULL must be handled deliberately.

Folder paths are metadata and organizational structure, **not the sole authorization control**.

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
context must fail closed, not fall through to an unfiltered query.

## Never

Never retrieve unauthorized rows and remove them later in application memory. The window between
fetch and filter is the vulnerability, and it is a blocked pattern — not a style preference.
