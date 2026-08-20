---
name: warn-wildcard-rag-exception
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: src[/\\].*\.(?:py|sql)$
  - field: new_text
    operator: regex_match
    pattern: (?i)scope["']?\s*[:=]\s*["']all["']
---

**Warning — corpus-wide RAG exception in application code.**

You are writing a `scope = 'all'` exception. Per `docs/adr/0014-rag-exceptions.md` that grants its
principal read access to **every indexed document**, overriding FileCloud denial, across every
department and classification.

This is permitted — it was requested explicitly, and ADR-0014 implements it. This warning exists
because it should never be created incidentally.

**Before proceeding, confirm:**

- The row has a **named `approver`** and a real `expires_at`. Both are `NOT NULL`, so the insert
  fails without them — but a placeholder name satisfies the constraint and defeats the point.
- The grant is **audit-logged with its `exception_id`** when it decides a retrieval. Otherwise a
  corpus-wide read is indistinguishable from ordinary authorized use, which is the difference
  between an answerable and an unanswerable audit question.
- Creation raises an **alert**. A wildcard exception coming into existence is a security event, not
  a configuration change.
- You are not using this where a **seeded test corpus** would do. If the need is "tests must exercise
  real authorization outcomes", fixtures with known ACLs are the tool, and they carry no production
  risk.

**`rag_exception` write access is equivalent to read access to the entire corpus.** Database
privileges, change control, and approval routing must reflect that equivalence.

ADR-0014 records this as accepted risk **R1, with no approver** — an open finding that must be zero
before production. If you are the person who would approve it, approve it in the ADR by name rather
than by writing code.

Test: `tests/authz/test_rag_exceptions.py`
