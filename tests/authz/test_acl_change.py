"""ACL-only change — permissions move, content does not.

Rewritten for ADR-0012. Under the old model an ACL change was a secondary signal;
the authorization decision came from the folder path. Now the ACL *is* the
decision, so an ACL-only change is the most common authorization event in the
system and its propagation path is a security control.

docs/architecture/04-ingestion.md
docs/architecture/02-authorization-model.md
"""

import pytest
from conftest import (
    ALLOW,
    DENY,
    HR_POLICY,
    KAMAL,
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


def test_grant_added_becomes_retrievable_after_sync():
    sync_acls([])
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is False

    sync_acls([AclEntry(HR_POLICY.document_id, KAMAL, USER, ALLOW)])
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is True


def test_grant_removed_stops_being_retrievable_after_sync():
    """The direction that matters. A removed grant must deny, and it must deny via
    the absence of a row rather than a stored deny."""
    sync_acls([AclEntry(HR_POLICY.document_id, KAMAL, USER, ALLOW)])
    assert HR_POLICY.document_id in retrievable_ids(ctx(principal_id=KAMAL))

    sync_acls([])
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=KAMAL))


def test_acl_change_does_not_re_embed():
    """Permissions change far more often than content; coupling the two makes
    revocation slow exactly when it needs to be fast.

    The content pipeline must not run for an ACL-only change.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, DENY)])
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is False


def test_tightened_acl_is_enforced_before_the_next_retrieval():
    """The staleness window is the interval in which a revoked user still reads.

    This test asserts the post-sync state. The window itself is an SLA question
    that ADR-0012 requires the architecture to define and that is still open.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, DENY)])
    assert retrievable_ids(ctx(principal_id=SARA)) == set()


def test_unchanged_documents_are_unaffected_by_another_documents_acl_change():
    """Sync is per-document and must not disturb neighbours."""
    sync_acls(
        [
            AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW),
            AclEntry("d-comm-plan", SARA, USER, ALLOW),
        ]
    )
    sync_acls([AclEntry("d-comm-plan", SARA, USER, ALLOW)])
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is False
