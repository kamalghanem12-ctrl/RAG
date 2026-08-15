---
name: block-unvalidated-token-claims
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: \.py$
  - field: new_text
    operator: regex_match
    pattern: verify(?:_signature|_aud|_exp|_iss|_nbf|_at_hash)?["']?\s*[:=]\s*(?:False|false)
---

**Blocked — token verification disabled.**

A token decoded without full verification is an attacker-supplied JSON document. Every claim in it
— `oid`, `groups`, `roles` — becomes whatever the caller typed.

**Required on every request, no exceptions and no debug bypass:**

| Check | Stops |
|---|---|
| Signature | Forged tokens |
| `iss` | Tokens from another issuer |
| `tid` | Tokens from another tenant |
| **`aud`** | **A token legitimately minted for a different resource, replayed here** |
| `exp` / `nbf` | Expired or premature tokens |

The `aud` check is the one most often skipped and the one that matters most: without it the API
accepts any valid token from the tenant, including one issued to an unrelated application.

If you are disabling verification to make a test pass, use a locally-signed fixture token instead —
the test suite needs the real validation path exercised.

See `docs/architecture/02a-authentication-flows.md`.
Test: `tests/authz/test_token_validation.py`

*(CLAUDE.md rule 7)*
