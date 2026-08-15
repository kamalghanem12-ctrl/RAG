"""Multi-department users.

Legitimate access to more than one Department must not create unintended
Restricted access in any of them.

docs/security/authorization-tests.md
"""

import pytest
from conftest import (
    COMMERCIAL_INTERNAL,
    COMMERCIAL_SALES_RESTRICTED,
    HR_INTERNAL,
    INVESTMENTS_INTERNAL,
    INVESTMENTS_SALES_RESTRICTED,
    authorize,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


@pytest.mark.parametrize(
    "doc", [COMMERCIAL_INTERNAL, INVESTMENTS_INTERNAL], ids=lambda d: d.path
)
def test_internal_allowed_in_every_held_department(multi_department_user, doc):
    assert authorize(multi_department_user, doc) is True


def test_restricted_allowed_only_where_entitled(multi_department_user):
    assert authorize(multi_department_user, COMMERCIAL_SALES_RESTRICTED) is True


def test_restricted_not_inherited_by_second_department(multi_department_user):
    """Holds (Commercial, Sales). Investments/Sales/Restricted must stay denied —
    membership of Investments does not extend the Sales entitlement into it."""
    assert authorize(multi_department_user, INVESTMENTS_SALES_RESTRICTED) is False


def test_unheld_department_still_denied(multi_department_user):
    assert authorize(multi_department_user, HR_INTERNAL) is False
