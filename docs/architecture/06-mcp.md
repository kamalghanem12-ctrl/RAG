# MCP Server and Shim

> Source: original specification §9, §10, §20. Content moved unchanged.

## MCP Shim

The client-side protocol integration between Claude Desktop and the centralized MCP Server.

Responsibilities: connect to the MCP Server · participate in the approved authentication flow ·
forward user requests · pass approved identity/access context · handle connection lifecycle.

**The shim stays lightweight and does not contain the authoritative authorization model.** It holds
no long-lived privileged credentials — see `02a-authentication-flows.md` for the token acquisition
design and `08-operations.md` for the secrets rule.

It is the only component that ships to Windows desktops while dev is Ubuntu and production is
RHEL. Packaging, signing, and distribution need their own design.

## MCP Server

The controlled AI tool interface.

Responsibilities: expose approved RAG capabilities · validate requests · validate authentication
context · call the API layer · return authorized results · enforce tool constraints.

**The MCP Server never bypasses the API authorization layer.** It is a tool surface, not a
shortcut to the database.

### Expose

```text
search_knowledge
retrieve_document_context
get_source_reference
```

### Never expose

```text
execute_sql
read_any_file
run_shell_command
call_any_url
```

Capabilities, never primitives. A tool that accepts arbitrary SQL, arbitrary paths, arbitrary
commands, or arbitrary URLs hands the authorization decision to whatever produced the argument —
which is the LLM. Defining any of these is a blocked pattern.

## FileCloud MCP vs. Enterprise RAG MCP

Two different capabilities. They must not share or bypass one another's authorization boundaries.

> Full design for the FileCloud side: `09-filecloud-mcp.md`. Decision and rationale:
> `../adr/0011-filecloud-mcp-scope.md`. The summary below is the contrast; that file is the detail.

| | FileCloud MCP | Enterprise RAG MCP |
|---|---|---|
| Purpose | Live repository operations | Semantic enterprise search |
| Operations | Browse, exact filename search, retrieve an exact document, access current versions, open/download source artifacts | Permission-aware retrieval, RAG orchestration, reranking, knowledge retrieval |
| Backing store | FileCloud, live | The RAG index |
| Authorization | Operates against the user's authorized FileCloud access path | The retrieval predicate in `02-authorization-model.md` |

The RAG MCP queries the index and does not require a live FileCloud request per semantic query.
That decoupling is what makes it fast — and also what makes synchronization state and drift
detection load-bearing rather than housekeeping.
