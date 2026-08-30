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
   |          contextualization plugs in here — optional, default off
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

## Chunk enrichment: contextualization

**Status: designed, not enabled. Default off.** The stage exists so that enabling it later is a
configuration change rather than a rebuild of the pipeline. Whether it is ever turned on is decided
by measurement, not by this document — see `../adr/0007-retrieval-eval.md`.

### What it is

A chunk split out of a document loses the context that made it meaningful. *"The threshold shall not
exceed 5% of net asset value"* is unfindable on its own — which policy, which year, which entity.
Contextualization asks an LLM to write a one- or two-sentence situating description of the chunk
within its source document, prepends it to the chunk text, and embeds the combined string.

The retrieved chunk shown to the user is the **original text**; the generated context participates
in embedding and keyword matching only.

### Where it sits

Inside **Chunk Enrichment**, between Chunking and BGE-M3. It is a pure function of
`(document, chunk)` and touches nothing downstream — no component after it needs to know whether a
chunk was contextualized. That property is what makes it pluggable, and it must be preserved.

### Design constraints

| Constraint | Requirement |
|---|---|
| Default | **Off.** A pipeline run with the stage disabled is the reference behaviour |
| Model | `claude-haiku-4-5` — high-volume, mechanical work; roughly a fifth the cost of an Opus-tier model for identical output |
| Determinism | `temperature=0`, and the prompt is versioned |
| Caching | The document is the cached prefix, chunks vary after it. All chunks of one document are processed together or the cache is wasted |
| Failure | A failed contextualization call degrades to the un-contextualized chunk. It **must not** fail the ingestion run |
| Isolation | Cost and latency belong to ingestion only. Nothing here runs in the request path |

### Versioning

Contextualization changes what is embedded, so it participates in the re-index story. Add to the
per-chunk tracking in the BGE-M3 section below:

```text
context_model            null when the stage is off
context_prompt_version
context_generated_at
```

A change to either field invalidates the embedding exactly as a `chunking_version` change does.
Re-running contextualization over the corpus costs the full ingestion bill again — it is a one-time
cost per configuration, not a one-time cost overall.

### Two things that must be settled before it is enabled

Neither blocks the design. Both block the switch.

**1. Egress.** The stage sends document content to the Claude API. No other part of ingestion leaves
Derayah's boundary, so this introduces a trust-boundary crossing that
`01-trust-boundaries.md` does not currently describe. It is a data-classification and compliance
decision for Derayah's information-governance owners, not an engineering one. It is *not* a rule 1
concern — rule 1 governs the retrieval context, and this is ingestion — but it is a real crossing
and must be approved as one.

**2. Retrieval poisoning.** Generated context is derived from untrusted document content and is then
stored and embedded. A document carrying injected text could steer its own generated context to
match queries it has nothing to do with — permanently, for every authorized reader. Rule 9 covers
untrusted content in the *retrieval* path; this extends the same exposure to ingestion, and belongs
in `../security/threat-model.md` before the stage is enabled.

Authorization is unaffected either way: a poisoned chunk can still only surface to principals
already authorized for it. This is a retrieval-integrity problem, not an authorization bypass.

### What it does not fix

Contextualization makes chunks *findable*. It does nothing for ANN recall under selective ACL
filters, which is a separate and harder problem — see `../adr/0005-ann-recall-under-acl.md`. A good
result here must not be read as progress there.

## BGE-M3

Track on every chunk:

```text
embedding_model
embedding_version
embedding_dimension
chunking_version
preprocessing_version
context_model            null when contextualization is off
context_prompt_version   null when contextualization is off
context_generated_at     null when contextualization is off
```

Support controlled re-indexing when any of these change. **Do not destroy existing embeddings
without a migration or rebuild strategy.**

Configuration of the embedding service is subject to rule R1 — see `../baselines/bge-m3-serving.md`.
