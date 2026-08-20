# Retrieval

> Source: original specification §13, §19. Content moved unchanged; the recall-starvation
> consequence is stated explicitly per `../adr/0005-ann-recall-under-acl.md`.

## RAG service responsibilities

Query understanding · query routing · retrieval · metadata filtering · ACL-aware retrieval · hybrid
search where justified · reranking · context construction · source and citation handling ·
retrieval quality controls.

The RAG service **consumes a validated authorization context and never invents permissions.** It
receives the context; it does not derive, extend, or infer it.

## Runtime flow

```text
User Query
   |
   v
Identity Validation
   |
   v
Authorization Context
   |
   v
Query Router
   |
   v
ACL-aware Retrieval
   |
   v
PostgreSQL + pgvector
   |
   v
Authorized Candidate Chunks
   |
   v
Reranker
   |
   v
Context Builder
   |
   v
Claude
```

Everything downstream of "Authorized Candidate Chunks" operates only on rows the user may read.
The reranker never sees a denied chunk; neither does the context builder, the prompt, or Claude.

## Techniques to evaluate

Vector search · metadata filtering · ACL filtering · hybrid search · query routing · search fan-out ·
reranking · **pgvector iterative scans where selective ACL filters could cause recall starvation.**

## Recall starvation under selective ACL filters

> **Escalated** by `../adr/0012-filecloud-acl-authoritative.md`. This was a Phase 7 evaluation
> question under the department model. Under per-user ACL filters it is a **first-order design risk
> that must be settled during Phase 6 index design.**
>
> The difference is arithmetic. A department filter partitioned the corpus into roughly as many
> buckets as there are departments — each one a large fraction of the whole. A per-user ACL filter
> can match a few dozen documents out of hundreds of thousands. That is the regime where filtered
> ANN stops working, not the regime where it needs tuning.

With an HNSW index and a highly selective ACL predicate, an ANN search can return **fewer rows than
`LIMIT`, or none at all** — the index walk exhausts its candidate list before finding enough rows
the user may read.

The danger is presentational: this surfaces to the user as "no results", which is indistinguishable
from a genuine empty result. A user with narrow entitlements experiences the system as broken, and
the natural "fix" under pressure is to widen the filter.

Required: iterative-scan configuration plus a **minimum-recall guard that logs** when a query
returns fewer authorized candidates than requested, so starvation is observable rather than
inferred. → `../adr/0005-ann-recall-under-acl.md`

### Directions to evaluate in Phase 6, not decided here

- A materialized `allowed_principals` array on the chunk with a GIN index, so the filter is an index
  operation rather than a join
- Partitioning by principal set, where the estate has a small number of recurring access shapes
- Pre-filtering to a candidate document set, then vector search within it
- Higher `ef_search` with a measured recall floor per selectivity band

Each trades write amplification, index size, or latency differently, and the right answer depends on
the real shape of Derayah's ACLs — how many distinct principal sets exist across the corpus. That
shape is currently unknown and is the first thing to measure once the projection holds real data.

## Never trade security for retrieval performance

If the only way to hit a latency target is to widen the filter, the latency target is wrong.

## Retrieval quality

Quality needs a baseline, an eval set, and a regression gate — currently absent, and far cheaper to
build before Phase 7 than after. → `../adr/0007-retrieval-eval.md`
