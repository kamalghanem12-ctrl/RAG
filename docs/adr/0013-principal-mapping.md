# ADR-0013 — Entra-to-FileCloud Principal Mapping and Group Expansion

**Status:** Proposed — **needs Derayah identity review**
**Blocks:** Phase 2, 3 (ADR-0012 cannot be implemented without it)

## Context

Under `0012-filecloud-acl-authoritative.md` the API authenticates a user through Entra ID and then
asks the projection what that user may read. Those two systems name people differently. Something
has to bridge them, and the bridge is an authorization control: get it wrong and either the user
reads nothing, or the user reads someone else's documents.

FileCloud ACLs may reference any mix of FileCloud-local users, AD/LDAP users, Entra-synchronized
users, FileCloud groups, and AD/LDAP groups. Which of these Derayah's instance actually contains is
an unresolved factual question (section 6 of the change request) and is the first thing identity
owners need to answer.

## Decision 1 — the join key

Use the **Entra object ID (`oid`)** as the canonical principal identifier, resolved through an
explicit mapping table to whatever identifier FileCloud uses for the same person.

**Email address is not an authorization key.** It is mutable, it is reassignable after an employee
leaves, it can differ between UPN and primary SMTP, and aliases mean one person can present several.
Any of those turns a mapping into a mis-grant. Email may be used as a *reconciliation hint* to
detect unmapped principals, never as the key that grants access.

An Entra identity with **no** confirmed FileCloud principal mapping resolves to **zero grants**, not
to a best-effort match. Fail closed.

## Decision 2 — group membership is pre-expanded during synchronization

This is the decision that keeps the request path clean.

The sync service resolves group principals into their member users and writes **user-level** grant
rows. Every row in `document_grant` names a user. At request time the API needs only the caller's
`oid`; it needs no `groups` claim, no Graph call, and no live FileCloud lookup.

### Why the alternatives were rejected

**Matching against the Entra `groups` claim** would walk directly back into ADR-0009's failure mode.
Entra truncates that claim past roughly 150–200 memberships and substitutes a pointer. An API
reading it naively sees fewer memberships than the user holds, so the user silently loses access to
documents they are entitled to. The direction is what makes it dangerous: it fails closed, so it
presents as a permissions bug rather than a security one, it lands on senior and long-tenured staff
first, and the fastest fix under pressure is to widen something.

**A live FileCloud lookup per request** would be authoritative and always fresh, but reintroduces
exactly the runtime dependency sections 2 and 14 of the change request exclude — FileCloud latency
on every query, FileCloud availability as a hard dependency, and API load that scales with query
volume rather than with change volume.

## What pre-expansion costs, stated plainly

**The overage problem relocates; it does not disappear.** Group expansion still has to enumerate
membership, and it now happens in the sync service rather than on the request path. That is a better
place for it — it is batch work, it can page, it can retry, it can fail loudly without failing a
user's query — but it is still the step where a truncated or partial membership list silently
narrows access.

Consequences that follow:

- **Expansion must be complete or the sync must fail.** A partially expanded group is worse than a
  failed sync, because a failed sync is visible and a partial one is not. No partial commit.
- **`tests/authz/test_groups_overage.py` is retained and re-aimed** at the expansion step rather
  than retired. The claim-truncation scenario becomes an expansion-truncation scenario.
- **Membership changes are authorization changes.** A user added to a group gains documents without
  any document or ACL changing. Group membership must therefore be a first-class synchronized
  object with its own change detection, not a lookup performed once at ingestion.
- **Write amplification.** One group grant on a folder inherited by 10,000 documents, expanded
  across 200 members, is 2,000,000 grant rows. The projection schema in
  `../architecture/03-data-model.md` must be designed for that shape from the start — it is the
  normal case, not the pathological one.
- **Nested groups must be flattened transitively**, and cycles must terminate. A group containing a
  group is ordinary in AD.

## Required mapping table

```text
principal_map
    entra_oid              stable, the canonical key
    filecloud_principal_id whatever FileCloud uses natively
    principal_type         USER | GROUP
    mapping_source         how the link was established
    verified_at            when it was last confirmed
    active                 soft-delete rather than hard delete
```

Unmapped-principal handling is a security property, not an operational nicety: a FileCloud ACL
naming a principal with no mapping must raise an alert and grant nothing. Silent skipping of
unmapped principals is how a whole group's access disappears without anyone noticing, and it is also
how an attacker-created local FileCloud account could otherwise be quietly ignored rather than
investigated.

## Open questions for identity owners

- Which principal types does Derayah's FileCloud instance actually contain? Are FileCloud users
  Entra-synchronized, AD-synchronized, or locally created?
- Is there a stable, non-email identifier common to both systems, or must the mapping be maintained
  explicitly?
- Where does authoritative **group membership** come from for expansion — AD, Entra, or FileCloud
  itself? If FileCloud groups are AD-backed, is AD or FileCloud the truth when they differ?
- Are there FileCloud-local accounts with no directory counterpart? If so, can they hold ACL entries
  on knowledge-base content, and what should the projection do with them?
- What is the acceptable lag for a **group membership** change, as distinct from an ACL change? A
  departure that removes someone from a group is a revocation and may warrant a tighter SLA.

## VERIFY status

### RESOLVED 2026-08-21 — Entra membership enumeration

Full detail and sources in `0009-entitlement-claims.md`. What bears on the expansion design here:

**Use `transitiveMemberOf` or `getMemberObjects`, not the endpoint in the token.** Microsoft's
guidance is that an application must not rely on the *value* of `_claim_sources` — only its presence
— because that endpoint may still reference the legacy Azure AD Graph (`graph.windows.net`), which
breaks where legacy endpoints are blocked. The sync service must construct its own Microsoft Graph
call.

`transitiveMemberOf` matters specifically for this ADR: expansion must be **transitive**, and Graph
exposes direct-and-transitive membership as a first-class query rather than something to compute by
walking nested groups. That removes the cycle-termination problem from our code and puts it in
Graph's.

**Group filtering is not an available shortcut.** The documented mitigation for large memberships —
emitting only "Groups assigned to the application" — **does not support indirect membership**, and
requires Entra ID P1. Under this ADR that would under-report nested membership, which is the same
silent narrowing this ADR exists to prevent. Do not reach for it.

**Confirmed thresholds:** 200 groups for JWT, 150 for SAML, 6 for implicit flow. The overage indicator
differs in shape by flow: `_claim_names`/`_claim_sources` for JWT and SAML, a bare boolean
`hasgroups: true` with no endpoint hint for implicit flow. Since the request path under this ADR
reads no groups claim at all, these numbers are now a *sync-path* constraint on how membership is
paged and retried — not a request-path one.

### Still unresolved — blocks ratification

```
VERIFY: FileCloud principal model and group semantics at the deployed version, including nested
        group support and whether the API exposes expanded membership or only direct members
        — against FileCloud official documentation
```

This is the one that decides how much work expansion actually is. If FileCloud exposes only direct
members, the sync service must resolve nesting itself on the FileCloud side as well as the directory
side. Blocked on the deployed FileCloud version — see `../baselines/filecloud.md`, open finding #1.
