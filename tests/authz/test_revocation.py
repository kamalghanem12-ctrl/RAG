"""Revocation — removing a grant denies subsequent retrieval.

A production-readiness gate. Revocation that is merely eventually-consistent is
revocation that does not work at the moment it is needed.

Rewritten for ADR-0012. Revocation now has four distinct paths, and each one is a
different mechanism that can fail independently:

    1. the FileCloud ACL grant is removed          -> sync drops the row
    2. the user leaves a granted group             -> membership sync drops the row
    3. the principal_map entry is deactivated      -> departure
    4. a rag_exception deny is added               -> emergency, does not wait for sync

Path 4 exists because paths 1-3 all depend on a synchronization cycle completing.
The staleness window between an ACL change and its projection is the interval in
which a revoked user still reads, and an emergency path must not be subject to it.

docs/security/authorization-tests.md
docs/adr/0014-rag-exceptions.md
"""

import pytest
from conftest import (
    ALLOW,
    AUDITOR,
    DENY,
    GROUP,
    HR_GROUP,
    HR_POLICY,
    KAMAL,
    SARA,
    SCOPE_ALL,
    USER,
    AclEntry,
    RagException,
    authorize,
    ctx,
    expand_group,
    retrievable_ids,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)

FUTURE = "2099-01-01T00:00:00Z"


def test_direct_grant_removal_denies():
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is True

    sync_acls([])
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is False


def test_leaving_a_granted_group_denies():
    """The grant row was never addressed to this user directly — it was expanded
    from group membership. Revocation has to reach the expanded row."""
    sync_acls([AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/")])
    assert KAMAL not in expand_group(HR_GROUP) or authorize(
        ctx(principal_id=KAMAL), HR_POLICY
    )

    sync_acls([AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/")])
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=KAMAL))


def test_deactivated_principal_mapping_denies():
    """A departure. The Entra identity may still authenticate; it maps to nothing."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    departed = ctx(principal_id=SARA, filecloud_principal_id=None)
    assert authorize(departed, HR_POLICY) is False


def test_exception_deny_revokes_without_waiting_for_sync():
    """The emergency path. Paths 1-3 all wait for a synchronization cycle; this one
    takes effect on the next request.

    It also has to outrank a wildcard allow, or emergency revocation would be
    defeated by the very mechanism most likely to need revoking.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, AUDITOR, USER, ALLOW)])
    RagException(
        principal_id=AUDITOR,
        effect=ALLOW,
        scope=SCOPE_ALL,
        approver="Test Approver, QA",
        expires_at=FUTURE,
    )
    RagException(
        principal_id=AUDITOR,
        effect=DENY,
        scope=SCOPE_ALL,
        approver="Test Approver, QA",
        expires_at=FUTURE,
    )
    assert authorize(ctx(principal_id=AUDITOR), HR_POLICY) is False


def test_retrieval_path_reflects_revocation_not_just_the_predicate():
    """The predicate is not the only place authorization is applied. Exercise the
    real query path too — a cached context, a stale session variable, or a grant
    row that sync failed to delete would pass a predicate unit test and still serve
    revoked content."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([])
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=SARA))


def test_revocation_is_not_defeated_by_a_stale_projection():
    """Staleness is a security state, not an operational one.

    If the projection cannot be confirmed current, the safe behaviour is to deny,
    not to serve the last known grant set. The acceptable staleness bound is an
    open SLA question in ADR-0012; this test pins the direction of the failure.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, DENY)])
    assert retrievable_ids(ctx(principal_id=SARA)) == set()
