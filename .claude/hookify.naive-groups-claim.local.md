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

**Under the current model there is no authorization reason to read this claim at all.**

`docs/adr/0012-filecloud-acl-authoritative.md` makes FileCloud authoritative for document access,
and `docs/adr/0013-principal-mapping.md` resolves group membership by **pre-expansion during ACL
synchronization** — not from the token. The request path needs one value: the caller's `oid`,
mapped through `principal_map`. If you are reaching for `groups` to decide what someone may read,
the design has drifted.

**The failure mode did not disappear — it moved.** Group expansion in the sync service still has to
enumerate membership, and a truncated or partial membership list silently narrows document access
exactly as a truncated claim would have. Sync is a better place for it (batch work can page, retry,
and fail loudly without failing a user's query) but the rule there is absolute: **complete or fail,
never partial commit.**

If you genuinely need membership for something that is *not* an authorization decision, detect the
overage indicator rather than trusting the list:

```python
if "_claim_names" in claims and "groups" in claims["_claim_names"]:
    raise OverageError("groups claim truncated; do not use for authorization")
```

Test: `tests/authz/test_groups_overage.py`, retained and re-aimed at the expansion path.

Test: `tests/authz/test_groups_overage.py`
