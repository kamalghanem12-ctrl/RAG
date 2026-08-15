# Architecture Overview

> Source: original specification §1, §2, §3, §28. Content moved unchanged.

## Mission

A production-grade, permission-aware Enterprise RAG platform. Not a PoC, demo, tutorial, or
disposable prototype.

Employees query enterprise knowledge through Claude Desktop while authorization is enforced
independently of the LLM, and unauthorized content can never enter the retrieval context.

The architecture must be: secure by design · Zero Trust · least privilege · defense in depth ·
permission-aware at retrieval time · modular · auditable · scalable · observable · production-ready ·
open-source-first wherever practical.

## Fixed stack

Do not replace any of these without first documenting the architectural reason, the security
impact, the operational impact, the alternatives considered, and the migration implications — as
an ADR.

| Layer | Technology |
|---|---|
| Identity provider | Microsoft Entra ID, SSO + MFA, domain-joined PCs |
| AI platform | Claude Enterprise; Claude Desktop is the user interface |
| Development | Claude Code as a VS Code extension on Ubuntu Server |
| Production runtime | RHEL, containerized/modular where appropriate |
| Secrets | Delinea PAM |
| Document repository | FileCloud — authoritative for content, ownership, permissions, versions |
| Embedding model | BGE-M3 |
| Vector / data store | PostgreSQL + pgvector |
| Integration | MCP — centralized server-side implementation plus a client-side shim |
| API layer | Dedicated API / API Gateway |

## Runtime architecture

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

Note that authentication does **not** follow this same single path — see
`02a-authentication-flows.md`, which corrects the original §8.

## Offline ingestion

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

## Separation of responsibilities

```text
Claude                  = reasoning and response generation
MCP Shim                = client-side MCP integration
MCP Server              = controlled AI tool interface
API Layer               = authentication, authorization, policy enforcement, orchestration
RAG Service             = retrieval, ranking, and context construction
PostgreSQL + pgvector   = persistence, metadata, vectors, database-level authorization
FileCloud               = authoritative document repository and document permissions
Entra ID                = authoritative user identity and group membership
Delinea PAM             = privileged secret management
```

## The non-negotiable principle

> Authorization must be enforced outside the LLM and before unauthorized content can enter the
> retrieval context. Each layer is a separate trust boundary. No client-side claim, MCP request,
> API parameter, prompt, or LLM decision is trusted as the final authorization control.
