---
name: block-dangerous-mcp-tools
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: \b(?:execute_sql|run_shell_command|read_any_file|call_any_url|exec_sql|run_command)\b
---

**Blocked — MCP primitive rather than a capability.**

You are defining a tool that accepts arbitrary SQL, an arbitrary path, an arbitrary command, or an
arbitrary URL.

**Why this is fatal here:** such a tool hands the authorization decision to whatever produced the
argument — which is the LLM. The entire architecture rests on the model never being the thing that
decides what may be read. One generic tool undoes it.

**Never expose:** `execute_sql` · `read_any_file` · `run_shell_command` · `call_any_url`

**Expose instead:**

```text
search_knowledge
retrieve_document_context
get_source_reference
```

Capabilities, never primitives. Each carries its own validation and routes through the API
authorization layer — the MCP server never bypasses it.

See `docs/architecture/06-mcp.md`.

*(CLAUDE.md rule 6)*
