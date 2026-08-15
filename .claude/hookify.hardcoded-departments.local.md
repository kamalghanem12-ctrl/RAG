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
and each change then becomes a code change, a review, a deployment. Worse, a branch keyed on a
department name is authorization logic that lives outside the single predicate, so it drifts
silently and is not covered by `tests/authz/`.

**Instead:** departments are data. They arrive in the authorization context, derived from validated
identity, and are compared by the predicate in `src/derayah_rag/authz/` — never by an `if` in a
handler.

```python
# not this
if ctx.department == "Commercial":
    ...

# this
stmt = select(Chunk).where(authorized(ctx))
```

This is a warning, not a block, because fixtures and migrations legitimately name departments. If
this fired in `tests/` or a seed script, it is a false positive — but check that it is really one.

See `docs/architecture/01-trust-boundaries.md` ("do not hard-code departments or sub-departments
into application logic").
