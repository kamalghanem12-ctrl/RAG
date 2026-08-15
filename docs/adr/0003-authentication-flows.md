# ADR-0003 — Authentication Flows and Flow 2 Silent Auth

**Status:** Proposed — **needs Derayah identity review**
**Blocks:** Phase 9 (and should be resolved long before it)

## Context

The original §8 drew one chain: `Claude Desktop → Enterprise SSO/MFA → MCP Shim → API`. That
implies the identity established for Claude Desktop reaches the API. It cannot.

There are three independent flows. See `../architecture/02a-authentication-flows.md` for the full
model; the decision needed here is the mechanism for **Flow 2**, shim → Derayah API.

The constraint set is tight: the shim must stay lightweight, must hold no long-lived privileged
credentials, must not put database or service credentials in a user's Claude configuration, and the
experience must be silent — the user has already authenticated once at the desktop and will not
accept a second prompt per query.

## Options

**A — MSAL with the WAM broker.** On an Entra-joined Windows PC, the broker acquires a token from
the machine's existing Primary Refresh Token. No prompt, no password, MFA claims already carried by
the PRT, and no token for the shim to persist — the OS holds it. Windows-only, which matches where
the shim actually ships.

**B — OAuth 2.1 authorization code + PKCE.** The MCP authorization spec's approach. One browser
prompt on first run, silent thereafter via refresh tokens. Cross-platform. Requires the shim to
store a refresh token in OS credential storage (DPAPI on Windows) and to implement refresh,
expiry, and revocation handling itself.

**C — Both: broker primary, PKCE fallback.** Try the broker; fall back where no PRT exists
(non-joined device, non-Windows developer machine). Two code paths, but survives the edge cases and
keeps the shim portable for development.

**Rejected — Kerberos / Integrated Windows Auth to the gateway.** Yields an AD identity without
Entra claims, so groups and app roles are unavailable, and it contradicts the standing rule that
being domain-joined never by itself grants backend access.

**Rejected — client-credentials secret in the shim.** Loses user identity entirely — every query
would arrive as the same service principal, making per-user authorization impossible — and places a
long-lived privileged credential in client configuration.

## Recommendation

**Option C.** Broker-first gives the best security properties and the silent experience on the
population that matters; PKCE fallback keeps developers unblocked without weakening production.

This is a recommendation. The decision belongs to Derayah's identity owners.

## Token validation (not optional under any option)

Signature · `iss` · `tid` · **`aud` = `api://<derayah-rag>`** · `exp`/`nbf` · required claims
present and well-formed.

The `aud` check is the specific control against replay — it stops a token legitimately minted for
another resource being presented here. → `tests/authz/test_token_validation.py`

## Also to be designed

Token refresh · revocation behavior · failure behavior · shim packaging, signing, and distribution
to Windows desktops (the shim is the only cross-platform component; dev is Ubuntu, production is
RHEL).

## Consequences

Under C: the shim carries an MSAL dependency and two acquisition paths. Revocation semantics differ
between them — broker-held tokens follow the PRT lifecycle, PKCE refresh tokens follow the
application's. Both must satisfy the revocation gate.

## VERIFY before ratification

```
VERIFY: current Claude Desktop support for remote MCP servers and its OAuth behavior
        — against official Anthropic MCP documentation
VERIFY: MSAL Python broker (pymsalruntime) availability, supported Windows versions,
        and PRT-based silent acquisition — against Microsoft identity platform documentation
VERIFY: current MCP authorization specification revision — against the official MCP spec
```

None of the above may be asserted from memory. An unresolved marker blocks ratification.
