"""Entra-to-FileCloud principal mapping — the oid is the key, never the email.

Two systems name the same person differently, and the bridge between them is an
authorization control. Get it wrong in one direction and the user reads nothing;
get it wrong in the other and they read someone else's documents.

docs/adr/0013-principal-mapping.md
"""

import pytest
from conftest import (
    ALLOW,
    HR_POLICY,
    SARA,
    USER,
    AclEntry,
    PrincipalMappingError,
    authorize,
    ctx,
    resolve_principal,
    retrievable_ids,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


def test_oid_is_the_canonical_key():
    """The principal is resolved from the validated oid, not from any other claim."""
    context = resolve_principal({"oid": SARA, "preferred_username": "sara@derayah.com"})
    assert context.principal_id == SARA


def test_email_alone_does_not_resolve_a_principal():
    """Email is mutable, reassignable after a departure, and one person can present
    several aliases. Any of those turns a mapping into a mis-grant.

    A token carrying an email but no oid must not resolve to a principal.
    """
    with pytest.raises((PrincipalMappingError, KeyError)):
        resolve_principal({"preferred_username": "sara@derayah.com"})


def test_unmapped_identity_grants_nothing(unmapped):
    """A valid Entra identity with no active principal_map entry resolves to zero
    grants — never a best-effort match on name or address."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    assert authorize(unmapped, HR_POLICY) is False
    assert retrievable_ids(unmapped) == set()


def test_unmapped_principal_in_an_acl_is_not_silently_skipped():
    """An ACL naming a principal with no mapping must fail loudly.

    Silently skipping is how a whole group's access disappears with nobody
    noticing, and how a locally-created FileCloud account gets ignored instead of
    investigated.
    """
    with pytest.raises(PrincipalMappingError):
        sync_acls([AclEntry(HR_POLICY.document_id, "fc-local-unknown", USER, ALLOW)])


def test_deactivated_mapping_revokes_access():
    """principal_map is soft-deleted rather than hard-deleted. An inactive mapping
    must stop granting immediately — a departure is a revocation."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    departed = ctx(principal_id=SARA, filecloud_principal_id=None)
    assert authorize(departed, HR_POLICY) is False
