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

## Environment fact, recorded 2026-08-14

Derayah's workstation fleet is **domain-joined, with a known set of excluded laptops**.

This is evidence, not a decision. It bears directly on the option set: Option A alone would leave
the excluded laptops with no path at all, since a broker acquisition needs a PRT. Option C covers
both populations by construction, which makes the fallback a production requirement rather than the
developer convenience it was described as below.

Still to establish: how many devices are excluded, why, and whether they are expected to use this
platform at all. If they are out of scope for the RAG platform entirely, the fallback's role
narrows again.

## Recommendation

**Option C.** Broker-first gives the best security properties and the silent experience on the
population that matters; PKCE fallback keeps developers unblocked without weakening production —
and, per the fact above, is also what covers the excluded laptops.

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

## VERIFY status

### RESOLVED 2026-08-21 — MSAL Python broker

Verified against Microsoft Learn. Sources at the end of this section.

| Question | Answer |
|---|---|
| Availability | **Windows 10 and above, and Windows Server 2019 and above.** MSAL.NET documents the floor more precisely as Windows 10 version 1703 (Creators Update) |
| Package | `pip install "msal[broker]>=1.20,<2"` — broker support is an extra, not in core MSAL |
| Enabling it | `PublicClientApplication(..., enable_broker_on_windows=True)` |
| Architectures | x64, x86, ARM64 |
| Silent acquisition | `acquire_token_interactive` **attempts silently first** when the Windows signed-in state is still valid, and only prompts when necessary. `prompt="select_account"` forces a prompt |
| Fallback | **MSAL falls back to a browser automatically** where WAM cannot be used |

Three findings that change the design rather than merely confirming it:

**A broker-specific redirect URI is mandatory.** The app registration must carry
`ms-appx-web://microsoft.aad.brokerplugin/<CLIENT_ID>`. Without it the broker fails with a
`broker_error` / `Status_ApiContractViolation` that does not obviously name the cause. This is an
Entra app-registration configuration item and belongs in `../baselines/entra-app-registration.md`,
which does not yet exist.

**MSAL's browser fallback is automatic, which strengthens Option C.** The recommendation below
described PKCE fallback as something to build. In practice MSAL already falls back to a browser when
WAM is unavailable, so Option C is closer to MSAL's default behaviour than to a second code path
written by hand. That lowers the cost of covering the excluded non-domain-joined laptops.

**AD FS and Azure AD B2C authorities are not supported by WAM** — MSAL falls back to a browser for
those. Not expected to apply here, since Derayah authenticates against Entra directly, but it would
silently change the experience if a federated authority were introduced later.

**Refresh tokens are device-bound and not accessible to the application.** This confirms the claim
in the Option A description above — there is genuinely no token for the shim to persist, and it is a
stronger property than "the shim chooses not to store one".

### Still unresolved — blocks ratification

```
VERIFY: current Claude Desktop support for remote MCP servers and its OAuth behavior
        — against official Anthropic MCP documentation
VERIFY: current MCP authorization specification revision — against the official MCP spec
```

Both are Anthropic/MCP-side and cannot be answered from Microsoft documentation. Neither may be
asserted from memory. An unresolved marker blocks ratification.

### Sources

- [Using MSAL Python with Web Account Manager](https://learn.microsoft.com/entra/msal/python/advanced/wam) — retrieved 2026-08-21
- [Desktop app that calls web APIs: acquire a token by using WAM](https://learn.microsoft.com/entra/identity-platform/scenario-desktop-acquire-token-wam) — retrieved 2026-08-21
- [Using MSAL.NET with Web Account Manager](https://learn.microsoft.com/entra/msal/dotnet/acquiring-tokens/desktop-mobile/wam) — retrieved 2026-08-21
