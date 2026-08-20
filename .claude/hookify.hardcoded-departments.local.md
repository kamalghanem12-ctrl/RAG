---
name: warn-hardcoded-departments
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: src[/\\].*\.py$
  - field: new_text
    operator: regex_match
    pattern: ["'](?:Commercial|Sales_Analytics|Sales|Marketing|Investments|Treasury|Compliance)["']
---

**Warning — department or sub-department name literal in application code.**

Under `src/`, a department name in a string literal means the org chart has been compiled into the
application.

**Why it matters:** departments and sub-departments change — they merge, split, and get renamed —
and each change then becomes a code change, a review, a deployment.

**Note what changed.** Under `docs/adr/0012-filecloud-acl-authoritative.md`, departments are
**metadata**, not authorization — access comes from the FileCloud ACL projection. So a department
literal is no longer *automatically* an authorization bug.

It is still worth flagging, and one case is worse than before: a branch keyed on a department name
that affects **what a user can see** is now authorization logic living outside the predicate *and*
outside the model — invisible to `tests/authz/` and to RLS both. Under the old model such a branch at
least spoke the same vocabulary as the predicate. Now it speaks none.

```python
# fine — metadata filter, narrows an already-authorized result set
stmt = select(Chunk).where(authorized(ctx)).where(Chunk.department == requested_dept)

# not fine — a visibility decision made outside the predicate
if ctx.department == "Commercial":
    stmt = select(Chunk)          # authorization skipped entirely
```

The distinction to check: does this literal **narrow** results, or does it **decide** them? Narrowing
is a filter. Deciding is authorization, and authorization lives in one place.

This is a warning, not a block, because fixtures and migrations legitimately name departments. If
this fired in `tests/` or a seed script, it is a false positive — but check that it is really one.

See `docs/architecture/01-trust-boundaries.md` ("do not hard-code departments or sub-departments
into application logic").
