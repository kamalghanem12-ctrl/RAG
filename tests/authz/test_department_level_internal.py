"""Department-level Internal content has no Sub-department.

Added during architecture review — not in the original matrix.

`Commercial/Internal` is stored with `sub_department IS NULL`. Two things must hold:
the Internal branch of the predicate must not reference `sub_department` at all, and
the NULL must never reach the Restricted branch — `NULL IN (...)` evaluates to NULL
rather than false, which excludes the row under RLS. That is fail-closed and therefore
safe, but it must be deliberate.

docs/architecture/02-authorization-model.md
"""

import pytest
from conftest import COMMERCIAL_INTERNAL, Document, authorize, ctx

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_department_level_internal_is_reachable(commercial_user):
    assert COMMERCIAL_INTERNAL.sub_department is None
    assert authorize(commercial_user, COMMERCIAL_INTERNAL) is True


def test_reachable_without_any_entitlements():
    """No restricted entitlements at all — the NULL sub_department must not
    cause the Internal branch to consult the entitlement set."""
    user = ctx(departments=("Commercial",), entitlements=())
    assert authorize(user, COMMERCIAL_INTERNAL) is True


def test_null_subdepartment_restricted_is_denied():
    """A malformed document — Restricted at department level, with no
    Sub-department to scope it to. There is no entitlement that could match it,
    so it must be denied rather than falling through."""
    malformed = Document("Commercial", "Restricted", None, "d-malformed")
    user = ctx(
        departments=("Commercial",),
        entitlements=(("Commercial", "Sales"), ("Commercial", "Marketing")),
    )
    assert authorize(user, malformed) is False


def test_null_does_not_match_an_entitlement_with_null_subdepartment():
    """Belt and braces: even if a (department, None) pair somehow reached the
    entitlement set, it must not unlock department-level Restricted content."""
    malformed = Document("Commercial", "Restricted", None, "d-malformed-2")
    user = ctx(departments=("Commercial",), entitlements=(("Commercial", None),))  # type: ignore[arg-type]
    assert authorize(user, malformed) is False
