---
name: block-session-scoped-db-context
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(?:py|sql)$
  - field: new_text
    operator: regex_match
    pattern: (?i)(?:execute\(\s*["'`]?\s*SET\s+(?!LOCAL\b)[a-z_]+\.)|(?:set_config\s*\([^)]*,\s*(?:False|false)\s*\))
---

**Blocked — session-scoped database context on a pooled connection.**

`SET` without `LOCAL` (or `set_config(..., false)`) sets the value for the *session*, not the
transaction. On a pooled connection the session outlives the request that set it.

**The failure:** the next request to borrow that connection inherits the previous user's
authorization context. Under RLS that is a silent cross-user data leak — the query succeeds, rows
are returned, nothing looks wrong. It is load-dependent and will not reproduce in single-user
testing.

**Instead:**

```python
async with conn.begin():
    await conn.execute(text("SET LOCAL app.user_id = :uid"), {"uid": ctx.user_id})
    # ...query...
```

or `set_config('app.user_id', uid, True)` — the third argument `true` meaning transaction-local.

Every data-path query runs inside an explicit transaction. Read-only queries included.

See `docs/adr/0004-rls-and-pooling.md`.

*(CLAUDE.md rule 5)*
