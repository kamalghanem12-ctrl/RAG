# ADR-0008 — Regulatory and Data-Residency Scope

**Status:** Proposed — **needs Derayah compliance and security review**
**Blocks:** Phase 0 sign-off

## Context

The original specification is thorough on technical security and silent on regulatory obligation.
For a Saudi financial institution building a system that reads the entire enterprise document
estate and sends selected content to an external AI service, that is a material gap.

Nothing in this ADR is a compliance determination. It is a list of questions that Derayah's
compliance, legal, and security owners must answer before the architecture can be considered
validated. **No approval is expressed or implied anywhere in this repository.**

## Questions requiring an owner and an answer

### Data residency and cross-border transfer

Document content leaves Derayah's estate and enters Claude Enterprise's context on every answered
query. Required:

- Where is that content processed and where, if anywhere, is it retained?
- What are the contractual terms in the Claude Enterprise agreement regarding retention, training
  use, and sub-processors?
- Does the resulting transfer satisfy PDPL requirements for cross-border transfer of personal data,
  where document content contains any?

### SAMA Cyber Security Framework

Which control domains apply, and which of them this platform must evidence:

- Identity and access management
- Third-party / outsourcing risk (the Claude Enterprise dependency)
- Data classification and protection
- Logging, monitoring, and incident response
- Change management and secure SDLC

### PDPL

- Does the corpus contain personal data? Almost certainly yes — HR documents, customer
  correspondence.
- What is the lawful basis for processing it through this system?
- How are data-subject rights handled when a document is indexed, chunked, and embedded? An erasure
  request must reach the chunks and the vectors, not only the source document.

### Derayah data classification

The platform's `Internal` / `Restricted` tiers must be mapped to Derayah's own classification
scheme. If Derayah's scheme has more levels, the two-tier model is insufficient and the data model
changes — which is a Phase 2 impact, not a Phase 10 one.

**Recorded 2026-08-14: Derayah has no data-classification scheme at present.** This is a factual
answer to the question above, not a determination that none is required. It has two consequences
that compliance and security must weigh:

- The two-tier model maps onto nothing. `Internal` and `Restricted` are currently definitions this
  platform invents, derived from FileCloud folder paths — see `0002-acl-source-of-truth.md`. Whether
  that is an acceptable basis for an access-control tier in a regulated institution is a governance
  question.
- **No document carries a label marking it as non-exportable.** There is therefore no mechanism, on
  either retrieval path, by which the platform could recognize content that must not leave the
  estate. Any such rule would have to be expressed some other way.

If a scheme is later issued, it is a re-review trigger for this ADR, the data model, and
`0011-filecloud-mcp-scope.md`.

### The FileCloud MCP widens the egress surface

`0011-filecloud-mcp-scope.md` adds a second path from Derayah content to Claude, with a materially
different profile: the RAG path sends curated, indexed, permission-filtered chunks, while the
FileCloud MCP can send **any file the user can open**, including personal working files never
intended for the knowledge base.

Every residency and cross-border question above therefore applies to that path too, over a wider
corpus and without an ingestion stage at which anything could be excluded. The audit question below
applies with particular force: local desktop reads produce no server-side record unless the MCP is
built to create one.

### Audit and evidence

What must be retained, for how long, and in what form, to satisfy an internal-audit or regulator
request about who accessed what through this system?

## Impact if deferred

Answers to the classification question change the data model. Answers to the residency question may
constrain what content may be indexed at all. Both are cheap to accommodate in Phase 2 and expensive
after Phase 7.

## Next step

Route to Derayah compliance, legal, and information-security owners. This ADR is a request for
determination, not a proposal to be approved.
