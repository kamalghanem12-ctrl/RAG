"""Deletion — a deleted source document is no longer retrievable.

A production-readiness gate. Deletion must reach the chunks and the vectors, not
only the document row: an orphaned chunk is still retrievable content.

docs/security/authorization-tests.md
"""

import pytest
from conftest import COMMERCIAL_INTERNAL, retrievable_ids

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_deleted_document_is_not_retrievable(commercial_user):
    """Deleted in FileCloud, sync has run. The user is fully authorized for it —
    which is the point: authorization is not what should be excluding it."""
    ids = retrievable_ids(commercial_user)
    assert COMMERCIAL_INTERNAL.document_id not in ids


def test_deletion_removes_chunks_not_only_the_document_row(commercial_user):
    """Chunk-level check. A document row deleted while its chunks survive leaves
    retrievable content with no source to audit against."""
    ids = retrievable_ids(commercial_user)
    assert not any(i.startswith(COMMERCIAL_INTERNAL.document_id) for i in ids)


def test_deleted_document_denial_is_indistinguishable_from_not_found():
    """A deleted document and a document that never existed must present
    identically. See ADR-0006 — otherwise deletion becomes an existence oracle."""
    pytest.skip("covered by the API-layer tests once Phase 8 lands; see ADR-0006")
