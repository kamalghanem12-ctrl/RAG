"""Shared fixtures for the authorization matrix.

These tests are the production-readiness gate (docs/security/authorization-tests.md).
They are written against the interface Phase 2 will implement, not against a stub —
so they fail with NotImplementedError until the real predicate lands, and start
passing the moment it is correct.

Every test module carries:

    pytestmark = pytest.mark.xfail(
        reason="Phase 2 not landed", raises=NotImplementedError, strict=True
    )

`strict=True` matters: an xpass is reported as a failure. That is deliberate. If a
test passes while the predicate is unimplemented, the test is asserting something
weaker than it should.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import pytest

try:  # pragma: no cover - the real implementation lands in Phase 2
    from derayah_rag.authz import authorize  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover

    def authorize(ctx: "AuthContext", doc: "Document") -> bool:
        """Placeholder for src/derayah_rag/authz.authorize.

        The single retrieval predicate, stated in
        docs/architecture/02-authorization-model.md:

            document.department IN user.departments
            AND (
                  document.security_tier = 'Internal'
               OR (
                      document.security_tier = 'Restricted'
                  AND (document.department, document.sub_department)
                      IN user.restricted_entitlements
                  )
            )

        In production this is enforced in SQL under RLS, not in Python. This
        function exists so the test matrix can express the expected behaviour
        before the SQL exists; Phase 2 replaces it with a thin wrapper that
        exercises the real database path.
        """
        raise NotImplementedError(
            "Phase 2 has not landed: src/derayah_rag/authz is not implemented. "
            "See docs/delivery/phases.md"
        )


class TokenValidationError(Exception):
    """Raised when a token fails signature, iss, tid, aud, exp/nbf, or claim checks.

    Deliberately NOT a subclass of NotImplementedError. Tests assert on this
    specific type so that the unimplemented placeholder cannot satisfy them —
    `pytest.raises(Exception)` would swallow NotImplementedError and pass while
    asserting nothing.
    """


class AuthorizationError(Exception):
    """Raised when an authorization context cannot be built safely — malformed
    entitlements (ADR-0010), unresolved groups overage (ADR-0009). Fail closed."""


try:  # pragma: no cover
    from derayah_rag.authz import (  # type: ignore[import-not-found]
        build_context,
        retrievable_ids,
        validate_token,
    )
except ImportError:  # pragma: no cover

    def validate_token(raw: str, *, audience: str, issuer: str, tenant: str) -> dict:
        """Placeholder for token validation.

        Must verify signature, iss, tid, aud, exp/nbf, and required claims.
        See docs/architecture/02a-authentication-flows.md.
        """
        raise NotImplementedError("Phase 2 has not landed: token validation")

    def build_context(claims: dict) -> "AuthContext":
        """Placeholder for authorization-context construction from validated claims.

        Responsible for groups-overage handling (ADR-0009) and the entitlement
        invariant (ADR-0010).
        """
        raise NotImplementedError("Phase 2 has not landed: context construction")

    def retrievable_ids(ctx: "AuthContext") -> set[str]:
        """Placeholder for 'what can this user actually retrieve from the index'.

        Distinct from authorize(): exercises the real query path, so it also
        covers deletion and ACL-sync behaviour rather than the predicate alone.
        """
        raise NotImplementedError("Phase 2 has not landed: retrieval path")


INTERNAL = "Internal"
RESTRICTED = "Restricted"


@dataclass(frozen=True)
class Document:
    department: str
    security_tier: str
    sub_department: str | None = None
    document_id: str = "doc-1"

    @property
    def path(self) -> str:
        parts = [self.department]
        if self.sub_department:
            parts.append(self.sub_department)
        parts.append(self.security_tier)
        return "/".join(parts)


@dataclass(frozen=True)
class AuthContext:
    """Derived server-side from validated identity. Never client-supplied."""

    user_id: str = "user-1"
    departments: frozenset[str] = field(default_factory=frozenset)
    # Fully-qualified (department, sub_department) pairs — never bare names.
    # See docs/architecture/02-authorization-model.md and
    # tests/authz/test_entitlement_qualification.py for why.
    restricted_entitlements: frozenset[tuple[str, str]] = field(
        default_factory=frozenset
    )
    groups: frozenset[str] = field(default_factory=frozenset)
    roles: frozenset[str] = field(default_factory=frozenset)


def ctx(
    departments: tuple[str, ...] = (),
    entitlements: tuple[tuple[str, str], ...] = (),
    **kwargs: object,
) -> AuthContext:
    return AuthContext(
        departments=frozenset(departments),
        restricted_entitlements=frozenset(entitlements),
        **kwargs,  # type: ignore[arg-type]
    )


# --- The corpus used across the matrix ------------------------------------
# Mirrors the worked example in docs/architecture/02-authorization-model.md,
# plus Investments/Sales — a deliberate sub-department name collision with
# Commercial/Sales. See test_entitlement_qualification.py.

COMMERCIAL_INTERNAL = Document("Commercial", INTERNAL, None, "d-comm-int")
COMMERCIAL_SALES_INTERNAL = Document("Commercial", INTERNAL, "Sales", "d-cs-int")
COMMERCIAL_SALES_RESTRICTED = Document("Commercial", RESTRICTED, "Sales", "d-cs-res")
COMMERCIAL_ANALYTICS_INTERNAL = Document(
    "Commercial", INTERNAL, "Sales_Analytics", "d-ca-int"
)
COMMERCIAL_ANALYTICS_RESTRICTED = Document(
    "Commercial", RESTRICTED, "Sales_Analytics", "d-ca-res"
)
COMMERCIAL_MARKETING_INTERNAL = Document("Commercial", INTERNAL, "Marketing", "d-cm-int")
COMMERCIAL_MARKETING_RESTRICTED = Document(
    "Commercial", RESTRICTED, "Marketing", "d-cm-res"
)
HR_INTERNAL = Document("HR", INTERNAL, None, "d-hr-int")
HR_TALENT_RESTRICTED = Document("HR", RESTRICTED, "Talent", "d-hrt-res")
INVESTMENTS_INTERNAL = Document("Investments", INTERNAL, None, "d-inv-int")
INVESTMENTS_SALES_RESTRICTED = Document("Investments", RESTRICTED, "Sales", "d-is-res")

CORPUS = [
    COMMERCIAL_INTERNAL,
    COMMERCIAL_SALES_INTERNAL,
    COMMERCIAL_SALES_RESTRICTED,
    COMMERCIAL_ANALYTICS_INTERNAL,
    COMMERCIAL_ANALYTICS_RESTRICTED,
    COMMERCIAL_MARKETING_INTERNAL,
    COMMERCIAL_MARKETING_RESTRICTED,
    HR_INTERNAL,
    HR_TALENT_RESTRICTED,
    INVESTMENTS_INTERNAL,
    INVESTMENTS_SALES_RESTRICTED,
]


@pytest.fixture
def corpus() -> list[Document]:
    return list(CORPUS)


@pytest.fixture
def commercial_user() -> AuthContext:
    """Commercial department, no restricted entitlements."""
    return ctx(departments=("Commercial",))


@pytest.fixture
def commercial_sales_user() -> AuthContext:
    """Commercial department, Restricted entitlement for Commercial/Sales only."""
    return ctx(
        departments=("Commercial",), entitlements=(("Commercial", "Sales"),)
    )


@pytest.fixture
def multi_department_user() -> AuthContext:
    """Commercial and Investments; Restricted only in Commercial/Sales."""
    return ctx(
        departments=("Commercial", "Investments"),
        entitlements=(("Commercial", "Sales"),),
    )
