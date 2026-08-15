# FileCloud Ingestion and Embedding

> Source: original specification §17, §18. Content moved unchanged.

## FileCloud is authoritative

For document content, permissions, version, and ownership.

Use a dedicated **read-only FileCloud service identity**, restricted to the approved knowledge-base
tree, with credentials retrieved from Delinea PAM at runtime. This is authentication Flow 3 — never
a variant of the user-facing flow. See `02a-authentication-flows.md`.

## Change types the pipeline must handle

New documents · modified documents · deleted documents · **ACL-only changes** · document movement ·
department changes · security-tier changes · version changes · incremental sync · periodic
reconciliation.

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

**ACL-only changes must not trigger re-embedding.** Permissions change far more often than content;
coupling the two makes revocation slow exactly when it needs to be fast.

The system maintains explicit synchronization state and detects drift. Deletion and revocation are
production-readiness gates: deleted content must stop being retrievable, and a removed entitlement
must deny subsequent retrieval.

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
