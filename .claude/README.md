# `.claude/` — Enforcement Layer

The rules in `/CLAUDE.md` are advisory: a model can read them and still not follow them. This
directory holds the ones that are actually enforced by the harness.

## Layers

| Tier | Mechanism | Enforces | Model can bypass |
|---|---|---|---|
| 1 | `/CLAUDE.md` prose | Intent, architecture | **Yes** |
| 2 | `settings.json` `permissions.deny` | Tool invocations | No — harness |
| 3 | `hookify.*.local.md` | Patterns in commands and edits | No — harness |
| 4 | `pytest tests/authz` + CI | Committed code | No |

A security rule that lives only in tier 1 is a hope. Every rule in `/CLAUDE.md` marked *blocked*
has a tier-3 counterpart here.

## Why the hookify rules are committed

Hookify's own convention is `.claude/hookify.<name>.local.md`, and `.local.md` is normally
gitignored as personal preference. **These are deliberately committed instead.** They are security
controls, not preferences — if only one engineer's machine has them, they enforce nothing. The
`.gitignore` un-ignores `hookify.*.local.md` specifically for this reason.

`settings.local.json` remains ignored; it is genuinely personal.

## Requirements

Hookify must be installed for tier 3 to do anything:

```
/plugin install hookify@claude-plugins-official
```

Its hooks shell out to `python3`. **Verify that `python3 --version` returns a real version** — on
Windows it often resolves to the Microsoft Store alias stub, in which case the hooks fail and every
rule here is silently inert. A rule that does not fire is not a rule.

Check what is live:

```
/hookify list
```

## The rules

| File | Event | Action | Enforces |
|---|---|---|---|
| `hookify.client-supplied-authz.local.md` | file | **block** | Rule 3 — authz values never come from the client |
| `hookify.post-retrieval-filtering.local.md` | file | **block** | Rule 4 — never retrieve then filter |
| `hookify.session-scoped-db-context.local.md` | file | **block** | Rule 5 — `SET LOCAL` only |
| `hookify.dangerous-mcp-tools.local.md` | file | **block** | Rule 6 — capabilities, not primitives |
| `hookify.unvalidated-token-claims.local.md` | file | **block** | Rule 7 — always verify tokens |
| `hookify.hardcoded-secrets.local.md` | file | **block** | Rule 8 — secrets live in Delinea |
| `hookify.naive-groups-claim.local.md` | file | warn | Groups overage handling |
| `hookify.hardcoded-departments.local.md` | file | warn | No org chart in application logic |
| `hookify.configuration-baseline.local.md` | bash | warn | Rule 10 / R1 — baseline before install |
| `hookify.config-file-write.local.md` | file | warn | Rule 10 / R1 — baseline before configure |
| `hookify.require-authz-tests.local.md` | stop | warn | Phase gate — tests before "done" |
| `hookify.phase-order-gate.local.md` | prompt | warn | Implement only the current phase |

## Maintaining them

Every pattern must be tested against a true positive **and** a false positive before it is enabled.
An over-broad blocking rule is worse than no rule: it trains people to work around the hook, and
then the hook protects nothing.

```bash
python -c "import re; print(re.search(r'PATTERN', 'sample text'))"
```

If a rule fires on legitimate code, fix the pattern. Do not disable the rule and move on.
