"""Entitlements are fully-qualified (department, sub_department) pairs.

Added during architecture review — not in the original matrix.

The original specification's example used a bare `restricted_entitlements = [Sales]`.
Two departments here each own a Sub-department named `Sales`. Under bare-name
matching, an entitlement for Commercial/Sales would grant Investments/Sales/Restricted
— a cross-department leak, which is the exact boundary the whole model exists to hold.

docs/architecture/02-authorization-model.md
"""

import pytest
from conftest import (
    COMMERCIAL_SALES_RESTRICTED,
    INVESTMENTS_SALES_RESTRICTED,
    authorize,
    ctx,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_qualified_entitlement_grants_only_its_own_department():
    """The regression test for bare-name matching. If this fails, entitlements
    are being compared by sub-department name alone."""
    user = ctx(departments=("Commercial",), entitlements=(("Commercial", "Sales"),))

    assert authorize(user, COMMERCIAL_SALES_RESTRICTED) is True
    assert authorize(user, INVESTMENTS_SALES_RESTRICTED) is False


def test_department_membership_alone_does_not_grant_same_named_subdepartment():
    """Holds both departments, entitled only in Commercial/Sales."""
    user = ctx(
        departments=("Commercial", "Investments"),
        entitlements=(("Commercial", "Sales"),),
    )

    assert authorize(user, COMMERCIAL_SALES_RESTRICTED) is True
    assert authorize(user, INVESTMENTS_SALES_RESTRICTED) is False


def test_entitlement_in_unheld_department_grants_nothing():
    """Entitled to Investments/Sales but not a member of Investments.
    Whatever ADR-0010 decides about this state, it must never ALLOW here."""
    user = ctx(departments=("Commercial",), entitlements=(("Investments", "Sales"),))

    assert authorize(user, INVESTMENTS_SALES_RESTRICTED) is False
