# Trust Boundaries

> Source: original specification §4, §5. Content moved unchanged.

Ten separate trust boundaries. **Do not assume that because two components sit inside the same
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

For each boundary, explicitly define and document: **authentication · authorization · encryption ·
input validation · output validation · logging · failure behavior.**

That table is a Phase 0 deliverable and is not yet complete. Producing it is architecture
validation work, not documentation work.

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
