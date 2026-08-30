# Configuration Baseline — pgvector

> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.
>
> Scope: the `vector` PostgreSQL extension providing embedding storage and approximate nearest
> neighbour search. Read alongside `postgresql.md` — pgvector is an extension inside that server,
> not a separate service.

## Status

**PROVISIONAL — not yet installed.** This baseline precedes installation, which is the order rule
R1 requires. Settings become real when the extension is created on the test server.

**This baseline closes both open VERIFY markers in `../adr/0005-ann-recall-under-acl.md`.** The
findings below change that ADR's premise and are the reason this document is worth reading before
any index is created.

## Object

| Field | Value |
|---|---|
| Component | pgvector (`vector` PostgreSQL extension) |
| Version pinned | **0.8.6** — current release at baseline date |
| PostgreSQL compatibility | 13 and above; targeted at PostgreSQL 16.15 (see `postgresql.md`) |
| Where deployed | RHEL 9.8 test server, native PostgreSQL installation |
| Owner | **UNNAMED — open finding #1** |
| Baseline date | 2026-08-21 |

## Sources consulted

Most authoritative last. Documentation recalled from memory is not a valid source.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | pgvector official documentation (README) | https://github.com/pgvector/pgvector | 0.8.6 | 2026-08-21 |
| 2 | Vendor security / hardening guide | **NOT APPLICABLE** — pgvector publishes none; it inherits the PostgreSQL security model | — | — |
| 3 | CIS Benchmark | **NOT CONSULTED** — no CIS Benchmark is published for pgvector; the PostgreSQL benchmark governs the server. See `postgresql.md` open findings | — | — |
| 4 | Derayah internal standard | **NOT RETRIEVED** — none supplied | — | — |

> Derayah internal standards override all external guidance wherever they are stricter.

## Findings that drive the design

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| **P1** | **Filtering is applied *after* the index is scanned.** Documented verbatim: *"With approximate indexes, filtering is applied after the index is scanned. If a condition matches 10% of rows, with HNSW and the default `hnsw.ef_search` of 40, only 4 rows will match on average."* | 1 | **This is the ACL-recall problem, stated by the vendor.** A permission-aware RAG filters far harder than 10% — a user authorised for 2% of the corpus would get roughly *one* row back from a default HNSW scan asking for ten. Not an error, not a timeout: silently short results. This is the single most important finding in this baseline |
| **P2** | **Iterative index scans exist and solve P1.** Added in **0.8.0**. Controlled by `hnsw.iterative_scan` and `ivfflat.iterative_scan`, each set to `strict_order` or `relaxed_order`. The scan continues pulling index tuples until enough rows survive the filter | 1 | The mitigation is a configuration setting, not application code. It must be set — the default is off |
| P3 | Bounding parameters: `hnsw.max_scan_tuples` (default 20,000), `hnsw.scan_mem_multiplier` (default 1, a multiple of `work_mem`), `ivfflat.max_probes` | 1 | Iterative scan without a bound is an unbounded scan. These caps are what keep a heavily-filtered query from degrading into a sequential scan |
| P4 | `hnsw.ef_search` default is **40** | 1 | The number that makes P1 as sharp as it is. Raising it is a partial mitigation and not a substitute for P2 |
| P5 | HNSW gives a better speed–recall tradeoff, needs no training, but builds slower and uses more memory. IVFFlat builds faster, uses less memory, and **requires training** (k-means over existing data) | 1 | IVFFlat's training requirement is awkward for an incrementally-ingested corpus — the index must be rebuilt as the corpus grows to stay well-conditioned |
| P6 | Vendor recommendation under selective filters: **HNSW with `iterative_scan` enabled** | 1 | Aligns with P5. Recorded as the intended starting configuration, subject to the measurement in `../adr/0007-retrieval-eval.md` |
| P7 | Build tuning: HNSW `m` (default 16) and `ef_construction` (default 64); IVFFlat `lists` (`rows/1000` up to 1M rows, `sqrt(rows)` beyond). `maintenance_work_mem` and `max_parallel_maintenance_workers` accelerate builds | 1 | Index build cost is a re-indexing consideration — see the versioning fields in `../architecture/04-ingestion.md` |

### Why P1 matters more here than in a normal RAG

In an unfiltered RAG, approximate search returning slightly fewer or slightly worse rows is a
quality issue. Under this platform's authorization model it is a **correctness** issue with a
dangerous failure signature: the user is authorized for the content, the predicate is correct, RLS
is working — and the answer is still wrong or empty, because the ANN scan never surfaced the rows
the filter would have kept.

That failure is invisible from the outside. It looks like "the assistant doesn't know", not like a
bug. It cannot be caught by the authorization matrix in `../security/authorization-tests.md`, which
tests that unauthorized content is *excluded*; this is authorized content being wrongly *omitted*.
It needs its own eval, and that is a direct input to `../adr/0007-retrieval-eval.md`.

Note also that this is **not** fixed by contextualization or any chunk-enrichment technique — see
`../architecture/04-ingestion.md`.

## Settings applied

None yet — the extension is not installed. Intended settings, each to be verified on the running
system before this section is treated as real:

| Setting | Intended value | Rationale | Source # |
|---|---|---|---|
| `hnsw.iterative_scan` | `strict_order` (starting point) | Mitigates P1. `strict_order` preserves exact distance ordering; `relaxed_order` trades ordering for speed and must be justified by measurement before adoption | 1 |
| `hnsw.ef_search` | To be tuned — **not** left at 40 | P4 | 1 |
| `hnsw.max_scan_tuples` | To be tuned from the default 20,000 | P3 — bounds worst-case scan cost under a narrow ACL filter | 1 |
| `hnsw.scan_mem_multiplier` | To be tuned against `work_mem` | P3 | 1 |
| Index type | HNSW | P5, P6 | 1 |
| `m` / `ef_construction` | Defaults (16 / 64) pending measurement | P7 | 1 |

Every value above is a **starting point pending the retrieval eval**, not a decision. Recording
them here is what makes the eventual tuning auditable.

## Deviations from baseline

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| D1 | No CIS Benchmark or vendor hardening guide consulted | Neither is published for pgvector; the PostgreSQL server benchmark governs | Extension-specific hardening guidance, if any exists elsewhere, was not applied | *(blank — not approved)* | — |

**Open findings: 3** — must be zero before production.

1. No named Derayah owner for this configuration.
2. Deviation D1 has no approver.
3. All settings are intended, not applied — nothing has been verified on a running system.

## Re-review trigger

- [ ] Component version bump (pgvector 0.8.6 → any other)
- [ ] PostgreSQL major version change (see `postgresql.md`)
- [ ] Benchmark or hardening guide published for pgvector
- [ ] Derayah standard revision
- [ ] **Retrieval eval produces measured values** — the intended settings above are replaced by
      measured ones, and this baseline is no longer provisional
- [ ] Corpus grows by an order of magnitude — P7 index parameters are size-dependent
- [ ] Fixed interval: annually

## Verification

Nothing installed, nothing verified. Checks to run on the test server once installed:

```
-- Extension present and at the pinned version
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';
-- expect: vector | 0.8.6

-- Iterative scan settings actually in effect
SHOW hnsw.iterative_scan;
SHOW hnsw.ef_search;
SHOW hnsw.max_scan_tuples;
SHOW hnsw.scan_mem_multiplier;

-- P1 regression check — the one that matters.
-- Build a table where a filter matches a small fraction of rows, then confirm
-- a top-10 ANN query under that filter actually returns 10 rows.
-- Run it with iterative_scan off and on; the difference is the finding.
EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM chunks
WHERE <acl predicate>
ORDER BY embedding <=> :query_vector
LIMIT 10;
```

The last check belongs in the automated eval, not only here. A configuration that silently
under-returns is exactly the kind of thing that passes a one-off manual check and then regresses.
