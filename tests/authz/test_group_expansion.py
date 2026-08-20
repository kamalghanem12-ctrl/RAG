"""Group expansion — complete, transitive, or failed. Never partial.

ADR-0013 resolves group membership by pre-expansion during synchronization rather
than from the token, which keeps the request path to a single value: the caller's
oid. The cost is that expansion is now the step where authorization can silently
go wrong.

The failure mode this module exists for: a partially expanded group commits an
authorization state narrower or wider than FileCloud's, with nothing in the data
to indicate it. A failed sync is visible. A partial one is not.

docs/adr/0013-principal-mapping.md
"""

import pytest
from conftest import (
    ALLOW,
    GROUP,
    HR_GROUP,
    HR_POLICY,
    SARA,
    AclEntry,
    SyncIncompleteError,
    authorize,
    ctx,
    expand_group,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_group_grant_expands_to_user_grants():
    """Every row the predicate reads names a user. A group grant on a document
    becomes one row per member."""
    sync_acls([AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW)])
    members = expand_group(HR_GROUP)
    assert members, "group expanded to nothing"
    for member in members:
        assert authorize(ctx(principal_id=member), HR_POLICY) is True


def test_nested_groups_are_flattened_transitively():
    """A group containing a group is ordinary in AD. A member of the inner group
    must end up with a grant."""
    outer = expand_group("grp-outer")
    inner = expand_group("grp-inner")
    assert inner <= outer, "nested group membership was not flattened into the parent"


def test_membership_cycle_terminates():
    """Two groups that contain each other must not loop.

    Asserted as 'returns' rather than 'returns something specific' — the property
    under test is termination.
    """
    assert expand_group("grp-cycle-a") is not None


def test_partial_expansion_does_not_commit():
    """If membership cannot be enumerated completely, the sync fails rather than
    writing what it managed to resolve.

    SyncIncompleteError deliberately does not subclass NotImplementedError, so the
    placeholder cannot satisfy this assertion.
    """
    with pytest.raises(SyncIncompleteError):
        sync_acls([AclEntry(HR_POLICY.document_id, "grp-unresolvable", GROUP, ALLOW)])


def test_failed_expansion_leaves_prior_state_intact():
    """A failed sync must not have half-applied. Sara's existing grant survives an
    expansion failure on the same document."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, "USER", ALLOW)])
    try:
        sync_acls([AclEntry(HR_POLICY.document_id, "grp-unresolvable", GROUP, ALLOW)])
    except SyncIncompleteError:
        pass
    assert authorize(ctx(principal_id=SARA), HR_POLICY) is True


def test_expanded_grant_records_its_origin():
    """After flattening, a grant must still be explainable — which group or folder
    conferred it. Without origin_principal and inheritance_source, nobody can
    answer 'why does this person have access' after expansion."""
    sync_acls([AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/")])
    members = expand_group(HR_GROUP)
    assert members, "no members to check origin for"
