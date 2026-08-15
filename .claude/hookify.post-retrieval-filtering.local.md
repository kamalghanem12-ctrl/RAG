---
name: block-post-retrieval-filtering
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: (?:\[[^\]]*\bfor\b[^\]]*\bin\b[^\]]*\b(?:chunks|results|rows|docs|candidates|hits)\b[^\]]*\bif\b[^\]]*(?:department|security_tier|acl|entitlement))|(?:\.filter\([^)]*(?:department|security_tier|entitlement))
---

**Blocked — retrieving then filtering.**

You are applying an authorization predicate to rows that have already been fetched. That means
unauthorized content was read out of the database and into application memory.

The window between fetch and filter *is* the vulnerability. It does not matter how quickly the rows
are discarded: they were retrieved, they may be logged, they may appear in a traceback, and one
missed branch puts them in front of the model.

**Instead:** push the predicate into the SQL `WHERE` clause and let RLS enforce it independently.
The query must never return a row the user may not read.

```python
# not this
allowed = [c for c in chunks if c.department in ctx.departments]

# this
stmt = select(Chunk).where(authorized(ctx))   # src/derayah_rag/authz/
```

See `docs/architecture/02-authorization-model.md` and `docs/architecture/03-data-model.md`.

*(CLAUDE.md rule 4)*
