---
name: block-client-supplied-authz
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: (?:request|body|payload|params|data|args|claims_in)\s*(?:\.get\(|\[)\s*["'](?:department|sub_department|security_tier|allowed_groups|allowed_users|roles|permissions)["']
---

**Blocked — authorization value read from the client.**

You are reading an authorization field off a request. The client controls that value, so honoring
it lets any caller elevate their own access by editing a JSON body.

**Never trust client-supplied:**
`department` · `sub_department` · `security_tier` · `allowed_groups` · `allowed_users` · `roles` ·
`permissions`

**Instead:** derive them server-side from the validated token, via the authorization context in
`src/derayah_rag/authz/`. The client may send a search query and legitimate business filters —
never an authorization value. Supplied authorization parameters are ignored or rejected, never
honored.

See `docs/architecture/07-api.md` and `docs/architecture/02-authorization-model.md`.
Test: `tests/authz/test_parameter_manipulation.py`

*(CLAUDE.md rule 3)*
