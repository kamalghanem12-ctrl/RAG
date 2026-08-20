"""Group membership truncation — retained and re-aimed at the expansion path.

ADR-0009 is largely dissolved by ADR-0012: Entra no longer carries document
entitlements, so the app-roles-versus-groups question no longer has an
authorization decision resting on it.

**The failure mode did not disappear. It moved.** Group expansion during ACL
synchronization still has to enumerate membership, and a truncated or partial
membership list silently narrows document access exactly as a truncated `groups`
claim would have. Sync is a better place for it — batch work can page, retry, and
fail loudly without failing a user's query — but "better place" is not "solved".

What makes it dangerous is unchanged and worth restating:

- It fails *closed*, so it is not an immediate breach.
- It therefore presents as a **permissions bug**, not a security one.
- Permissions bugs get fixed fast and locally, under pressure from a senior user
  who cannot see documents they know they should.
- The fastest fix is to widen something.
- It lands first on large, long-standing groups — which tend to be the ones
  attached to the most sensitive folders.

docs/adr/0009-entitlement-claims.md
docs/adr/0013-principal-mapping.md
"""

import pytest
from conftest import (
    ALLOW,
    GROUP,
    HR_GROUP,
    HR_POLICY,
    AclEntry,
    AuthorizationError,
    SyncIncompleteError,
    authorize,
    ctx,
    expand_group,
    resolve_principal,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_truncated_membership_fails_rather_than_committing():
    """A partial expansion must never be written.

    This is the whole test module in one assertion: a group whose membership could
    only be partially enumerated produces a failed sync, not a narrower
    authorization state.
    """
    with pytest.raises(SyncIncompleteError):
        sync_acls([AclEntry(HR_POLICY.document_id, "grp-truncated", GROUP, ALLOW)])


def test_large_group_expands_completely():
    """Membership counts above the old claim-truncation threshold must expand in
    full. The threshold is not the design constraint any more, but the size is
    still where implementations quietly give up."""
    members = expand_group("grp-large")
    assert len(members) > 200, (
        f"expanded only {len(members)} members — expansion appears truncated"
    )


def test_every_member_of_a_granted_group_can_read():
    """No member is silently dropped."""
    sync_acls([AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW)])
    for member in expand_group(HR_GROUP):
        assert authorize(ctx(principal_id=member), HR_POLICY) is True, (
            f"{member} lost access despite group membership"
        )


def test_groups_claim_is_not_used_for_authorization():
    """The request path needs one value: the caller's oid.

    A token whose `groups` claim is truncated must make no difference to what the
    user can read, because the claim is not consulted. If this assertion ever
    fails, the design has drifted back to reading entitlements from the token.
    """
    truncated = {
        "oid": "oid-sara",
        "tid": "<tenant-id>",
        "_claim_names": {"groups": "src1"},
        "_claim_sources": {"src1": {"endpoint": "https://graph.microsoft.com/..."}},
    }
    context = resolve_principal(truncated)
    assert context.principal_id == "oid-sara"


def test_overage_indicator_is_never_treated_as_a_membership_list():
    """If anything does read the claim, it must detect the pointer rather than
    treating it as data."""
    with pytest.raises(AuthorizationError):
        resolve_principal({"oid": "oid-sara", "groups": {"_claim_names": "src1"}})
