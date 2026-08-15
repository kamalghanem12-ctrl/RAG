"""Token validation.

Added during architecture review — not in the original matrix.

The critical case is audience: a token *validly* minted for a different resource,
correctly signed by the right tenant, must still be rejected. Without that check
the API accepts any token from the tenant, including one issued to an unrelated
application — a confused-deputy path straight past every other control.

docs/architecture/02a-authentication-flows.md
"""

import pytest
from conftest import TokenValidationError, validate_token

pytestmark = pytest.mark.xfail(
    reason="Phase 2 not landed", raises=NotImplementedError, strict=True
)

AUDIENCE = "api://derayah-rag"
ISSUER = "https://login.microsoftonline.com/<tenant-id>/v2.0"
TENANT = "<tenant-id>"


def _validate(raw: str):
    return validate_token(raw, audience=AUDIENCE, issuer=ISSUER, tenant=TENANT)


VALID_TOKEN = "<fixture:valid>"


def test_valid_token_is_accepted():
    claims = _validate(VALID_TOKEN)
    assert claims["aud"] == AUDIENCE


@pytest.mark.parametrize(
    "case",
    [
        "wrong_audience",
        "wrong_issuer",
        "wrong_tenant",
        "expired",
        "not_yet_valid",
        "bad_signature",
        "unsigned_alg_none",
        "missing_required_claims",
    ],
)
def test_invalid_token_is_rejected(case):
    """Each case is a separately-minted fixture token, locally signed. Do not
    substitute a decode with verification disabled — the point is to exercise
    the real validation path."""
    with pytest.raises(TokenValidationError):
        _validate(f"<fixture:{case}>")


def test_token_for_another_audience_is_rejected():
    """Correctly signed, right tenant, not expired — issued for Microsoft Graph.
    This is the replay case, and the reason `aud` is checked at all."""
    with pytest.raises(TokenValidationError):
        _validate("<fixture:aud=https://graph.microsoft.com>")


def test_alg_none_is_rejected():
    """An unsigned token whose header claims alg=none. Rejected before any claim
    is read."""
    with pytest.raises(TokenValidationError):
        _validate("<fixture:alg=none>")
