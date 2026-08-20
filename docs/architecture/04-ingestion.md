# FileCloud Ingestion and Embedding

> Source: original specification §17, §18. Content moved unchanged.

## FileCloud is authoritative

For document content, permissions, version, and ownership.

Use a dedicated **read-only FileCloud service identity**, restricted to the approved knowledge-base
tree, with credentials retrieved from Delinea PAM at runtime. This is authentication Flow 3 — never
a variant of the user-facing flow. See `02a-authentication-flows.md`.

## Change types the pipeline must handle

New documents · modified documents · deleted documents · **ACL-only changes** · **inherited
permission changes** · **user-level permission changes** · **group-level permission changes** ·
**group membership changes** · **folder permission changes** · document movement · department
changes · security-tier changes · version changes · incremental sync · periodic reconciliation.

> **Revised** by `../adr/0012-filecloud-acl-authoritative.md`. ACL extraction was a secondary
> concern under the path-derived model — `filecloud_acl_reference` was stored and never evaluated.
> It is now the primary authorization path, and the permission-related change types above are
> promoted from footnotes to first-class.

## Two pipelines, two cadences

Content and permissions change at different rates and must propagate independently.

```text
Content pipeline   FileCloud → change detection → extract → chunk → embed → chunks
Authorization      FileCloud → ACL + membership extraction → normalize → expand → document_grant
```

**ACL-only changes must not trigger re-embedding.** Permissions change far more often than content;
coupling them makes revocation slow exactly when it needs to be fast. This rule predates the change
and is now load-bearing rather than merely efficient.

### The authorization sync path

```text
FileCloud ACL entries + group membership
   ↓
document_acl_raw          (as extracted, for audit and drift)
   ↓  resolve effective permissions — explicit deny removes the grant
   ↓  expand groups transitively into member users
document_grant            (effective, user-level, what the predicate reads)
```

Three properties are non-negotiable:

- **Complete or fail, per document.** A partially expanded group commits an authorization state
  narrower or wider than FileCloud's, with nothing in the data to show it. No partial commit.
- **An unmapped principal grants nothing and raises an alert.** Silently skipping a principal with
  no `principal_map` entry is how a whole group's access disappears unnoticed — and how a
  locally-created FileCloud account gets ignored instead of investigated.
- **A failed or stale sync is a security state.** It must alarm, not merely retry. Staleness is the
  window in which a revoked user still reads.

Emergency revocation must not wait for the next scheduled sync. `rag_exception` with
`effect = 'deny'` outranks every allow and is the intended path — see `../adr/0014-rag-exceptions.md`.

## Pipeline

```text
FileCloud
   |
   v
Change Detection
   |
   v
Content + Metadata + ACL Extraction
   |
   v
Chunking
   |
   v
Chunk Enrichment
   |
   v
BGE-M3
   |
   v
PostgreSQL + pgvector
```

The system maintains explicit synchronization state and detects drift. Deletion and revocation are
production-readiness gates: deleted content must stop being retrievable, and a removed grant must
deny subsequent retrieval.

The pipeline above is the **content** path. The authorization path runs separately and at its own
cadence — see "Two pipelines, two cadences" above.

## BGE-M3

Track on every chunk:

```text
embedding_model
embedding_version
embedding_dimension
chunking_version
preprocessing_version
```

Support controlled re-indexing when any of these change. **Do not destroy existing embeddings
without a migration or rebuild strategy.**

Configuration of the embedding service is subject to rule R1 — see `../baselines/bge-m3-serving.md`.
