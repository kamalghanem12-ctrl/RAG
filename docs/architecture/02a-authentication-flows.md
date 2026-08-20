# Authentication Flows

> Source: original specification §8.
> **Redrawn.** The original diagram showed a single chain, `Claude Desktop → Enterprise SSO/MFA →
> MCP Shim → API`, which implies a handoff that cannot exist. See "Correction record" at the end.

## Three independent flows

They share an identity provider. They share nothing else — different protocols, different relying
parties, different lifecycles. Design and review them separately.

| # | Flow | Protocol | Relying party | Interactive |
|---|---|---|---|---|
| 1 | User → Claude Enterprise | SAML SSO + MFA | **Anthropic** | Yes, browser SSO |
| 2 | MCP Shim → Derayah API | OIDC / OAuth 2.0 bearer token | **Derayah RAG API** | No — silent |
| 3 | Ingestion → FileCloud | Service principal, credentials from Delinea | FileCloud | Never |

## Flow 1 — User to Claude Enterprise

SAML SSO against Entra ID, MFA satisfied at the IdP. This authenticates the human to *Anthropic's*
service and grants the Claude Enterprise seat.

**Flow 1 produces nothing Flow 2 can consume.** The SAML assertion is issued to Anthropic as the
relying party and is consumed there. Claude Desktop does not forward it to MCP servers, and the
shim has no mechanism to obtain it. Flows 1 and 2 are separate trust domains that happen to share
an IdP.

This is not a defect to engineer around — it is precisely what makes "authorization enforced
outside the LLM" achievable. The API authenticates the user independently, from scratch, and owes
nothing to whatever Anthropic concluded about that user's identity.

Flow 1 is configured in Claude Enterprise's own tenant settings and is **outside this repository's
enforcement path**. Documented here for completeness only.

## Flow 2 — MCP Shim to Derayah API

The authorization-bearing flow. Everything in `02-authorization-model.md` depends on this token.

**Protocol: OIDC / OAuth 2.0, not SAML.** Flow 1 is SAML because it is browser SSO, human-to-app.
Flow 2 is delegated API access and requires a bearer token scoped to the API's own audience.
Conflating the two is the most common way this class of design fails.

### Silent acquisition

Recommended: **MSAL with the WAM broker, auth-code + PKCE as fallback.**

On an Entra-joined Windows PC the broker uses the machine's existing Primary Refresh Token — no
prompt, no password, MFA claims already carried by the PRT, and no bearer token for the shim to
persist. Where no PRT is available, auth-code + PKCE per the MCP authorization spec prompts once
and goes silent thereafter via refresh tokens, with the token held in OS credential storage
(DPAPI on Windows).

Both satisfy the constraint that the shim stays lightweight (`06-mcp.md`) and holds no long-lived
credentials (`08-operations.md`).

Rejected alternatives:

- **Kerberos / Integrated Windows Auth to the gateway** — yields an AD identity without Entra
  claims, and contradicts the standing rule that being domain-joined never by itself grants
  backend access.
- **Client-credentials secret in the shim** — loses user identity entirely and places a long-lived
  privileged credential in client configuration. Forbidden.

Status: recommended, not decided. → `../adr/0003-authentication-flows.md`

### Token validation at the API

Every request. No exceptions, no debug bypass.

| Check | Why |
|---|---|
| Signature | Authenticity |
| `iss` | Issued by the expected Entra tenant endpoint |
| `tid` | Correct tenant |
| **`aud`** | **Scoped to `api://<derayah-rag>`** — not Microsoft Graph, not anything Anthropic-facing |
| `exp` / `nbf` | Not expired, not premature |
| Required claims | Present and well-formed before an authorization context is built |

The `aud` check is the specific control against replay: it is what stops a token legitimately
minted for a *different* resource being presented at the RAG API. Decoding a token with any
verification disabled is a blocked pattern.
→ `tests/authz/test_token_validation.py`

### Groups claim overage

Entra truncates the `groups` claim beyond roughly 150–200 group memberships, substituting a
`_claim_names` / `_claim_sources` pointer to Microsoft Graph. At Derayah's scale this threshold
will be crossed.

The failure is dangerous because of its *direction*: reading `groups` naively sees **fewer**
memberships than the user actually holds. That fails closed, so it presents as a permissions bug
rather than a security one — and is therefore likely to be "fixed" badly, and quickly, under
delivery pressure.

**Revised by `../adr/0012-filecloud-acl-authoritative.md`.** The request path no longer reads this
claim at all. Entra establishes identity; FileCloud decides document access; group membership is
resolved by **pre-expansion during ACL synchronization**, not from the token. The API needs one
value: the caller's `oid`, mapped through `principal_map`.

The failure mode did not disappear — it **moved to the expansion step**, where the rule is
complete-or-fail rather than best-effort. A partially expanded group silently narrows access exactly
as a truncated claim would have.
→ `tests/authz/test_groups_overage.py`, retained and re-aimed at expansion
→ `../adr/0013-principal-mapping.md`

### Also required

Token refresh, revocation behavior, and failure behavior must each be explicitly designed — not
inherited from a library default. Revocation in particular is a production-readiness gate: removing
a user's entitlement must deny subsequent retrieval.

## Flow 3 — Ingestion to FileCloud

Non-interactive. A dedicated **read-only** FileCloud service identity, restricted to the approved
knowledge-base tree, with credentials retrieved from Delinea PAM at runtime.

Never a variant of Flow 2 — different lifecycle, no user identity, no delegation. See
`04-ingestion.md` and `08-operations.md`.

## Cross-platform note

The shim runs on users' **Windows** desktops. Development is Ubuntu; production runtime is RHEL.
The shim is the only cross-platform component in the system and needs its own packaging,
signing, and distribution story. → `../adr/0003-authentication-flows.md`

## Verification obligation

Every version-specific claim in this document — current Claude Desktop remote-MCP auth support,
MSAL broker availability in Python on Windows, current Entra overage thresholds — must be checked
against official Anthropic and Microsoft documentation before the corresponding ADR is ratified.
They are marked `VERIFY` in the ADR text rather than asserted here as settled fact.

## Correction record

The original §8 drew:

```text
User → Claude Desktop → Enterprise SSO/MFA → Validated Identity/Token
     → MCP Shim → MCP Server → API Layer → Token Validation → Authorization Context
```

A single chain, implying the identity established for Claude Desktop flows through to the API. It
does not and cannot. The original's own closing caution — "never assume that being domain-joined or
Windows-authenticated automatically grants backend access" — was correct and is preserved; this
document extends the same skepticism to the Claude Enterprise session itself.
