# Phased Delivery and Delivery Rules

> Source: original specification §26, §27. Content moved unchanged.

## Before implementing any phase

1. Inspect the current repository.
2. Review existing code and dependencies.
3. Review current official documentation for the relevant technologies — and, for anything being
   installed or configured, satisfy rule R1 (`../baselines/`).
4. Identify risks and assumptions.
5. Propose the design and interface.
6. Implement **only the current phase**.
7. Add tests.
8. Run tests and static/security checks.
9. Document what changed.
10. Document assumptions and remaining risks.

**Do not silently redesign architecture.** If an architectural assumption is unsafe or
inconsistent, stop and explain before implementing it.

**Do not advance** until the current phase has: architecture validation · tests · security
validation · documented decisions · known failure behavior.

## Phases

### Phase 0 — Architecture Validation ← current
Inspect repository · validate architecture · identify gaps · produce ADRs · confirm component
contracts.

Status: ADRs 0001–0010 drafted in `../adr/`. Five need Derayah review before Phase 2 can proceed.
The trust-boundary table in `../architecture/01-trust-boundaries.md` is still outstanding.

### Phase 1 — Project Foundation
Repository structure · container/runtime structure · configuration management · logging · health
checks · CI/CD foundations · secure dependency management.

### Phase 2 — Identity and Authorization Foundation
Entra integration · token validation · authorization context · policy model ·
Department/Internal/Restricted rules · PostgreSQL RLS · authorization tests.

> **Do not proceed until Phase 2 is validated.** This is the gate everything downstream rests on.
> `pytest tests/authz` moving from `xfail` to green is the objective signal.

### Phase 3 — FileCloud Ingestion
Read-only service account · change detection · content processing · metadata extraction · ACL
extraction · synchronization · reconciliation.

### Phase 4 — Chunking and Metadata
Chunk strategy · enrichment · metadata model · versioning · security metadata.

### Phase 5 — BGE-M3 Embedding Pipeline
Embedding service · versioning · batch processing · failure handling · re-indexing strategy.

### Phase 6 — PostgreSQL + pgvector
Schema · indexes · RLS · retrieval predicates · performance testing · backup/recovery.

### Phase 7 — Retrieval
Query processing · ACL-aware retrieval · hybrid search where justified · reranking · context
construction · evaluation.

### Phase 8 — MCP Server
Tool definitions · MCP security · API integration · authorization propagation · testing.

### Phase 9 — MCP Shim / Claude Desktop Integration
Client configuration · secure authentication flow · connection management · error handling ·
packaging/deployment.

> Highest-risk phase. The authentication design it depends on is unresolved — see
> `../adr/0003-authentication-flows.md`. Resolve that ADR early rather than at Phase 9.

### Phase 10 — Security Validation
Threat model · penetration/security tests · authorization bypass tests · prompt injection tests ·
MCP abuse tests · permission drift tests.

### Phase 11 — Observability and Operations
Metrics · logs · traces · dashboards · alerts · audit.

### Phase 12 — Production Hardening
HA · backup/DR · capacity testing · failure testing · operational runbooks · security acceptance ·
production readiness review.
