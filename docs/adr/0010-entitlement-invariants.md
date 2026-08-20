# ADR-0010 — Entitlement Invariants

**Status:** **Moot** under `0012-filecloud-acl-authoritative.md`
**Blocks:** nothing

> **Why moot.** This ADR asked whether a user may hold a Restricted entitlement for
> `(Commercial, Sales)` without holding Commercial department access — a state the old predicate made
> reachable and which was almost certainly unintended.
>
> ADR-0012 retires department and sub-department entitlements entirely. Authorization is a set of
> per-document grants projected from FileCloud, so there is no parent-child entitlement relationship
> left to be violated. The unpaired state cannot be constructed.
>
> Retained for the record, and because the *class* of defect it describes is worth remembering: a
> reachable state that no test would generate, because nobody writes a test for a case they assume
> cannot happen. `tests/authz/test_entitlement_invariants.py` is retired with this ADR; the
> equivalent question under the new model — can a grant exist for a principal with no valid mapping —
> is asserted by `tests/authz/test_principal_mapping.py`.

## Context

The authorization rule is:

> Every Sub-department may contain both Internal and Restricted content. All Internal content is
> accessible to everyone authorized for the parent Department, while Restricted content is
> accessible only to users explicitly authorized for that specific Sub-department.

"Accessible to everyone authorized for the parent Department" implies something the model does not
currently enforce: that Restricted access presupposes Department access.

Nothing prevents an authorization context of the form:

```text
departments             = []                          # or [Investments]
restricted_entitlements = [(Commercial, Sales)]
```

Under the predicate as written, this user can read `Commercial/Sales/Restricted` but **not**
`Commercial/Sales/Internal` — the Internal branch requires `document.department IN user.departments`,
which fails. A user with access to the sensitive documents in a sub-department but not the routine
ones.

That is almost certainly not intended. But it is currently reachable, and it is a state the test
matrix would never generate on its own, because no one writes a test for a case they assume cannot
happen.

## Options

**A — Reject at context construction.** Restricted entitlement for `(D, S)` without `D` in
`departments` is a malformed authorization context. Fail the request closed and raise a security
event, on the grounds that it indicates a directory misconfiguration or a manipulation attempt.

**B — Restricted implies parent Department access.** The context builder derives
`departments := departments ∪ {D for (D, S) in restricted_entitlements}`. Self-healing, no failed
requests, and matches the natural reading of the prose rule.

**C — Leave it legal.** Accept that the state can exist and that it grants Restricted-only access.
Defensible only if Derayah has a real case for it — a compliance or audit function with access to
one sub-department's restricted material and no business need for departmental routine documents.

## Recommendation

**Option A.**

B is more forgiving, but it *widens* access based on a state that should not exist — quietly
granting a whole department's Internal content because of what looks like a directory error. Silent
widening is the wrong default for this system.

A fails closed and makes the misconfiguration visible, which is how it gets fixed. If Derayah
identifies a genuine business case for C, it should be an explicit, named exception rather than an
accident of predicate design.

This is a recommendation. The underlying question — can an entitlement legitimately exist without
its parent department? — is a business and governance question, not a technical one.

## Consequences

Under A: the context builder gains a validation step and a distinct failure mode. Provisioning must
guarantee the invariant, which means the entitlement-granting process must grant department access
alongside — an identity-governance requirement, not just a code one. Coordinate with ADR-0009.

## Test

`tests/authz/test_entitlement_invariants.py` asserts the chosen behavior. It is written to be the
test that changes when this ADR is ratified — currently `xfail`, and deliberately so, because
asserting either behavior now would encode an undecided question as fact.
