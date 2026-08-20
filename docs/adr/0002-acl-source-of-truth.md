# ADR-0002 — FileCloud ACL vs. Path-Derived Tier: Which Is Authoritative?

**Status:** **Superseded** by `0012-filecloud-acl-authoritative.md`, which resolves this as
**Option B**
**Blocks:** nothing further — retained as the record of the question and the options considered

> **Resolution.** ADR-0012 selects Option B: the FileCloud ACL is authoritative and the path-derived
> tier model is retired as an access control. This ADR recommended Option A; that recommendation was
> not adopted. The reason is capability rather than a defect in Option A — the
> `(department, sub_department, security_tier)` model can express organizational shape but cannot
> express a grant to one named person, an inherited folder permission, a group grant, or a
> documented exception.
>
> ADR-0012 requires the same security and information-governance ratification this ADR called for,
> and has not received it. The "Open" questions at the end of this file carry forward to ADR-0012
> unchanged: the acceptable reconciliation lag for a tightened ACL, and whether FileCloud exposes ACL
> change events or must be polled.

## Context

The original specification asserts two incompatible things.

§17: *"FileCloud is the authoritative repository for document content, permissions, version and
ownership."*

§14/§16: the retrieval predicate enforces on `department`, `sub_department`, and `security_tier` —
columns derived from the FileCloud **folder path** at ingestion time. §14 then adds: *"Folder paths
are metadata and organizational structure, not the sole authorization control."*

But the predicate is *entirely* path-derived. `filecloud_acl_reference` is stored on every chunk and
never evaluated in the decision. So either the document is wrong about FileCloud being
authoritative, or the predicate is incomplete.

This is not academic. The two sources will disagree — a document whose FileCloud ACL was tightened
by its owner but whose folder location did not change, or vice versa.

## Options

**A — Path-derived tier is authoritative; FileCloud ACL is a reconciliation input that can only
revoke.** The predicate stays as designed. Ingestion additionally reads the FileCloud ACL and marks
a chunk unavailable where the ACL is *narrower* than the path implies. Never broader — an ACL can
take access away but never grant it. Simple, fast, fail-closed on conflict.

**B — FileCloud ACL is authoritative; the tier model is a derived convenience.** The predicate must
evaluate materialized ACL entries per document. Truest to §17, but couples retrieval latency to ACL
cardinality and makes the elegant `(department, sub_department, security_tier)` predicate a
secondary index rather than the control.

**C — Both must agree; disagreement quarantines the document.** Strictest. Any drift removes the
document from the index and raises an operational alert. Highest confidence, highest operational
burden, and a single mis-set folder can hide a document from everyone.

## Recommendation

**Option A**, on the grounds that it preserves a predicate that is cheap to enforce under RLS while
still honoring FileCloud as the ultimate restraint. The "can only revoke, never grant" asymmetry is
what makes it safe.

This is a recommendation. The choice is a security-policy decision about what Derayah considers the
system of record for document permissions, and belongs to the security and information-governance
owners.

## Consequences

Under A: ingestion must extract and compare both; drift detection must alarm on divergence;
`document_acl` becomes a revocation list rather than a grant list. The reconciliation interval
becomes a security parameter — it is the window during which a tightened ACL is not yet enforced.

## Open

- What is the acceptable reconciliation lag, in the worst case, for a *tightened* ACL?
- Does FileCloud expose ACL change events, or must reconciliation poll?
