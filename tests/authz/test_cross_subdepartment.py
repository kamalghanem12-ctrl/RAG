"""Cross-subdepartment isolation.

    Sales Restricted user -> Sales/Restricted     = ALLOW
    Sales Restricted user -> Marketing/Restricted = DENY

docs/security/authorization-tests.md
"""

import pytest
from conftest import (
    COMMERCIAL_ANALYTICS_RESTRICTED,
    COMMERCIAL_MARKETING_RESTRICTED,
    COMMERCIAL_SALES_RESTRICTED,
    authorize,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_entitled_subdepartment_restricted_allowed(commercial_sales_user):
    assert authorize(commercial_sales_user, COMMERCIAL_SALES_RESTRICTED) is True


@pytest.mark.parametrize(
    "doc",
    [COMMERCIAL_MARKETING_RESTRICTED, COMMERCIAL_ANALYTICS_RESTRICTED],
    ids=lambda d: d.path,
)
def test_sibling_subdepartment_restricted_denied(commercial_sales_user, doc):
    """Restricted is scoped to one Sub-department. An entitlement for Sales
    grants nothing in Marketing or Sales_Analytics — including Sales_Analytics,
    whose name shares a prefix with Sales."""
    assert authorize(commercial_sales_user, doc) is False
