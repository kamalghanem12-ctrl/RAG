# CLAUDE.md — Production Enterprise Permission-Aware RAG Platform

## 1. Mission and Scope

Act as a **Senior Enterprise AI Architect, Solution Architect, Security Architect, and Production Software Engineer**.

This repository is for a **production-grade, permission-aware Enterprise RAG platform**. It is not a Proof of Concept (PoC), demo, tutorial, or disposable prototype.

The platform must enable employees to query enterprise knowledge through **Claude Desktop** while ensuring that authorization is enforced independently of the LLM and that unauthorized content can never enter the retrieval context.

The architecture must be:

- Secure by design
- Zero Trust
- Least Privilege
- Defense in Depth
- Permission-aware at retrieval time
- Modular
- Auditable
- Scalable
- Observable
- Production-ready
- Open-source-first wherever practical

---

# 2. Current Environment and Fixed Stack

## Identity

- **Microsoft Entra ID** is the enterprise Identity Provider.
- Authentication uses **SSO with MFA**.
- Users operate from **domain-joined PCs**.
- Identity information may include:
  - User identity
  - Department
  - Groups
  - Roles
  - Other trusted claims

## AI Platform

- **Claude Enterprise** is already deployed.
- **Claude Desktop** is the primary user-facing AI interface.
- **Claude Code** is the primary AI development environment.
- Claude Code runs as a **Visual Studio Code extension on an Ubuntu Server** used for development/engineering.

## Production Runtime

- **Operating System:** RHEL
- **Application architecture:** containerized/modular where appropriate
- **Secrets:** Delinea PAM
- **Architecture:** open-source-first wherever practical

## Document Repository

- **FileCloud** is the authoritative document repository.
- FileCloud is the source of truth for:
  - Document content
  - Document ownership
  - Document permissions / ACLs
  - Document versions

## RAG Stack

- **Embedding model:** BGE-M3
- **Vector/Data Store:** PostgreSQL + pgvector
- **RAG architecture:** permission-aware retrieval
- **Integration:** MCP
- **API Layer:** dedicated API / API Gateway
- **MCP Server:** centralized server-side MCP implementation
- **MCP Shim:** client-side integration between Claude Desktop and the centralized MCP Server

Do not replace these fixed technologies without first documenting:
1. The architectural reason.
2. The security impact.
3. The operational impact.
4. The alternatives considered.
5. The migration implications.

---

# 3. Target Production Architecture

The target logical architecture is:

```text
                              USER
                                |
                                v
                     +----------------------+
                     |    Claude Desktop    |
                     +----------+-----------+
                                |
                         MCP Shim / Client
                                |
                                v
                     +----------------------+
                     |     MCP Server       |
                     | Controlled AI Tools  |
                     +----------+-----------+
                                |
                                v
                     +----------------------+
                     |    API / Gateway     |
                     | AuthN / AuthZ /      |
                     | Policy Enforcement   |
                     +----------+-----------+
                                |
                 +--------------+---------------+
                 |                              |
                 v                              v
        +------------------+           +-------------------+
        |   RAG Service    |           | Identity / Policy |
        | Retrieval &      |           | Services          |
        | Orchestration    |           +-------------------+
        +--------+---------+
                 |
                 v
        +-------------------------+
        | PostgreSQL + pgvector   |
        | Metadata + Vectors + RLS|
        +-----------+-------------+
                    |
                    v
          Authorized Candidate Chunks
                    |
                    v
                Reranker
                    |
                    v
            Context Construction
                    |
                    v
               Claude Model
                    |
                    v
                  USER
```

Offline ingestion:

```text
                      FileCloud
                          |
                 Read-only Ingestion
                      Service
                          |
                          v
                Change Detection
                          |
                          v
                Document Processing
                          |
             +------------+------------+
             |            |            |
          Content      Metadata       ACL
          Extraction   Extraction   Extraction
             |            |            |
             +------------+------------+
                          |
                     Chunking
                          |
                 Chunk Enrichment
                          |
                      BGE-M3
                    Embeddings
                          |
                          v
                PostgreSQL + pgvector
```

---

# 4. Mandatory Trust Boundaries

Treat the following as separate trust boundaries:

1. User workstation
2. Claude Desktop
3. MCP Shim
4. MCP Server
5. API / Gateway
6. Identity / Authorization services
7. RAG Service
8. PostgreSQL
9. FileCloud
10. External AI/LLM services

For each trust boundary, explicitly define:

- Authentication
- Authorization
- Encryption
- Input validation
- Output validation
- Logging
- Failure behavior

Do not assume that because two components are inside the same network they are trusted.

---

# 5. Non-Negotiable Security Principles

## DO NOT

- Treat the platform as a PoC or demo.
- Allow direct client access to PostgreSQL.
- Allow Claude Desktop to hold privileged backend credentials.
- Trust user-supplied department/group/role/permission claims.
- Let the LLM make the final authorization decision.
- Put authorization only in a system prompt.
- Use FileCloud folder names as the sole security mechanism.
- Hard-code user permissions.
- Hard-code departments or sub-departments into application logic.
- Create an API endpoint per department/sub-department merely to represent authorization.
- Retrieve unauthorized records and filter them only after retrieval.
- Expose generic SQL execution through MCP.
- Expose arbitrary filesystem access through MCP.
- Expose shell/command execution through MCP.
- Store production secrets in source code.
- Store long-lived privileged credentials in MCP client configuration.
- Implement security-critical behavior as an opaque framework "magic" step without tests.
- Introduce a dependency/framework without documenting its architectural role and risk.

## ALWAYS

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
- Verify current official documentation before using external frameworks/APIs.
- Document assumptions, trade-offs, and architectural decisions.

---

# 6. Authorization Model

The enterprise knowledge hierarchy is:

```text
Department
|
+-- Internal
|
+-- Sub-department A
|     +-- Internal
|     +-- Restricted
|
+-- Sub-department B
|     +-- Internal
|     +-- Restricted
|
+-- ...
```

## Core Authorization Rules

### Rule 1 — Department Internal Access

If a user is authorized for a Department, the user may access:

- The Department-level `Internal` content.
- `Internal` content under every Sub-department within that Department.

Sub-department membership is **not required** for Internal content.

### Rule 2 — Sub-department Restricted Access

`Restricted` content is scoped to a specific Sub-department.

A user must have explicit Restricted entitlement for that Sub-department.

### Example

```text
Commercial/
├── Internal/
├── Sales/
│   ├── Internal/
│   └── Restricted/
├── Sales_Analytics/
│   ├── Internal/
│   └── Restricted/
└── Marketing/
    ├── Internal/
    └── Restricted/
```

A user with:

```text
department = Commercial
restricted_entitlements = [Sales]
```

must have:

```text
Commercial/Internal                   ALLOW
Commercial/Sales/Internal             ALLOW
Commercial/Sales/Restricted           ALLOW
Commercial/Sales_Analytics/Internal   ALLOW
Commercial/Sales_Analytics/Restricted DENY
Commercial/Marketing/Internal         ALLOW
Commercial/Marketing/Restricted       DENY
HR/Internal                           DENY
```

This policy must be represented explicitly in the authorization model and enforced outside the LLM.

---

# 7. Authorization Context

For every request, construct a normalized authorization context from trusted identity sources.

Conceptually:

```text
user_id
department
groups
roles
restricted_entitlements
```

Do not allow the client to define or override these values.

The effective authorization context must be derived from:

```text
Entra ID Identity
        +
Validated Groups / Roles
        +
Approved enterprise authorization mapping
```

FileCloud remains authoritative for document ACLs.

The RAG authorization layer reconciles:

```text
User Authorization
        +
Document Authorization
        =
Effective Retrieval Authorization
```

---

# 8. Authentication Flow

The intended request flow is:

```text
User
  |
  v
Claude Desktop
  |
  v
Enterprise SSO / MFA
  |
  v
Validated Identity / Token
  |
  v
MCP Shim
  |
  v
MCP Server
  |
  v
API Layer
  |
  v
Token Validation
  |
  v
Authorization Context
```

The implementation must explicitly define and validate:

- Token issuer
- Audience
- Signature
- Expiration
- Required claims
- Group/role resolution
- Token refresh
- Failure behavior
- Revocation behavior

Never assume that being domain-joined or Windows-authenticated automatically grants backend access.

---

# 9. MCP Shim Responsibilities

The MCP Shim is the client-side protocol integration.

Responsibilities:

- Connect Claude Desktop to the centralized MCP Server.
- Participate in the approved authentication flow.
- Forward user requests.
- Pass approved identity/access context.
- Handle MCP connection lifecycle.

The shim must remain lightweight.

It must not contain the authoritative authorization model.

---

# 10. MCP Server Responsibilities

The MCP Server is the controlled AI tool interface.

Responsibilities:

- Expose approved RAG capabilities.
- Validate requests.
- Validate authentication context.
- Call the API Layer.
- Return authorized results.
- Enforce tool constraints.

Preferred capabilities include:

```text
search_knowledge
retrieve_document_context
get_source_reference
```

Do not expose:

```text
execute_sql
read_any_file
run_shell_command
call_any_url
```

The MCP Server must never bypass the API authorization layer.

---

# 11. API / Gateway Responsibilities

The API Layer is the primary application-level policy enforcement point.

Responsibilities:

- Authentication validation
- Authorization
- RBAC / ABAC
- Identity and claims validation
- Department isolation
- Restricted entitlement evaluation
- Request validation
- Rate limiting
- Audit logging
- Security policy enforcement
- Calling controlled RAG operations

Do not trust client-supplied:

```text
department
sub_department
security_tier
allowed_groups
allowed_users
roles
permissions
```

These must be derived from trusted server-side identity/authorization context.

---

# 12. API Design Principle

Do not create separate security endpoints such as:

```text
/api/hr
/api/hr/talent
/api/hr/talent/restricted
/api/commercial/sales
```

Do not make URL paths the authorization mechanism.

Prefer capability-oriented endpoints such as:

```text
POST /api/v1/knowledge/search
POST /api/v1/knowledge/context
GET  /api/v1/knowledge/source/{document_id}
```

The API receives the business request, but the server independently determines the user's effective scope.

The client may provide a search query and legitimate business filters, but must never be able to elevate authorization by supplying:

- department
- sub_department
- security_tier
- allowed_groups
- allowed_users
- role
- permission

Any supplied authorization parameters must be ignored, validated, or rejected according to the security design.

---

# 13. RAG Service Responsibilities

The RAG service is responsible for:

- Query understanding
- Query routing
- Retrieval
- Metadata filtering
- ACL-aware retrieval
- Hybrid search where justified
- Reranking
- Context construction
- Source/citation handling
- Retrieval quality controls

The RAG service must consume a validated authorization context and must not invent permissions.

---

# 14. PostgreSQL + pgvector

PostgreSQL + pgvector is the fixed initial vector/data platform.

Store at minimum:

```text
documents
chunks
document_acl
authorization_metadata
ingestion_jobs
sync_state
embedding_versions
audit metadata
```

Every indexed document/chunk must support metadata such as:

```text
document_id
chunk_id
department
sub_department
security_tier
filecloud_document_id
filecloud_path
filecloud_acl_reference
classification
owner
document_version
last_modified
ingestion_timestamp
embedding_model
embedding_version
```

`security_tier` must be:

```text
Internal
Restricted
```

Folder paths are metadata and organizational structure, not the sole authorization control.

---

# 15. PostgreSQL Row-Level Security

Use PostgreSQL Row-Level Security as a database-level defense-in-depth control.

Target model:

```text
Validated User Identity
        |
        v
Authorization Context
        |
        v
Request-Scoped DB Context
        |
        v
RLS + Retrieval Predicates
        |
        v
Authorized Rows Only
```

Explicitly design:

- RLS policies
- Secure database roles
- Request/session context
- Connection pooling behavior
- Transaction boundaries
- Privilege separation
- Bypass prevention
- Failure behavior

Never retrieve unauthorized rows and remove them later in application memory.

---

# 16. Retrieval Authorization Rule

Conceptually:

```text
ALLOW Internal
    IF document.department == user.department

ALLOW Restricted
    IF document.department == user.department
    AND document.security_tier == Restricted
    AND document.sub_department
        IN user.restricted_entitlements
```

The rule must be enforced before unauthorized chunks are sent to:

- Reranker
- Context builder
- Prompt
- Claude

The LLM must never receive unauthorized content.

---

# 17. FileCloud Ingestion

FileCloud is the authoritative repository for:

- Document content
- Document permissions
- Document version
- Document ownership

Use a dedicated **read-only FileCloud service identity**.

Restrict it to the approved knowledge-base tree.

The ingestion system must support:

- New documents
- Modified documents
- Deleted documents
- ACL-only changes
- Document movement
- Department changes
- Security-tier changes
- Version changes
- Incremental sync
- Periodic reconciliation

Pipeline:

```text
FileCloud
   |
   v
Change Detection
   |
   v
Content + Metadata + ACL Extraction
   |
   v
Chunking
   |
   v
Chunk Enrichment
   |
   v
BGE-M3
   |
   v
PostgreSQL + pgvector
```

ACL-only changes must not require unnecessary re-embedding.

The system must maintain a clear synchronization state and detect drift.

---

# 18. BGE-M3

Use **BGE-M3** for embeddings.

Track:

```text
embedding_model
embedding_version
embedding_dimension
chunking_version
preprocessing_version
```

Support controlled re-indexing when these change.

Do not destroy existing embeddings without a migration/rebuild strategy.

---

# 19. Runtime Retrieval Flow

```text
User Query
   |
   v
Identity Validation
   |
   v
Authorization Context
   |
   v
Query Router
   |
   v
ACL-aware Retrieval
   |
   v
PostgreSQL + pgvector
   |
   v
Authorized Candidate Chunks
   |
   v
Reranker
   |
   v
Context Builder
   |
   v
Claude
```

Evaluate and use where appropriate:

- Vector search
- Metadata filtering
- ACL filtering
- Hybrid search
- Query routing
- Search fan-out
- Reranking
- pgvector iterative scans where selective ACL filters could cause recall starvation

Never trade security for retrieval performance.

---

# 20. FileCloud MCP vs RAG MCP

Treat these as different capabilities.

## FileCloud MCP

Used for live repository operations such as:

- Browse
- Exact filename search
- Retrieve an exact document
- Access current versions
- Open/download/retrieve source artifacts

It can operate against the user's authorized FileCloud access path.

## Enterprise RAG MCP

Used for:

- Semantic enterprise search
- Permission-aware retrieval
- RAG orchestration
- Reranking
- Knowledge retrieval

It queries the RAG index and does not need a live FileCloud request for every semantic query.

These two capabilities must not share or bypass one another's authorization boundaries.

---

# 21. Secrets and PAM

Use **Delinea PAM** for production secrets and privileged credentials.

Never:

- Hard-code secrets
- Commit secrets
- Store production credentials in Git
- Place long-lived privileged credentials in the MCP Shim
- Put database service credentials in the user's Claude configuration

Implement:

- Least-privileged service identities
- Secret retrieval
- Rotation
- Auditing
- Failure behavior
- Emergency recovery

---

# 22. Security Requirements

Protect against:

- Cross-department data leakage
- Restricted-content leakage
- Prompt injection
- MCP abuse
- Client parameter manipulation
- Token theft
- Privilege escalation
- Stale ACLs
- Permission drift
- Database bypass
- Service-account compromise
- Malicious documents
- Index poisoning
- Sensitive aggregation leakage

Treat all retrieved document content as **untrusted data** and never as trusted system instructions.

---

# 23. Mandatory Authorization Tests

Build automated tests for:

### Department isolation

```text
Commercial user -> Commercial/Internal = ALLOW
Commercial user -> HR/Internal = DENY
```

### Internal inheritance

```text
Commercial user -> Commercial/Sales/Internal = ALLOW
Commercial user -> Commercial/Marketing/Internal = ALLOW
```

### Restricted access

```text
Commercial user without Sales entitlement
-> Commercial/Sales/Restricted = DENY

Commercial user with Sales entitlement
-> Commercial/Sales/Restricted = ALLOW
```

### Cross-subdepartment isolation

```text
Sales Restricted user
-> Sales/Restricted = ALLOW
-> Marketing/Restricted = DENY
```

### Multi-department user

Validate legitimate multi-department access without creating unintended Restricted access.

### Revocation

Remove a user's entitlement and verify subsequent retrieval is denied.

### ACL change

Change a document from Internal to Restricted and verify authorization behavior.

### Deletion

Delete the source document and verify it is no longer retrievable.

### Manipulation

Attempt to bypass authorization through:

- MCP parameters
- API parameters
- document ID
- FileCloud path
- department
- sub_department
- security_tier
- natural-language prompt manipulation

All must fail.

---

# 24. Production Operations

Implement from the start:

- Structured logging
- Metrics
- Tracing where justified
- Health checks
- Readiness checks
- Graceful shutdown
- Retry policies
- Dead-letter handling
- Idempotent ingestion
- Database migrations
- Dependency/version pinning
- Security scanning
- Backup/recovery
- Monitoring
- Alerting
- Audit logging

Track at minimum:

### Identity
- Authentication failures
- Token validation failures
- Authorization denials

### Ingestion
- New/modified/deleted documents
- ACL changes
- Sync lag
- Processing failures
- Embedding failures

### Retrieval
- Query latency
- Retrieval latency
- Reranker latency
- Empty retrieval
- Retrieval quality
- ACL filtering impact

### Platform
- MCP health
- API latency
- PostgreSQL health
- pgvector performance
- Connection pool health
- CPU/memory/storage

### Security
- Repeated authorization failures
- Cross-department attempts
- Restricted-content attempts
- Suspicious MCP activity

---

# 25. Production Readiness Gate

Do not declare production readiness until:

- SSO/MFA works.
- Identity/token validation works.
- Authorization is independent of the LLM.
- Department isolation works.
- Internal inheritance works.
- Restricted sub-department controls work.
- PostgreSQL RLS works.
- ACL synchronization works.
- Revocation works.
- Deleted content is no longer retrievable.
- Prompt injection cannot bypass authorization.
- MCP cannot bypass API authorization.
- Client cannot directly access PostgreSQL.
- Production secrets are managed through Delinea PAM.
- Audit trails exist.
- Backup/recovery is tested.
- Failure modes are documented.
- Security tests pass.

---

# 26. Phased Delivery Model

Claude Code must work through explicit phases.

## Phase 0 — Architecture Validation

- Inspect repository
- Validate architecture
- Identify gaps
- Produce architecture decision records
- Confirm component contracts

## Phase 1 — Project Foundation

- Repository structure
- Container/runtime structure
- Configuration management
- Logging
- Health checks
- CI/CD foundations
- Secure dependency management

## Phase 2 — Identity and Authorization Foundation

- Entra integration
- Token validation
- Authorization context
- Policy model
- Department/Internal/Restricted rules
- PostgreSQL RLS
- Authorization tests

Do not proceed until Phase 2 is validated.

## Phase 3 — FileCloud Ingestion

- Read-only service account
- Change detection
- Content processing
- Metadata extraction
- ACL extraction
- Synchronization
- Reconciliation

## Phase 4 — Chunking and Metadata

- Chunk strategy
- Enrichment
- Metadata model
- Versioning
- Security metadata

## Phase 5 — BGE-M3 Embedding Pipeline

- Embedding service
- Versioning
- Batch processing
- Failure handling
- Re-indexing strategy

## Phase 6 — PostgreSQL + pgvector

- Schema
- Indexes
- RLS
- Retrieval predicates
- Performance testing
- Backup/recovery

## Phase 7 — Retrieval

- Query processing
- ACL-aware retrieval
- Hybrid search where justified
- Reranking
- Context construction
- Evaluation

## Phase 8 — MCP Server

- Tool definitions
- MCP security
- API integration
- Authorization propagation
- Testing

## Phase 9 — MCP Shim / Claude Desktop Integration

- Client configuration
- Secure authentication flow
- Connection management
- Error handling
- Packaging/deployment

## Phase 10 — Security Validation

- Threat model
- Penetration/security tests
- Authorization bypass tests
- Prompt injection tests
- MCP abuse tests
- Permission drift tests

## Phase 11 — Observability and Operations

- Metrics
- Logs
- Traces
- Dashboards
- Alerts
- Audit

## Phase 12 — Production Hardening

- HA
- Backup/DR
- Capacity testing
- Failure testing
- Operational runbooks
- Security acceptance
- Production readiness review

---

# 27. Claude Code Delivery Rules

Before implementing any phase:

1. Inspect the current repository.
2. Review existing code and dependencies.
3. Review current official documentation for relevant technologies.
4. Identify risks and assumptions.
5. Propose the design and interface.
6. Implement only the current phase.
7. Add tests.
8. Run tests and static/security checks.
9. Document what changed.
10. Document assumptions and remaining risks.

Do not silently redesign architecture.

If an architectural assumption is unsafe or inconsistent, stop and explain the issue before implementing it.

Do not move to the next phase until the current phase has:
- Architecture validation
- Tests
- Security validation
- Documented decisions
- Known failure behavior

---

# 28. Core Separation of Responsibilities

```text
Claude
    = reasoning and response generation

MCP Shim
    = client-side MCP integration

MCP Server
    = controlled AI tool interface

API Layer
    = authentication, authorization, policy enforcement, orchestration

RAG Service
    = retrieval, ranking, and context construction

PostgreSQL + pgvector
    = persistence, metadata, vectors, and database-level authorization

FileCloud
    = authoritative document repository and document permissions

Entra ID
    = authoritative user identity and group membership

Delinea PAM
    = privileged secret management
```

## Non-Negotiable Security Principle

> **Authorization must be enforced outside the LLM and before unauthorized content can enter the retrieval context. Each layer is a separate trust boundary. No client-side claim, MCP request, API parameter, prompt, or LLM decision is trusted as the final authorization control.**
