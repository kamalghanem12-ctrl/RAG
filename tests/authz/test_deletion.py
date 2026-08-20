"""Deleted content must stop being retrievable.

A production-readiness gate, unchanged in spirit by ADR-0012 but with a new place
to go wrong: deletion must reach the chunks, the vectors, *and* the grant rows. An
orphaned document_grant row pointing at a deleted document is not itself a leak,
but it is drift, and drift is how a re-created document id inherits stale
authorization.

docs/architecture/04-ingestion.md
"""

import pytest
from conftest import (
    ALLOW,
    HR_POLICY,
    SARA,
    USER,
    AclEntry,
    authorize,
    ctx,
    retrievable_ids,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_deleted_document_is_not_retrievable():
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    assert HR_POLICY.document_id in retrievable_ids(ctx(principal_id=SARA))

    sync_acls([])  # document gone from FileCloud
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=SARA))


def test_deletion_removes_the_grant_rows():
    """Deletion reaching the chunks but not the projection leaves orphaned grants.

    Not a leak on its own — but a re-created document reusing the id would inherit
    them, which is.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([])
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is False


def test_deletion_reaches_chunks_and_vectors_not_only_the_document_row():
    """An erasure request must reach the chunks and the embeddings, not only the
    source document record. See docs/adr/0008-regulatory-scope.md on data-subject
    rights."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([])
    assert retrievable_ids(ctx(principal_id=SARA)) == set()
