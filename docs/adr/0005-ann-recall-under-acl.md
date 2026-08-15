# ADR-0005 — ANN Recall Under Selective ACL Filters

**Status:** Proposed
**Blocks:** Phase 7

## Context

The original §19 named "pgvector iterative scans where selective ACL filters could cause recall
starvation" — an unusually sharp catch. But it stated the technique without stating the
consequence, and the consequence is what needs a decision.

With an HNSW index and a highly selective ACL predicate, an approximate search walks a fixed
candidate list and filters it. If few candidates survive the filter, the query returns **fewer rows
than `LIMIT`, or none** — not because nothing relevant exists, but because the index walk gave up
before finding it.

The danger is presentational. To the user it is "no results", indistinguishable from a genuine
empty result. The users who hit it hardest are exactly those with the narrowest entitlements. And
the intuitive fix, under delivery pressure, is to widen the filter.

## Decision

**1. Enable iterative index scans**, so the search continues walking until it accumulates enough
rows that satisfy the filter or exhausts the index.

**2. Add a minimum-recall guard.** When a query returns fewer authorized candidates than requested,
log it as a distinct, structured event — not a debug line. Fields: user's entitlement breadth,
requested `LIMIT`, rows returned, whether the index was exhausted.

**3. Distinguish the two empty cases in the response contract.** "No authorized results" and "no
results" are different states internally, even though — per ADR-0006 — they must look identical to
the user. The distinction lives in telemetry, not in the API response.

**4. Never widen the filter to improve recall.** If a latency or recall target can only be met by
loosening the ACL predicate, the target is wrong.

## Consequences

- Iterative scans trade latency for recall. Query latency becomes entitlement-dependent, so
  percentile latency must be tracked per entitlement breadth, not just globally.
- The minimum-recall guard is a security signal as much as a quality one: a sudden rise correlates
  with an ACL sync problem.
- Index parameter tuning (`m`, `ef_construction`, `ef_search`) is security-relevant and belongs in
  `../baselines/pgvector.md` under rule R1.

## Alternatives considered

**Pre-filter to a materialized authorized set, then search.** Exact recall, but the authorized set
can be large and rebuilding it per query is expensive. Worth revisiting if iterative scans prove
too slow at production cardinality.

**Over-fetch and post-filter.** Rejected outright — it retrieves unauthorized rows into application
memory, which is a blocked pattern regardless of how quickly they are discarded.

## VERIFY before ratification

```
VERIFY: pgvector iterative scan support, configuration parameters, and version availability
        — against official pgvector documentation for the pinned version
VERIFY: HNSW vs. IVFFlat behavior under selective filters — against pgvector documentation
```
