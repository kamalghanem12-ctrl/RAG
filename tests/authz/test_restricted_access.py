"""Restricted access requires an explicit entitlement for that Sub-department.

    Commercial user without Sales entitlement -> Commercial/Sales/Restricted = DENY
    Commercial user with    Sales entitlement -> Commercial/Sales/Restricted = ALLOW

docs/security/authorization-tests.md
"""

import pytest
from conftest import COMMERCIAL_SALES_INTERNAL, COMMERCIAL_SALES_RESTRICTED, authorize

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_restricted_denied_without_entitlement(commercial_user):
    assert authorize(commercial_user, COMMERCIAL_SALES_RESTRICTED) is False


def test_restricted_allowed_with_entitlement(commercial_sales_user):
    assert authorize(commercial_sales_user, COMMERCIAL_SALES_RESTRICTED) is True


def test_entitlement_does_not_remove_internal_access(commercial_sales_user):
    """Holding Restricted must not narrow anything."""
    assert authorize(commercial_sales_user, COMMERCIAL_SALES_INTERNAL) is True
