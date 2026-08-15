---
name: block-hardcoded-secrets
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.(?:py|sql|ya?ml|toml|ini|conf|json|env|sh|ps1)$
  - field: new_text
    operator: regex_match
    pattern: (?i)(?:password|passwd|pwd|api_key|apikey|client_secret|secret_key|access_token)\s*[:=]\s*["'][^"'\s{$][^"']{5,}["']|(?:postgresql|postgres|mysql|mongodb)(?:\+\w+)?://[^:/\s${]+:[^@\s${]+@
---

**Blocked — credential literal in source.**

An inline password, API key, client secret, or a connection string with embedded credentials.

**Delinea PAM is the source of truth for production secrets.** A credential in source is a
credential in git history, in every clone, in every CI log that echoes config, and in every backup
of the repository — and rotating it means rewriting history rather than rotating a secret.

**Instead:**

```python
# from PAM at runtime
password = pam.get_secret("rag/db/app_user")

# or from environment for local dev only
password = os.environ["DB_PASSWORD"]

# templated DSN — placeholders are fine
dsn = "postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@${DB_HOST}/rag"
```

Also forbidden: long-lived privileged credentials in the MCP shim, and database credentials in a
user's Claude configuration.

If this fired on a placeholder or a test fixture, use an obvious sentinel (`"<from-pam>"`,
`${VAR}`) rather than something that looks like a real secret — the pattern deliberately allows
`$` and `{`.

See `docs/architecture/08-operations.md`.

*(CLAUDE.md rule 8)*
