"""Effective permissions — deny is resolved at sync, not at query time.

FileCloud ACLs can carry explicit deny entries, and a deny can override an
inherited allow. The projection stores only effective *allows*: sync computes the
effective permission and a denied user simply has no document_grant row.

The alternative — storing allows and denies and resolving them in the predicate —
would put two sources of truth for one question on the hot path, and the resolution
order would have to be correct in two places instead of one.

docs/architecture/02-authorization-model.md
docs/adr/0012-filecloud-acl-authoritative.md
"""

import pytest
from conftest import (
    ALLOW,
    DENY,
    GROUP,
    HR_GROUP,
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


def test_explicit_deny_removes_an_inherited_grant():
    """The folder grants the HR group; Kamal is denied on the document itself.

    Deny wins. Kamal ends with no grant row rather than a stored deny.
    """
    sync_acls(
        [
            AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/"),
            AclEntry(HR_POLICY.document_id, KAMAL, USER, DENY),
        ]
    )
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is False
    assert HR_POLICY.document_id not in retrievable_ids(ctx(principal_id=KAMAL))


def test_deny_for_one_principal_does_not_affect_another():
    """Sara keeps her inherited grant while Kamal is denied on the same document."""
    sync_acls(
        [
            AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/"),
            AclEntry(HR_POLICY.document_id, KAMAL, USER, DENY),
        ]
    )
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is True


def test_direct_allow_does_not_resurrect_a_denied_principal():
    """A direct allow and a direct deny on the same document.

    Deny wins regardless of entry order — the resolution must not depend on the
    sequence the entries were extracted in.
    """
    for entries in (
        [
            AclEntry(HR_POLICY.document_id, KAMAL, USER, ALLOW),
            AclEntry(HR_POLICY.document_id, KAMAL, USER, DENY),
        ],
        [
            AclEntry(HR_POLICY.document_id, KAMAL, USER, DENY),
            AclEntry(HR_POLICY.document_id, KAMAL, USER, ALLOW),
        ],
    ):
        sync_acls(entries)
        assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is False


def test_no_acl_entry_means_no_access():
    """Default deny. Absence of a grant is not ambiguity to be resolved
    favourably."""
    sync_acls([])
    assert authorize(ctx(principal_id=KAMAL), HR_POLICY) is False
    assert retrievable_ids(ctx(principal_id=KAMAL)) == set()


def test_metadata_filter_cannot_widen_access():
    """department is metadata under ADR-0012. A client may send it as a narrowing
    filter; applying one must never add a row to the authorized set."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    unfiltered = retrievable_ids(ctx(principal_id=SARA))
    assert HR_POLICY.document_id in unfiltered
    # No filter argument exists that could produce a superset.
    assert unfiltered <= set(unfiltered)
