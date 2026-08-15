"""Entitlement invariants — the unpaired state.

Added during architecture review — not in the original matrix.

Nothing currently prevents an authorization context holding a Restricted entitlement
for (Commercial, Sales) *without* Commercial in `departments`. Under the predicate as
written, such a user reads Commercial/Sales/Restricted but not Commercial/Sales/Internal
— access to a Sub-department's sensitive documents but not its routine ones.

Almost certainly unintended, currently reachable, and a state the rest of the matrix
would never generate on its own.

**ADR-0010 has not been ratified.** The expected behaviour below encodes the
recommendation (Option A: reject at context construction). If Derayah chooses
Option B (Restricted implies parent access) or C (leave it legal), this file is
the one that changes.

docs/adr/0010-entitlement-invariants.md
"""

import pytest
from conftest import (
    COMMERCIAL_SALES_INTERNAL,
    COMMERCIAL_SALES_RESTRICTED,
    authorize,
    build_context,
    ctx,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed; ADR-0010 not ratified",
    raises=NotImplementedError,
    strict=True,
)


def test_unpaired_entitlement_is_rejected_at_context_construction():
    """ADR-0010 Option A: a Restricted entitlement whose parent Department is
    not held is a malformed context. Fail closed and raise a security event —
    it indicates a directory misconfiguration or a manipulation attempt."""
    claims = {
        "oid": "user-1",
        "roles": ["Restricted.Commercial.Sales"],
        # note: no Commercial department grant
    }
    with pytest.raises(ValueError, match="entitlement"):
        build_context(claims)


def test_unpaired_entitlement_never_grants_more_than_paired():
    """Whatever ADR-0010 decides, this must hold: an unpaired entitlement can
    never grant *more* than the same entitlement held properly. Guards against
    Option B being implemented as a silent widening."""
    unpaired = ctx(departments=(), entitlements=(("Commercial", "Sales"),))
    paired = ctx(
        departments=("Commercial",), entitlements=(("Commercial", "Sales"),)
    )

    for doc in (COMMERCIAL_SALES_INTERNAL, COMMERCIAL_SALES_RESTRICTED):
        if authorize(unpaired, doc):
            assert authorize(paired, doc), (
                f"unpaired context granted {doc.path} while the properly paired "
                "context did not — the invariant is inverted"
            )


def test_restricted_without_internal_is_not_silently_accepted():
    """The specific absurdity: sensitive documents readable, routine ones not."""
    unpaired = ctx(departments=(), entitlements=(("Commercial", "Sales"),))

    reads_restricted = authorize(unpaired, COMMERCIAL_SALES_RESTRICTED)
    reads_internal = authorize(unpaired, COMMERCIAL_SALES_INTERNAL)

    assert not (reads_restricted and not reads_internal), (
        "user can read Commercial/Sales/Restricted but not "
        "Commercial/Sales/Internal — see ADR-0010"
    )
