---
name: warn-require-authz-tests
enabled: true
event: stop
action: warn
pattern: .*
---

**Before finishing — the gate, not a formality.**

If this session touched the authorization path, the data model, the API surface, the MCP tools, or
the token flow:

- [ ] `pytest tests/authz -v` was run and its result reported honestly — including failures
- [ ] No test was weakened, skipped, or `xfail`-ed to make the suite pass
- [ ] An `xpass` was investigated — it means a test asserts something weaker than it should

If this session installed or configured anything:

- [ ] `docs/baselines/<object>.md` exists, is current for the pinned version, and every deviation
      carries a **named** Derayah approver (rule R1)

If this session made an architectural choice:

- [ ] It is recorded in `docs/adr/` as **Proposed** — not silently adopted
- [ ] No approval was recorded that was not actually given
- [ ] Unresolved `VERIFY` markers were left in place, not quietly deleted

If a phase is being called done, check its gate in `docs/delivery/phases.md`: architecture
validation · tests · security validation · documented decisions · known failure behavior.

Say plainly what was not done. A partial result reported accurately is worth more than a complete
one reported optimistically.
