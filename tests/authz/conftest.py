"""Shared fixtures for the authorization matrix.

**Revised by docs/adr/0012-filecloud-acl-authoritative.md.** The predicate no
longer reads (department, sub_department, security_tier). Entra authenticates;
FileCloud decides document access; PostgreSQL holds a synchronized projection
that the predicate reads under RLS.

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

from dataclasses import dataclass

import pytest

# --- Errors ---------------------------------------------------------------
# None of these subclass NotImplementedError. Tests assert on these specific
# types so the unimplemented placeholder cannot satisfy them —
# pytest.raises(Exception) would swallow NotImplementedError and pass while
# asserting nothing.


class TokenValidationError(Exception):
    """Token failed signature, iss, tid, aud, exp/nbf, or claim checks."""


class AuthorizationError(Exception):
    """An authorization context could not be built safely. Fail closed."""


class PrincipalMappingError(AuthorizationError):
    """No active principal_map entry for this Entra identity.

    Resolves to zero grants, never a best-effort email match.
    See docs/adr/0013-principal-mapping.md.
    """


class SyncIncompleteError(Exception):
    """Group expansion or ACL sync could not complete.

    Raised instead of committing a partial expansion. A partially expanded group
    is an authorization state narrower or wider than FileCloud's, with nothing in
    the data to indicate it.
    """


# --- The interface Phase 2 implements ------------------------------------

try:  # pragma: no cover - the real implementation lands in Phase 2
    from derayah_rag.authz import (  # type: ignore[import-not-found]
        authorize,
        expand_group,
        resolve_principal,
        retrievable_ids,
        sync_acls,
        validate_token,
    )
except ImportError:  # pragma: no cover

    def validate_token(raw: str, *, audience: str, issuer: str, tenant: str) -> dict:
        """Placeholder for token validation.

        Must verify signature, iss, tid, aud, exp/nbf, and required claims.
        Unchanged by ADR-0012 — Entra remains the identity authority.
        See docs/architecture/02a-authentication-flows.md.
        """
        raise NotImplementedError("Phase 2 has not landed: token validation")

    def resolve_principal(claims: dict) -> "AuthContext":
        """Placeholder for principal resolution.

        Maps the validated Entra `oid` to a FileCloud principal through
        principal_map. The `oid` is the canonical key — never the email address,
        which is mutable and reassignable. An identity with no active mapping
        raises PrincipalMappingError rather than guessing.
        """
        raise NotImplementedError("Phase 2 has not landed: principal resolution")

    def authorize(ctx_: "AuthContext", doc: "Document") -> bool:
        """Placeholder for src/derayah_rag/authz.authorize.

        The single retrieval predicate, stated in
        docs/architecture/02-authorization-model.md. Precedence, first match wins:

            1. rag_exception deny,  unexpired  -> DENY
            2. rag_exception allow, unexpired  -> ALLOW (overrides FileCloud denial)
            3. document_grant row present      -> ALLOW
            4. otherwise                       -> DENY

        In production this is enforced in SQL under RLS, not in Python. This
        function exists so the test matrix can express the expected behaviour
        before the SQL exists; Phase 2 replaces it with a thin wrapper that
        exercises the real database path.
        """
        raise NotImplementedError(
            "Phase 2 has not landed: src/derayah_rag/authz is not implemented. "
            "See docs/delivery/phases.md"
        )

    def retrievable_ids(ctx_: "AuthContext") -> set[str]:
        """Placeholder for 'what can this principal actually retrieve'.

        Distinct from authorize(): exercises the real query path, so it also
        covers deletion, sync, and exception behaviour rather than the predicate
        alone.
        """
        raise NotImplementedError("Phase 2 has not landed: retrieval path")

    def sync_acls(entries: "list[AclEntry]") -> None:
        """Placeholder for the ACL synchronization step.

        Resolves effective permissions — an explicit deny removes the grant
        rather than being stored — then expands group principals transitively
        into member users, writing user-level rows to document_grant.

        Must be complete-or-fail per document. Raises SyncIncompleteError rather
        than committing a partial expansion.
        """
        raise NotImplementedError("Phase 2 has not landed: ACL sync")

    def expand_group(group_id: str) -> set[str]:
        """Placeholder for transitive group membership expansion.

        Nested groups are flattened; cycles must terminate. A truncated or
        partial membership list silently narrows document access, so this either
        returns complete membership or raises.
        """
        raise NotImplementedError("Phase 2 has not landed: group expansion")


# --- Model ----------------------------------------------------------------

USER = "USER"
GROUP = "GROUP"

ALLOW = "allow"
DENY = "deny"

SCOPE_DOCUMENT = "document"
SCOPE_ALL = "all"


@dataclass(frozen=True)
class Document:
    """A FileCloud document. The authorization object — chunks inherit its
    effective authorization and have no permissions of their own."""

    document_id: str
    path: str
    # Metadata under ADR-0012, not authorization. Retained because business
    # filtering, ranking, and reporting still use them, and because tests must
    # prove a metadata filter cannot widen access.
    department: str | None = None
    classification: str | None = None


@dataclass(frozen=True)
class AclEntry:
    """A raw FileCloud ACL entry, as extracted. Off the decision path —
    document_acl_raw exists for audit and drift detection."""

    document_id: str
    principal_id: str
    principal_type: str = USER
    effect: str = ALLOW
    inheritance_source: str | None = None


@dataclass(frozen=True)
class Grant:
    """An effective, expanded, user-level row in document_grant. What the
    predicate reads. A denied user has no Grant."""

    document_id: str
    principal_id: str
    origin_principal: str | None = None
    grant_source: str = "direct"  # direct | group | inherited


@dataclass(frozen=True)
class RagException:
    """A governed exception. approver and expires_at are NOT NULL in the schema.
    See docs/adr/0014-rag-exceptions.md."""

    principal_id: str
    effect: str
    scope: str = SCOPE_DOCUMENT
    document_id: str | None = None
    approver: str | None = None
    expires_at: str | None = None
    exception_id: str = "exc-1"


@dataclass(frozen=True)
class AuthContext:
    """Derived server-side from validated identity. Never client-supplied.

    Deliberately small: under ADR-0012 the API resolves *who you are* and the
    database resolves *what that entitles you to*. There are no department sets
    or entitlement pairs to assemble, and therefore none to assemble wrongly.
    """

    principal_id: str = "oid-user-1"
    filecloud_principal_id: str | None = "fc-user-1"


def ctx(
    principal_id: str = "oid-user-1",
    filecloud_principal_id: str | None = "fc-user-1",
) -> AuthContext:
    return AuthContext(
        principal_id=principal_id, filecloud_principal_id=filecloud_principal_id
    )


# --- The corpus used across the matrix ------------------------------------
# Documents are named by what they are, not by the authorization tier they used
# to sit in. `department` is present only to prove it no longer decides access.

HR_POLICY = Document("d-hr-policy", "HR/Policy.pdf", "HR")
HR_SALARY_BANDS = Document("d-hr-bands", "HR/Talent/SalaryBands.xlsx", "HR")
COMMERCIAL_PLAN = Document("d-comm-plan", "Commercial/Plan2026.docx", "Commercial")
COMMERCIAL_SALES_DECK = Document("d-cs-deck", "Commercial/Sales/Deck.pptx", "Commercial")
COMMERCIAL_SALES_MARGINS = Document(
    "d-cs-margins", "Commercial/Sales/Margins.xlsx", "Commercial"
)
INVESTMENTS_POLICY = Document(
    "d-inv-policy", "Investments/Policy2026.pdf", "Investments"
)
# Deliberate path collision with Commercial/Sales — proves path shape is metadata
# and that grants are per-document, so a reused folder name cannot leak.
INVESTMENTS_SALES_MARGINS = Document(
    "d-is-margins", "Investments/Sales/Margins.xlsx", "Investments"
)

CORPUS = [
    HR_POLICY,
    HR_SALARY_BANDS,
    COMMERCIAL_PLAN,
    COMMERCIAL_SALES_DECK,
    COMMERCIAL_SALES_MARGINS,
    INVESTMENTS_POLICY,
    INVESTMENTS_SALES_MARGINS,
]

# Principals
SARA = "oid-sara"
KAMAL = "oid-kamal"
AUDITOR = "oid-auditor"
HR_GROUP = "grp-hr"


@pytest.fixture
def corpus() -> list[Document]:
    return list(CORPUS)


@pytest.fixture
def sara() -> AuthContext:
    """Granted HR/Policy.pdf via HR group membership inherited from the folder."""
    return ctx(principal_id=SARA, filecloud_principal_id="fc-sara")


@pytest.fixture
def kamal() -> AuthContext:
    """No grant on HR content."""
    return ctx(principal_id=KAMAL, filecloud_principal_id="fc-kamal")


@pytest.fixture
def unmapped() -> AuthContext:
    """A valid Entra identity with no principal_map entry. Zero grants."""
    return ctx(principal_id="oid-nomapping", filecloud_principal_id=None)


@pytest.fixture
def hr_group_acl() -> list[AclEntry]:
    """HR folder grants the HR group; both HR documents inherit it."""
    return [
        AclEntry(HR_POLICY.document_id, HR_GROUP, GROUP, ALLOW, "HR/"),
        AclEntry(HR_SALARY_BANDS.document_id, HR_GROUP, GROUP, ALLOW, "HR/"),
    ]
