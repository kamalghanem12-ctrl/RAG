"""Internal inheritance — sub-department membership is NOT required for Internal.

    Commercial user -> Commercial/Sales/Internal     = ALLOW
    Commercial user -> Commercial/Marketing/Internal = ALLOW

docs/security/authorization-tests.md
"""

import pytest
from conftest import (
    COMMERCIAL_ANALYTICS_INTERNAL,
    COMMERCIAL_MARKETING_INTERNAL,
    COMMERCIAL_SALES_INTERNAL,
    authorize,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


@pytest.mark.parametrize(
    "doc",
    [
        COMMERCIAL_SALES_INTERNAL,
        COMMERCIAL_MARKETING_INTERNAL,
        COMMERCIAL_ANALYTICS_INTERNAL,
    ],
    ids=lambda d: d.path,
)
def test_internal_inherited_across_all_subdepartments(commercial_user, doc):
    """A user authorized for the Department reads Internal content in every
    Sub-department of it, without holding any Restricted entitlement."""
    assert authorize(commercial_user, doc) is True


def test_internal_inheritance_does_not_leak_restricted(commercial_user, corpus):
    """The whole point of the correction to the original predicate: inheriting
    Internal must not drag Restricted along with it."""
    restricted = [d for d in corpus if d.security_tier == "Restricted"]
    assert not any(authorize(commercial_user, d) for d in restricted)
