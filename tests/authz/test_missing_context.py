"""No authorization context means no rows. Never all rows.

Under ADR-0012 the request-scoped context is a single value — `rag.principal_id`,
set with SET LOCAL inside the request transaction. That is simpler to reason about
than the old context object, and simpler to get catastrophically wrong: an unset
setting must yield zero rows.

This is the failure mode RLS exists to catch. If the predicate compares against an
unset or empty principal and the comparison degenerates to TRUE, every user reads
everything, and no test of the happy path would notice.

docs/adr/0004-rls-and-pooling.md
docs/architecture/03-data-model.md
"""

import pytest
from conftest import (
    ALLOW,
    HR_POLICY,
    SARA,
    USER,
    AclEntry,
    AuthContext,
    AuthorizationError,
    authorize,
    retrievable_ids,
    sync_acls,
)

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)


@pytest.mark.parametrize("principal", ["", None])
def test_empty_principal_retrieves_nothing(principal):
    """Empty or unset, the answer is the empty set — not the corpus."""
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    broken = AuthContext(principal_id=principal, filecloud_principal_id=None)
    assert retrievable_ids(broken) == set()
    assert authorize(broken, HR_POLICY) is False


def test_request_without_context_fails_closed():
    """A request that cannot establish a context must fail rather than fall
    through to an unfiltered query.

    AuthorizationError deliberately does not subclass NotImplementedError.
    """
    with pytest.raises(AuthorizationError):
        retrievable_ids(None)  # type: ignore[arg-type]


def test_context_does_not_survive_into_the_next_request():
    """The pooling rule, asserted behaviourally.

    Session-scoped SET survives the request that set it and leaks into whichever
    request next borrows that connection — one user's authorization context
    silently applied to another user's query. SET LOCAL inside an explicit
    transaction is the only permitted form.
    """
    sync_acls([AclEntry(HR_POLICY.document_id, SARA, USER, ALLOW)])
    sara_sees = retrievable_ids(AuthContext(principal_id=SARA))
    assert HR_POLICY.document_id in sara_sees

    # A subsequent request on the same pooled connection, with no context set.
    leaked = retrievable_ids(AuthContext(principal_id="", filecloud_principal_id=None))
    assert leaked == set(), "authorization context leaked across requests"
