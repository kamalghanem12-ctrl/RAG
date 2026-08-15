# Trust Boundaries

> Source: original specification §4, §5. Content moved unchanged.

Eleven separate trust boundaries. **Do not assume that because two components sit inside the same
network they trust each other.**

1. User workstation
2. Claude Desktop
3. MCP Shim
4. MCP Server
5. API / Gateway
6. Identity / Authorization services
7. RAG Service
8. PostgreSQL
9. FileCloud
10. External AI / LLM services
11. FileCloud MCP — added by `../adr/0011-filecloud-mcp-scope.md`

> The original specification listed ten. The FileCloud MCP is a distinct boundary because it reaches
> user content on a path that does not traverse boundaries 4–8 at all.

For each boundary: **authentication · authorization · encryption · input validation · output
validation · logging · failure behavior.**

## The table

Rows marked **OPEN** depend on an unratified ADR. They are recorded as open rather than filled with
a plausible answer — a guessed control reads as a decided one at review time, which is how a gap
becomes invisible.

### 1. User workstation

| | |
|---|---|
| Authentication | Entra ID sign-in to the Windows device. Domain-joined fleet, with a known set of excluded laptops → `../adr/0003-authentication-flows.md` |
| Authorization | Being domain-joined grants **nothing** on the backend. Device posture is not entitlement |
| Encryption | Disk encryption is a workstation-fleet control, outside this platform's scope but load-bearing for boundary 11's local index |
| Input validation | n/a — the boundary's output is a user's typed query |
| Output validation | n/a |
| Logging | Endpoint logging is a fleet control, not this platform's |
| Failure behavior | No device access → no path to anything here. Fails closed by construction |

### 2. Claude Desktop

| | |
|---|---|
| Authentication | The user's Claude Enterprise sign-in. **Separate from, and no evidence of, Derayah backend identity** |
| Authorization | None. Claude Desktop holds no entitlement and must never hold privileged backend credentials |
| Encryption | TLS to Anthropic, managed by the client |
| Input validation | Treats nothing from the model as authorization |
| Output validation | Model output is presented to the user; it is not an instruction to any Derayah component |
| Logging | Client-side, outside Derayah's control. **Not an audit source** |
| Failure behavior | Loss of the desktop session ends the conversation. No cached entitlement survives it |

### 3. MCP Shim

| | |
|---|---|
| Authentication | Acquires a user token for the API. Mechanism **OPEN** → `../adr/0003-authentication-flows.md` (recommendation: broker-first with PKCE fallback) |
| Authorization | **None, deliberately.** The shim carries no authorization model. It forwards identity; it never asserts entitlement |
| Encryption | TLS to the MCP Server / API. Certificate validation never disabled |
| Input validation | Forwards user requests; performs no privilege-bearing interpretation |
| Output validation | Passes results through unchanged. Never re-labels or re-classifies |
| Logging | Connection lifecycle and auth failures. **No document content, no tokens** |
| Failure behavior | Token acquisition fails → no request is sent. Never degrades to an unauthenticated or service-identity call |

### 4. MCP Server

| | |
|---|---|
| Authentication | Validates the caller's token: signature, `iss`, `tid`, `aud`, `exp`/`nbf`, required claims → `02a-authentication-flows.md` |
| Authorization | **Delegates entirely to the API layer.** The MCP Server is a tool surface, never a shortcut to the database |
| Encryption | TLS inbound and outbound |
| Input validation | Tool arguments validated against the declared capability schema. No tool accepts arbitrary SQL, path, command, or URL → CLAUDE.md rule 6 |
| Output validation | Returns only what the API returned. Never synthesizes or widens a result set |
| Logging | Tool invoked, caller identity, decision, latency. Content excluded |
| Failure behavior | Any validation failure → deny. Deny is indistinguishable from not-found → **OPEN**, `../adr/0006-deny-vs-notfound.md` |

### 5. API / Gateway

| | |
|---|---|
| Authentication | The authoritative token validation point. Same checks as boundary 4, independently performed — not inherited |
| Authorization | **The Policy Enforcement Point.** Builds the authorization context server-side from validated claims. Client-supplied `department`, `sub_department`, `security_tier`, `allowed_groups`, `allowed_users`, `roles`, `permissions` are never read → CLAUDE.md rule 3 |
| Encryption | TLS terminated here; onward hops re-encrypted |
| Input validation | Full request-body validation. Authorization-bearing fields in a body are rejected, not ignored silently |
| Output validation | Only authorized rows can be present — nothing is filtered out here, because nothing unauthorized was ever fetched → CLAUDE.md rule 4 |
| Logging | Identity, decision, entitlements used, result count. Audit-grade |
| Failure behavior | Fail closed. Context that cannot be built safely → request denied, security event raised → **OPEN**, `../adr/0010-entitlement-invariants.md` |

### 6. Identity / Authorization services

| | |
|---|---|
| Authentication | Entra ID is authoritative for user identity. Its signing keys are the trust root |
| Authorization | Entitlements derived from validated claims. Carrier mechanism **OPEN** → `../adr/0009-entitlement-claims.md` (app roles vs. groups) |
| Encryption | TLS to Entra and to Graph, where Graph is used |
| Input validation | Claims validated for presence and shape. Entitlements are fully-qualified `(department, sub_department)` pairs, never bare names |
| Output validation | A truncated `groups` claim is **never** silently accepted. Detect overage; resolve or fail closed loudly |
| Logging | Token validation outcomes, overage events, context-construction failures |
| Failure behavior | Entra unreachable → deny. Degraded identity never means degraded authorization |

### 7. RAG Service

| | |
|---|---|
| Authentication | Receives an already-validated authorization context from boundary 5. Accepts no identity assertion from a client |
| Authorization | Does not decide. Executes retrieval under the context it was given; the predicate lives in `authz/` → CLAUDE.md rule 2 |
| Encryption | TLS to the database and the embedding service |
| Input validation | Query text is data. Retrieved document content is untrusted data, never instructions → CLAUDE.md rule 9 |
| Output validation | Reranker and context builder operate only on rows the predicate already permitted. Unauthorized content cannot reach them because it was never fetched |
| Logging | Query executed, candidate and returned counts, reranking outcome. Content excluded |
| Failure behavior | Missing or malformed context → refuse to query. Never falls back to an unfiltered retrieval |

### 8. PostgreSQL

| | |
|---|---|
| Authentication | Application role, credentials from Delinea. No client ever connects directly → the "Never" list below |
| Authorization | **RLS is the enforcement mechanism.** Request context set with `SET LOCAL` inside an explicit transaction; session-scoped `SET` leaks across pooled connections → **OPEN**, `../adr/0004-rls-and-pooling.md`. The application role must not own its tables, or RLS is silently inert |
| Encryption | TLS required; encryption at rest per the platform baseline → `../baselines/` |
| Input validation | Parameterized statements only. The predicate is SQL, never string-assembled from request values |
| Output validation | RLS is the output guarantee. No application-side filtering is permitted → CLAUDE.md rule 4 |
| Logging | Connection, transaction, and RLS-policy denials. Statement logging must not capture content |
| Failure behavior | No context set → RLS returns nothing. **Empty, never everything** |

### 9. FileCloud

| | |
|---|---|
| Authentication | Ingestion uses a dedicated read-only service account. Baseline pending → `../baselines/filecloud-service-account.md` (not yet written) |
| Authorization | **Authoritative for document permissions.** Whether the path-derived tier or the ACL wins on conflict is **OPEN** → `../adr/0002-acl-source-of-truth.md` |
| Encryption | TLS for API and client traffic |
| Input validation | Ingestion treats all document content as untrusted input — including anything resembling an instruction |
| Output validation | Extracted ACLs and metadata validated before they become authorization data |
| Logging | Sync runs, change detection, ACL drift, reconciliation outcomes |
| Failure behavior | Sync failure → the index goes stale, and stale is a security state. Reconciliation lag is the window in which a tightened ACL is unenforced → `../adr/0002-acl-source-of-truth.md` |

### 10. External AI / LLM services

| | |
|---|---|
| Authentication | Claude Enterprise, under Derayah's agreement. Not a Derayah-controlled component |
| Authorization | **None, and none is delegated.** The model never makes an authorization decision → CLAUDE.md rule 1 |
| Encryption | TLS in transit. Processing and retention terms **OPEN** → `../adr/0008-regulatory-scope.md` |
| Input validation | Only authorized content is ever placed in context. This is enforced upstream, not here |
| Output validation | Model output is an answer, not a command. It grants nothing and reaches no Derayah component as an instruction |
| Logging | Outside Derayah's control. Audit evidence must come from boundaries 4–8 |
| Failure behavior | Unavailable → no answer. Never a fallback that widens retrieval to compensate |

### 11. FileCloud MCP

> Local process on the user's workstation. Full design: `09-filecloud-mcp.md`.

| | |
|---|---|
| Authentication | **Holds no credentials.** Stage 1 inherits the FileCloud Desktop/Sync client's authenticated state. Stage 2 is blocked pending a password-free delegated path → `../adr/0011-filecloud-mcp-scope.md` |
| Authorization | **Inherited from FileCloud, not re-implemented.** Safe only while the MCP acts as the signed-in user and nobody else. A service account here is a total bypass — blocked by `.claude/hookify.filecloud-service-account.local.md` |
| Encryption | Stage 1 reads local disk; confidentiality rests on workstation disk encryption (boundary 1). The local search index inherits the sensitivity of what it indexes |
| Input validation | Path jail to the resolved FileCloud client root, read from `syncclientconfig.xml` and never hard-coded. Compare paths **after** full resolution; reject symlink and `..` escape rather than sanitizing |
| Output validation | Read-only. File content is untrusted data, never instructions. Citations carry path, version, and modified time so the user can verify them |
| Logging | **OPEN.** Local reads are invisible to server-side audit. If "who read what through Claude" must be answerable, this boundary has to log locally and ship those logs → `../adr/0008-regulatory-scope.md` |
| Failure behavior | Client root unreadable → report no repository. Never fall back to a guessed path or a wider directory. Content not synced is reported as not present, not as absent from FileCloud |

## Cross-boundary invariants

- **Boundaries 4–8 and boundary 11 answer to different authorities and may disagree.** A RAG denial
  is not a FileCloud denial, and a FileCloud grant is never evidence of RAG entitlement. The two
  MCPs share no credential, session, or process identity.
- **No boundary inherits a validation performed at another.** Boundaries 4 and 5 both validate the
  token, independently.
- **Every failure mode above resolves to less access, never more.**

## Never

- Treat the platform as a PoC or demo.
- Allow direct client access to PostgreSQL.
- Allow Claude Desktop to hold privileged backend credentials.
- Trust user-supplied department, group, role, or permission claims.
- Let the LLM make the final authorization decision.
- Put authorization only in a system prompt.
- Use FileCloud folder names as the sole security mechanism.
- Hard-code user permissions.
- Hard-code departments or sub-departments into application logic.
- Create an API endpoint per department or sub-department merely to represent authorization.
- Retrieve unauthorized records and filter them only after retrieval.
- Expose generic SQL execution through MCP.
- Expose arbitrary filesystem access through MCP.
- Expose shell or command execution through MCP.
- Store production secrets in source code.
- Store long-lived privileged credentials in MCP client configuration.
- Implement security-critical behavior as an opaque framework "magic" step without tests.
- Introduce a dependency or framework without documenting its architectural role and risk.

## Always

- Validate architecture before implementation.
- Separate authentication, authorization, retrieval, and generation.
- Enforce authorization outside the LLM.
- Enforce authorization before unauthorized content becomes LLM context.
- Treat FileCloud ACLs as authoritative for document permissions.
- Treat Entra ID as authoritative for user identity and group membership.
- Treat the RAG index as a derived, synchronized representation.
- Design for permission revocation and permission drift.
- Use PostgreSQL RLS and retrieval-time filtering as defense in depth.
- Add observability and auditing from the beginning.
- Implement unit, integration, security, and authorization tests.
- Prefer open-source technologies wherever practical.
- Verify current official documentation before using external frameworks or APIs — and before
  installing or configuring anything (rule R1, `../baselines/`).
- Document assumptions, trade-offs, and architectural decisions.
