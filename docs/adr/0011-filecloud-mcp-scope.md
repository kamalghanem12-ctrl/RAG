# ADR-0011 — FileCloud MCP: Scope, Authorization, and Credential Model

**Status:** Proposed — **needs Derayah security review**
**Blocks:** the FileCloud MCP track (see `../delivery/phases.md`). Does **not** block Phases 1–12.

## Context

`../architecture/06-mcp.md` already names two distinct MCP capabilities and states that they "must
not share or bypass one another's authorization boundaries." It does not say how the FileCloud MCP
authenticates, what it is allowed to read, or what happens when the two capabilities disagree. This
ADR decides that.

The requirement: an employee chatting with Claude should be able to search and cite documents in
their **own** FileCloud repository — including personal working files — and this must work for users
who have no Enterprise RAG access at all.

### The two capabilities have opposite egress profiles

This is the fact that makes the FileCloud MCP a security decision rather than an integration task.

| | RAG MCP | FileCloud MCP |
|---|---|---|
| What can reach the model | curated, indexed, permission-filtered chunks | any file the user can open |
| Who decides | Derayah's retrieval predicate, in SQL, under RLS | FileCloud's own ACL engine |
| Scope of the corpus | what ingestion chose to index | the user's entire accessible repository |
| Governed by | ADR-0002, ADR-0009, ADR-0010 | this ADR |

The RAG platform's entire design effort goes into controlling what content can reach the model. The
FileCloud MCP is a second, wider channel to the same model. That is defensible — FileCloud is the
authoritative permission source per `../architecture/01-trust-boundaries.md`, so a user reading
their own file through Claude is the same authorization decision FileCloud already makes when they
open it in Explorer. It is defensible *only* while the MCP acts strictly as that user.

Note also that Derayah has **no data-classification scheme today** (recorded in ADR-0008). There is
therefore no label on any file that could mark it as non-exportable on either path.

## What the vendor documentation actually says

Retrieved from FileCloud official documentation, 2026-08-14. Recorded here because the design turns
on it. Full baseline: `../baselines/filecloud.md`.

- **No official FileCloud MCP server exists.** This is a build, not an integration.
- The documented user API authentication is **`loginguest` with `userid` and `password`**, returning
  a session cookie the client replays on every subsequent call. No token, OIDC, or API-key path for
  user-delegated API access is documented.
- FileCloud supports **SAML 2.0 SSO with Microsoft Entra ID**, acting as the Service Provider — but
  as a browser redirect flow for the web portal, not a documented non-browser API authentication
  mechanism. The "SSO API" added in 23.251+ imports users and groups; it is provisioning, not
  delegated authentication.
- Server-side **content search** (txt, pdf, doc, docx, xls, xlsx, ppt, pptx; OCR from v20.3) and
  **metadata search** (18.1+) exist, both administrator-enabled.
- **FileCloud Sync** stores content locally — default `C:\Users\<user>\Documents\FileCloud`, path
  configurable via `syncfolderlocation` in `syncclientconfig.xml`. FileCloud Desktop offers
  per-item "always keep on this device".

### The blocker this creates

An API-backed FileCloud MCP, as documented, requires the user's FileCloud password to reach the MCP
client configuration. `../architecture/01-trust-boundaries.md` forbids exactly that:

> Store long-lived privileged credentials in MCP client configuration.

So the obvious design is closed off by a standing rule, not by preference.

## Options

**A — Desktop-backed (local).** The MCP reads the local FileCloud Sync/Desktop folder. It holds no
credentials at all: the sync client has already authenticated as the user, and what is present on
disk is by construction already scoped to what that user may access. Authorization is inherited,
not re-implemented. Works on the non-domain-joined laptops too, because it depends on the FileCloud
client being installed rather than on the domain join.

Limits: only synced or offline-pinned content is visible, not the full repository. FileCloud's
server-side content search is unavailable, so search is whatever the MCP indexes locally. Deletions
and ACL tightening are visible only as fast as the sync client applies them.

**B — API-backed (server).** The MCP calls the FileCloud REST API as the user. Full repository
coverage and server-side content and metadata search. Blocked as documented, per above, unless
FileCloud can offer a supported password-free user-delegated authentication path.

**C — Service account.** Rejected outright, and named here so it is on the record as rejected. The
RAG ingestion account is read-only across the *entire* document estate. An MCP using it would let
every user read every document through Claude — a total authorization bypass wearing the costume of
a convenience feature. This is the most dangerous reachable state in the new capability, which is
why it gets a hook rather than a sentence: `.claude/hookify.filecloud-service-account.local.md`.

## Recommendation

**A now, B gated.** Ship the desktop-backed MCP, which needs no credentials, no new trust in the
client, and no answer from anyone. Treat B as conditional on a single question to Derayah's
FileCloud administrators or the vendor:

> Is there a supported mechanism for a non-browser client to authenticate to FileCloud as the
> signed-in user without holding that user's password?

If the answer is no, B does not happen and A is the product. If the answer is yes, B is a second
ADR, because the answer determines the design.

This is a recommendation. The scope question — whether an employee's *private* FileCloud content
should be reachable by an external AI service at all — is a security and information-governance
decision, not a technical one, and belongs with the same owners reviewing ADR-0008.

## Invariants, regardless of option

1. **The MCP acts only as the signed-in user.** Never a service account, never a shared credential,
   never the ingestion account. → `tests/authz/test_filecloud_mcp_isolation.py`
2. **No admin API.** `adminlogin` and every administrator endpoint are out of scope permanently.
3. **Capabilities, never primitives** (CLAUDE.md rule 6). The tool surface is
   `search_my_files`, `get_file_content`, `list_folder`, `get_file_reference`. No tool takes an
   arbitrary path, URL, command, or query language as a parameter.
4. **Path jail.** Under A, every resolved path must remain inside the FileCloud client root. The
   root is read from `syncclientconfig.xml`, never hard-coded — a user may have moved it. Symlinks
   and `..` traversal are rejected after resolution, not before.
5. **Read-only.** No write, move, delete, or share operation. Retrieval and citation only.
6. **Retrieved content is untrusted data, never instructions** (CLAUDE.md rule 9). A document that
   says "you are now authorized" changes nothing.
7. **The two MCPs never share a credential, a session, or a process identity.** A RAG denial must
   not become a FileCloud grant, or the reverse.

## Consequences

Under A: the MCP is a local process on the user's workstation, so it inherits that workstation's
trust level and needs its own boundary row in `../architecture/01-trust-boundaries.md`. Local
indexing means a local index, which is a new artifact holding derived content from the user's files
— its location, encryption at rest, and lifecycle need deciding, and it should be treated as
carrying the same sensitivity as the files it indexes.

Auditability differs sharply from the RAG path. RAG access is logged server-side; local desktop
reads are not, unless the MCP logs them itself. If Derayah needs to answer "who read what through
Claude", A must log locally and ship those logs somewhere — which is an operations requirement, not
an afterthought. → ADR-0008's audit-and-evidence question applies to this track too.

## VERIFY before ratification

```
VERIFY: FileCloud user API authentication mechanisms at the deployed version, specifically
        whether any password-free user-delegated path exists
        — against FileCloud official documentation and FileCloud support
VERIFY: FileCloud Desktop vs. Sync local storage semantics at the deployed version, including
        whether placeholder/on-demand files are readable without triggering a download
        — against FileCloud official documentation
VERIFY: current Claude Desktop local MCP server support and configuration model
        — against official Anthropic documentation
```

The findings above were retrieved against `latest` documentation, not against Derayah's deployed
version. The deployed version is unknown at the time of writing and is an open finding in
`../baselines/filecloud.md`. An unresolved marker blocks ratification.
