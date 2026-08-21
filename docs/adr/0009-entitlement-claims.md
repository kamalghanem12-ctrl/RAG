# ADR-0009 — How Entitlements Are Carried From Entra

**Status:** **Largely dissolved** by `0012-filecloud-acl-authoritative.md`. Retained because its
failure mode relocated rather than disappeared
**Blocks:** nothing directly — the surviving concern moved to `0013-principal-mapping.md`

> **What changed.** ADR-0012 makes FileCloud authoritative for document permissions, so Entra no
> longer carries `restricted_entitlements`. The question this ADR asked — app roles versus security
> groups as the carrier — no longer has an authorization decision resting on it.
>
> **What did not change.** The groups-overage failure mode described below is still real, and it is
> still in the architecture. It moved from the *request path* to the *sync path*: group expansion in
> the ACL synchronization service must enumerate membership, and a truncated or partial membership
> list silently narrows document access exactly as a truncated claim would have.
>
> Sync is a better place for it — batch work can page, retry, and fail loudly without failing a
> user's query — but "better place" is not "solved". The analysis in this file transfers, and
> `tests/authz/test_groups_overage.py` is retained and re-aimed at expansion rather than retired.
> See `0013-principal-mapping.md`, which carries the surviving decision.

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

## VERIFY — RESOLVED 2026-08-21

Both markers are closed against Microsoft Learn. The "roughly 150–200" figure used above was
approximate; the real numbers are below and supersede it.

### Overage thresholds

| Token type | Limit |
|---|---|
| JWT | **200** groups |
| SAML | **150** groups |
| Implicit flow | **6** groups |

### Overage indicator structure

JWT and SAML omit `groups` entirely and substitute:

```json
{
  "_claim_names":   { "groups": "src1" },
  "_claim_sources": { "src1": { "endpoint": "<url to get this user's group membership>" } }
}
```

Implicit flow is different in shape, not just in threshold: it emits a boolean `hasgroups: true`
with **no endpoint hint at all**. SAML carries the pointer as a
`http://schemas.microsoft.com/claims/groups.link` attribute claim. Code that checks only for
`_claim_names` misses the implicit-flow case.

### The finding that matters most, and was not in this ADR

**The `_claim_sources` endpoint may still point at the legacy Azure AD Graph** (`graph.windows.net`),
which breaks if legacy endpoints are blocked — and they increasingly are. Microsoft's guidance is
explicit: applications **must not rely on the value** of the overage claim, only on its **presence**,
and must construct their own Microsoft Graph call.

That inverts the naive implementation. The endpoint handed to you in the token is not the endpoint to
call. Use `getMemberObjects` with `{"securityEnabledOnly": false}`, or `transitiveMemberOf` for
direct plus transitive membership.

### App roles

**Confirmed: app roles are not subject to the group-overage mechanism.** This was the central claim
in the recommendation above and it holds.

Limits, which the ADR asked about and did not know:

- **1,200 total entries** across *all* application-manifest collections combined — `appRoles`,
  `keyCredentials`, `identifierUris`, `redirectUris`, `requiredResourceAccess`,
  `oauth2PermissionScopes`. App roles compete with redirect URIs and API permissions for one shared
  budget, so "a role per entitlement" has a ceiling that is lower than it looks.
- **1,500 app role assignments** per user, group, or service principal, across all app roles —
  including assignments where the resource service principal has been soft-deleted.

Two operational gotchas that would have presented as "roles don't work":

- Roles must be assigned under **Enterprise applications → Users and groups**. Defining them on the
  app registration alone does not activate them.
- `roles` must be added as an **optional claim** in Token configuration to be emitted.
- If a **service principal** is added to a group and the app role is assigned to that group, Entra
  does **not** emit the `roles` claim. Group-assigned roles work for users, not for service
  principals.

### Group filtering is a weaker mitigation than it appears

The documented way to stay under the limit is to emit only "Groups assigned to the application". But
that option **does not support indirect membership** — only groups the user is a *direct* member of —
and it requires Microsoft Entra ID P1. Under ADR-0013 this matters: a filtered claim would
under-report nested membership, which is the same silent narrowing by another route.

### Sources

- [ID token claims reference — groups overage claim](https://learn.microsoft.com/entra/identity-platform/id-token-claims-reference#groups-overage-claim) — retrieved 2026-08-21
- [Access token claims reference — payload claims](https://learn.microsoft.com/entra/identity-platform/access-token-claims-reference#payload-claims) — retrieved 2026-08-21
- [Configure group claims and app roles in tokens](https://learn.microsoft.com/security/zero-trust/develop/configure-tokens-group-claims-app-roles#group-overages) — retrieved 2026-08-21
- [Add app roles to your application](https://learn.microsoft.com/entra/identity-platform/howto-add-app-roles-in-apps) — retrieved 2026-08-21
- [Microsoft Entra service limits and restrictions](https://learn.microsoft.com/entra/identity/users/directory-service-limits-restrictions#overview) — retrieved 2026-08-21
- [Understand the app manifest — manifest limits](https://learn.microsoft.com/entra/identity-platform/reference-microsoft-graph-app-manifest#common-issues) — retrieved 2026-08-21
