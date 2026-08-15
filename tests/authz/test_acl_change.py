"""ACL change — a document moving Internal -> Restricted changes authorization.

Also the reverse, and the ingestion property that an ACL-only change must not
require re-embedding (docs/architecture/04-ingestion.md).

docs/security/authorization-tests.md
"""

import pytest
from conftest import Document, authorize, retrievable_ids

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)

DOC_ID = "d-tier-change"


def test_internal_to_restricted_denies_unentitled_user(commercial_user):
    before = Document("Commercial", "Internal", "Sales", DOC_ID)
    after = Document("Commercial", "Restricted", "Sales", DOC_ID)

    assert authorize(commercial_user, before) is True
    assert authorize(commercial_user, after) is False


def test_internal_to_restricted_still_allows_entitled_user(commercial_sales_user):
    after = Document("Commercial", "Restricted", "Sales", DOC_ID)
    assert authorize(commercial_sales_user, after) is True


def test_restricted_to_internal_opens_to_department(commercial_user):
    before = Document("Commercial", "Restricted", "Marketing", DOC_ID)
    after = Document("Commercial", "Internal", "Marketing", DOC_ID)

    assert authorize(commercial_user, before) is False
    assert authorize(commercial_user, after) is True


def test_department_move_revokes_previous_department(commercial_user):
    """A document moved out of Commercial stops being readable by Commercial
    users, even though its content and embeddings are unchanged."""
    moved = Document("HR", "Internal", "Talent", DOC_ID)
    assert authorize(commercial_user, moved) is False


def test_tier_change_visible_through_retrieval_path(commercial_user):
    """Not just the predicate — the indexed metadata must actually be updated.
    A tier change that never reaches the index is a stale ACL."""
    assert DOC_ID not in retrievable_ids(commercial_user)
