"""Revocation — removing an entitlement denies subsequent retrieval.

A production-readiness gate. Revocation that is merely eventually-consistent is
revocation that does not work at the moment it is needed.

docs/security/authorization-tests.md
"""

import pytest
from conftest import COMMERCIAL_SALES_RESTRICTED, authorize, ctx, retrievable_ids

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_predicate_denies_after_entitlement_removed():
    before = ctx(departments=("Commercial",), entitlements=(("Commercial", "Sales"),))
    after = ctx(departments=("Commercial",), entitlements=())

    assert authorize(before, COMMERCIAL_SALES_RESTRICTED) is True
    assert authorize(after, COMMERCIAL_SALES_RESTRICTED) is False


def test_department_removal_denies_everything_in_it():
    before = ctx(departments=("Commercial",))
    after = ctx(departments=())

    from conftest import COMMERCIAL_INTERNAL

    assert authorize(before, COMMERCIAL_INTERNAL) is True
    assert authorize(after, COMMERCIAL_INTERNAL) is False


def test_retrieval_path_reflects_revocation_not_just_the_predicate():
    """The predicate is not the only place authorization is applied. Exercise the
    real query path too — a cached context or a stale session variable would pass
    the unit test above and still serve revoked content."""
    revoked = ctx(departments=("Commercial",), entitlements=())
    assert COMMERCIAL_SALES_RESTRICTED.document_id not in retrievable_ids(revoked)
