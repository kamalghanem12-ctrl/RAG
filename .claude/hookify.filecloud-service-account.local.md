---
name: block-filecloud-mcp-service-account
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (?:^|[/\\])(?:src|filecloudmcp)[/\\].*\.py$
  - field: new_text
    operator: regex_match
    pattern: (?i)\b(?:adminlogin|admin_login|(?:filecloud|ingestion)_service_account|service_account_(?:login|password|token|credential))\b
---

**Blocked — the FileCloud MCP is acquiring an identity that is not the user's.**

You are referencing a service account, a shared credential, or a FileCloud administrator endpoint
in code that reaches FileCloud.

**Why this is fatal here:** the FileCloud MCP implements no authorization of its own. It *inherits*
FileCloud's, and that inheritance is sound for exactly one reason — it acts as the signed-in user,
so FileCloud makes the same decision it would make if that user opened the file in Explorer.

Swap in a service account and the inheritance inverts. The RAG ingestion account is **read-only
across the entire document estate**. An MCP holding it would let every user read every document
through Claude: a total authorization bypass, arriving as a convenience feature and looking like
one in review. It is the single most dangerous reachable state in this capability.

`adminlogin` is worse still — administrator endpoints are permanently out of scope.

**Instead:**

- **Stage 1 (desktop-backed):** hold no credentials at all. Read the local FileCloud Sync/Desktop
  content, which the client already authenticated this user to hold. Resolve the root from
  `syncfolderlocation` in `syncclientconfig.xml`; never hard-code it.
- **Stage 2 (API-backed):** blocked pending a supported password-free user-delegated
  authentication path from FileCloud. A user password in MCP client configuration is forbidden by
  `docs/architecture/01-trust-boundaries.md`.

The two MCPs share no credential, session, or process identity. A RAG denial is not a FileCloud
denial, and a FileCloud grant is never evidence of RAG entitlement.

See `docs/adr/0011-filecloud-mcp-scope.md` and `docs/architecture/09-filecloud-mcp.md`.
Asserted by `tests/authz/test_filecloud_mcp_isolation.py`.
