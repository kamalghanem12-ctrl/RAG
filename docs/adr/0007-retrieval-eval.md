# ADR-0007 — Retrieval Quality Baseline and Regression Gate

**Status:** Proposed
**Blocks:** Phase 7

## Context

"Retrieval quality" appears exactly once in the original specification, inside a list of things the
RAG service is responsible for. There is no eval set, no metric, no baseline, and no regression
gate.

For a RAG platform this matters as much as the authorization tests. Authorization decides whether
the system is *safe*; retrieval quality decides whether it is *useful*. A permission-aware RAG that
returns nothing relevant is a correctly-secured failure — and it fails in a way that invites
exactly the wrong fix, because the fastest way to improve recall is always to loosen a filter.

Building this before Phase 7 is far cheaper than after. Without a baseline there is no way to tell
whether a chunking change, an embedding version bump, or a reranker swap helped or hurt.

## Decision

**1. A golden question set**, built with the business, covering:

- Department-level Internal retrieval
- Sub-department Internal retrieval
- Restricted retrieval for an entitled user
- Questions whose best answer sits in a document the asker may **not** read — the correct behavior
  is a good answer from what they *can* read, or an honest empty result, never a leak
- Multi-department users
- Questions requiring synthesis across several documents

Each entry: question, expected source document(s), expected security tier, asking persona.

**2. Metrics.** Recall@k and MRR against the expected sources, plus **authorized-recall** — recall
computed only over documents the asking persona is entitled to see. Global recall is misleading
here: a system that retrieves everything scores well on recall and is a security failure.

**3. A regression gate in CI.** Metrics must not drop below the recorded baseline without an
explicit, reviewed override. Version the baseline alongside `embedding_version` and
`chunking_version` — a deliberate model change resets the baseline, a code change does not.

**4. The eval set is fixture data, not production data.** It must be safe to commit. Building it
from real restricted documents would put restricted content in the repository.

## Consequences

- Requires business-side time to build a credible question set. That is the main cost and it cannot
  be shortcut by generating questions from the documents themselves — such questions test lexical
  overlap, not usefulness.
- The eval set becomes a maintained artifact with an owner.
- CI needs a seeded index, adding to Phase 1 infrastructure work.

## Open

- Who owns the golden set, and how often is it refreshed?
- Is an LLM-as-judge component justified for answer quality, or is source-retrieval accuracy
  sufficient for the gate? Recommendation: start with retrieval accuracy only — it is objective,
  cheap, and stable — and add judged answer quality later if retrieval accuracy proves insufficient
  as a proxy.
