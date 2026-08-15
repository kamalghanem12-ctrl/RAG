# ADR-0009 — How Entitlements Are Carried From Entra

**Status:** Proposed — **needs Derayah identity review**
**Blocks:** Phase 2

## Context

The authorization context needs `departments` and `restricted_entitlements`, derived from validated
Entra identity. The original §7 says these come from "Entra ID Identity + Validated Groups/Roles +
Approved enterprise authorization mapping" without choosing a mechanism.

The choice matters more than it appears, because of a failure mode in the obvious option.

### The groups-claim overage problem

Entra truncates the `groups` claim when a user's membership count exceeds roughly 150–200,
substituting a `_claim_names` / `_claim_sources` pointer to Microsoft Graph rather than the list.
At Derayah's scale, senior and long-tenured staff will cross that threshold.

An API that reads `groups` naively then sees **fewer** entitlements than the user holds. The
direction is what makes it dangerous:

- It fails *closed* for Restricted content, so it is not an immediate breach.
- It therefore presents as a **permissions bug**, not a security one.
- Permissions bugs get fixed fast and locally, under pressure from a senior user who cannot see
  their own department's documents.
- The fastest fix is to widen something.

It also affects precisely the users most likely to hold sensitive entitlements.

## Options

**A — Entra app roles.** Roles defined on the RAG API's app registration, delivered in the `roles`
claim. Purpose-built for application authorization. Not subject to the group-overage mechanism.
Grants are auditable against the application rather than tangled in directory-wide group
membership. Requires a role-assignment process and a role per entitlement.

**B — Security groups plus Graph overage handling.** Keep groups as the source; the API detects the
overage indicator and resolves full membership via Graph server-side. Reuses existing group
governance. Adds a Graph dependency on the request path — with its own latency, failure mode, and
throttling behavior — and the overage path is rarely exercised, so it is the path most likely to be
subtly wrong.

**C — Groups plus an approved server-side mapping table.** Entra groups remain authoritative for
membership; a change-controlled server-side table translates groups into departments and
`(department, sub_department)` entitlements. Matches §7's "approved enterprise authorization
mapping" most literally. Adds an artifact that must itself be governed, reviewed, and kept in sync.

## Recommendation

**Option A**, with C as the mapping layer if the entitlement vocabulary turns out not to map
cleanly one-to-one onto roles.

Rationale: A removes the failure mode rather than handling it. B's correctness depends on a rarely
executed code path, which is the worst place for a security control to live.

This is a recommendation. Whether Derayah's identity governance can support per-entitlement app
roles is a question for the identity owners.

## Non-negotiable regardless of option

- The API **never** trusts a truncated claim silently. Detect overage; resolve or fail closed
  loudly. → `tests/authz/test_groups_overage.py`
- Entitlements are fully-qualified `(department, sub_department)` pairs, never bare sub-department
  names. → `tests/authz/test_entitlement_qualification.py`
- The client never supplies any of this. → `../architecture/07-api.md`

## VERIFY before ratification

```
VERIFY: current Entra group-claim overage thresholds for JWT and SAML, and the exact
        overage indicator structure — against Microsoft identity platform documentation
VERIFY: app role claim behavior, limits, and whether app roles are subject to any
        equivalent overage — against Microsoft identity platform documentation
```

The 150–200 figure above is approximate and must not be relied on as stated. Resolve the marker.
