"""Entra groups-claim overage.

Added during architecture review — not in the original matrix.

Entra truncates `groups` beyond roughly 150-200 memberships, substituting a
`_claim_names` / `_claim_sources` pointer to Graph. Read naively, the API then sees
FEWER entitlements than the user holds.

The direction is what makes it dangerous. It fails closed, so it is not a breach —
it presents as a permissions bug, gets escalated by a senior user who cannot see
their own department's documents, and the fastest fix under pressure is to widen
something.

docs/adr/0009-entitlement-claims.md
"""

import pytest
from conftest import AuthorizationError, build_context

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)

OVERAGE_CLAIMS = {
    "oid": "user-1",
    "tid": "<tenant-id>",
    "_claim_names": {"groups": "src1"},
    "_claim_sources": {
        "src1": {"endpoint": "https://graph.microsoft.com/v1.0/users/user-1/getMemberObjects"}
    },
    # note: no "groups" key at all — this is what overage looks like
}


def test_overage_indicator_is_detected():
    """The context builder must not treat a missing `groups` key as 'no groups'."""
    context = build_context(OVERAGE_CLAIMS)
    assert context is not None


def test_overage_resolves_full_membership_or_fails_closed():
    """Two acceptable outcomes, one unacceptable one.

    Acceptable: resolve via Graph and produce the complete entitlement set, or
    raise loudly so the failure is visible.

    Unacceptable: return a context with fewer entitlements than the user holds
    and no signal that anything was truncated.
    """
    try:
        context = build_context(OVERAGE_CLAIMS)
    except AuthorizationError:
        return  # failed closed and loudly — acceptable

    assert getattr(context, "groups_resolved_via_graph", False) is True, (
        "overage was silently ignored: the context was built from a truncated "
        "claim without resolving full membership"
    )


def test_truncated_claim_is_never_silently_trusted():
    """A `groups` list present alongside an overage indicator is still truncated.
    The presence of some groups must not be read as the complete set."""
    partial = dict(OVERAGE_CLAIMS, groups=["group-a", "group-b"])

    try:
        context = build_context(partial)
    except AuthorizationError:
        return

    assert getattr(context, "groups_resolved_via_graph", False) is True, (
        "a truncated groups claim was trusted because it was non-empty"
    )


def test_no_overage_path_is_unaffected():
    """The common case must not pay for the rare one."""
    normal = {"oid": "user-1", "tid": "<tenant-id>", "groups": ["group-a"]}
    context = build_context(normal)
    assert getattr(context, "groups_resolved_via_graph", False) is False
