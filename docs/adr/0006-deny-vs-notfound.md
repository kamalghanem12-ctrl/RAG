# ADR-0006 — Deny Must Be Indistinguishable From Not-Found

**Status:** Proposed
**Blocks:** Phase 7, Phase 8

## Context

The original §22 lists "sensitive aggregation leakage" as a threat and provides no control for it.
A related and more immediate gap: nothing in the specification requires that a denial be
indistinguishable from a non-existent resource.

Without that requirement, the API becomes an **existence oracle**. An attacker enumerates document
IDs and learns which exist in departments they cannot read. Existence alone is disclosure — the
presence of a document titled `Project_Falcon_Q3_Valuation` in `Investments/Restricted` is
material information even to someone who never reads a word of it.

The leak has more channels than the obvious one:

| Channel | Leak |
|---|---|
| HTTP status | `403` vs. `404` |
| Response body | "not authorized" vs. "not found" |
| Latency | An authorization check that runs only for existing documents is measurably slower |
| Citations | Titles and paths returned alongside authorized results |
| Error detail | Stack traces, validation messages naming a real path |
| Rate-limit behavior | Different throttling for real vs. fake IDs |

## Decision

**1. `404` for both.** `GET /api/v1/knowledge/source/{document_id}` returns the same status and the
same body whether the document does not exist or the user may not read it.

**2. Citations carry nothing the user could not retrieve.** A citation is only ever generated from a
chunk that passed the retrieval predicate. Never enrich a citation from a source the predicate did
not authorize.

**3. Constant-ish response path.** Do not short-circuit the authorization check when a document is
absent. The two paths should not be trivially separable by timing. Full constant-time is not the
goal; removing the obvious signal is.

**4. Rate limiting is an authorization control.** Per-user query-volume limits are the only
mitigation offered for sensitive aggregation leakage — reconstructing a restricted picture from many
individually-permitted retrievals. Treat limits as a security parameter, and alert on users
approaching them rather than only rejecting at the threshold.

## Consequences

- Support and debugging get harder: "the user says the document is missing" no longer distinguishes
  a permissions problem from a sync problem. **Server-side audit logs must record the true reason**
  — the distinction lives in telemetry, never in the response.
- The `404`-for-denied convention must be documented for API consumers, or it will be "fixed" by
  someone who reads it as a bug.

## Open

- What per-user query-volume limit is appropriate? It needs a real usage baseline, so this is
  deliberately deferred to Phase 11 rather than guessed now.
- Should repeated `404`s on non-existent IDs raise a security alert? They are the signature of
  enumeration.
