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
    pattern: (?:request|body|payload|params|data|args|claims_in)\s*(?:\.get\(|\[)\s*["'](?:principal_id|filecloud_principal_id|principal|exception_id|exception_scope|exception_effect|grants?|allowed_groups|allowed_users|roles|permissions)["']
---

**Blocked — authorization value read from the client.**

You are reading an authorization field off a request. The client controls that value, so honoring
it lets any caller elevate their own access by editing a JSON body.

**Never trust client-supplied:**
`principal_id` · `filecloud_principal_id` · `principal` · `grant` / `grants` · `exception_id` ·
`exception_scope` · `exception_effect` · `allowed_groups` · `allowed_users` · `roles` ·
`permissions`

**Instead:** resolve the principal server-side from the validated token's `oid`, through
`principal_map`, and let the ACL projection and RLS decide what that principal may read. See
`src/derayah_rag/authz/`.

`exception_*` is on this list for a specific reason: a client that could name an exception could
name a `scope = 'all'` one, and `rag_exception` write access is equivalent to read access to the
entire corpus. Exceptions come from the governed store, never from a request.

**`department`, `sub_department`, and `security_tier` are no longer on this list.** Under
`docs/adr/0012-filecloud-acl-authoritative.md` they are metadata, and a client may legitimately send
them as *narrowing* business filters. A metadata filter may only reduce the authorized result set —
if applying one can add a row, it is being used as authorization and that is the bug.

See `docs/architecture/07-api.md` and `docs/architecture/02-authorization-model.md`.
Test: `tests/authz/test_parameter_manipulation.py`

*(CLAUDE.md rule 3)*
