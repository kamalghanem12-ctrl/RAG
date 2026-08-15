---
name: warn-naive-groups-claim
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: claims\s*(?:\.get\(|\[)\s*["']groups["']
---

**Warning — reading the `groups` claim directly.**

Entra truncates `groups` beyond roughly 150–200 memberships, replacing the list with a
`_claim_names` / `_claim_sources` pointer to Microsoft Graph. At Derayah's scale, senior and
long-tenured staff will cross that threshold.

**Why this is worse than it looks.** Reading `groups` naively then yields **fewer** entitlements
than the user actually holds. That fails *closed*, so it is not an immediate breach — it presents
as a permissions bug. A senior user cannot see their own department's documents, it gets escalated,
and the fastest fix under pressure is to widen something.

It also hits precisely the users most likely to hold sensitive entitlements.

**Required:** detect the overage indicator and resolve full membership via Graph server-side, or
fail closed loudly. Never trust a truncated claim silently.

```python
if "_claim_names" in claims and "groups" in claims["_claim_names"]:
    groups = await resolve_groups_via_graph(claims["oid"])
else:
    groups = claims.get("groups", [])
```

Better still: carry `restricted_entitlements` as Entra **app roles**, which are not subject to this
mechanism. See `docs/adr/0009-entitlement-claims.md`.

Test: `tests/authz/test_groups_overage.py`
