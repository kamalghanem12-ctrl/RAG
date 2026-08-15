---
name: warn-phase-order-gate
enabled: true
event: prompt
action: warn
conditions:
  - field: user_prompt
    operator: regex_match
    pattern: (?i)\bphase\s*(?:1[0-2]|\d)\b|\bnext phase\b|\bproduction[- ]ready\b|\bgo live\b
---

**Phase work — check the gate before starting.**

`docs/delivery/phases.md` defines twelve phases and the rule that each completes before the next
begins. Two gates are hard:

**Phase 2 (Identity and Authorization) blocks everything downstream.** Nothing in Phases 3–12 is
meaningful until authorization works and `pytest tests/authz` is green rather than `xfail`. Building
retrieval on an unvalidated authorization core means rebuilding it.

**Production readiness is a checklist with an exit code**, in `docs/architecture/08-operations.md` —
not a judgement call. Do not declare readiness while any item is open.

**Before implementing any phase:**

1. Inspect the current repository
2. Review existing code and dependencies
3. Review current official documentation — and satisfy rule R1 for anything being installed
4. Identify risks and assumptions
5. Propose the design and interface
6. Implement **only the current phase**
7. Add tests
8. Run tests and static/security checks
9. Document what changed
10. Document assumptions and remaining risks

**Do not silently redesign architecture.** If an assumption looks unsafe or inconsistent, stop and
explain before implementing it.

Current phase: **Phase 0 — Architecture Validation.** Five ADRs still need named Derayah owners.
