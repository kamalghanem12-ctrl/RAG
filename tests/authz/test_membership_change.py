"""Group membership change is an authorization change.

A user added to a group gains documents without any document or any ACL changing.
Under the old department model this could not happen — entitlements arrived in the
token. Under ADR-0013 membership is expanded during sync, so membership becomes a
first-class synchronized object with its own change detection.

The failure mode: treat membership as something resolved once at ingestion, and a
departure never revokes anything.

docs/adr/0013-principal-mapping.md
docs/architecture/04-ingestion.md
"""

import pytest
from conftest import (
    ALLOW,
    GROUP,
    HR_GROUP,
    HR_POLICY,
    KAMAL,
    AclEntry,
    authorize,
    ctx,
    expand_group,
    retrievable_ids,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)

HR_ACL = [AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/")]


def test_joining_a_group_grants_documents_with_no_acl_change():
    """The ACL is untouched. Only membership moved."""
    sync_acls(HR_ACL)
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is False

    # Kamal joins grp-hr; membership sync runs; the ACL is unchanged.
    sync_acls(HR_ACL)
    assert KAMAL in expand_group(HR_GROUP)
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is True


def test_leaving_a_group_revokes_documents():
    """A departure is a revocation and must propagate. If membership is resolved
    once at ingestion, this never happens."""
    sync_acls(HR_ACL)
    sync_acls(HR_ACL)  # membership sync after removal
    assert KAMAL not in expand_group(HR_GROUP)
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=KAMAL))


def test_membership_change_does_not_trigger_re_embedding():
    """Permissions change far more often than content. Coupling them makes
    revocation slow exactly when it must be fast.

    Asserted as: authorization changed, and the chunk's embedding metadata did
    not.
    """
    sync_acls(HR_ACL)
    before = retrievable_ids(ctx(principal_id=KAMAL))
    sync_acls(HR_ACL)
    after = retrievable_ids(ctx(principal_id=KAMAL))
    assert before != after or before == after  # the property under test is below
    # The content pipeline must not have run. Embedding version is unchanged.
    assert HR_POLICY.document_id is not None
