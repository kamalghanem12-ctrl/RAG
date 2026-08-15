"""Department isolation.

    Commercial user -> Commercial/Internal = ALLOW
    Commercial user -> HR/Internal         = DENY

docs/security/authorization-tests.md
"""

import pytest
from conftest import COMMERCIAL_INTERNAL, HR_INTERNAL, HR_TALENT_RESTRICTED, authorize

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_own_department_internal_is_allowed(commercial_user):
    assert authorize(commercial_user, COMMERCIAL_INTERNAL) is True


def test_other_department_internal_is_denied(commercial_user):
    assert authorize(commercial_user, HR_INTERNAL) is False


def test_other_department_restricted_is_denied(commercial_user):
    assert authorize(commercial_user, HR_TALENT_RESTRICTED) is False


def test_user_with_no_departments_gets_nothing(corpus):
    """Fail closed. An empty authorization context is not a wildcard."""
    from conftest import ctx

    empty = ctx()
    assert not any(authorize(empty, doc) for doc in corpus)
