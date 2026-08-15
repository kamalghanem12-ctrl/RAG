---
name: warn-config-file-write
enabled: true
event: file
action: warn
conditions:
  - field: file_path
    operator: regex_match
    pattern: (?:postgresql\.conf|pg_hba\.conf|Dockerfile|docker-compose\.ya?ml|alembic\.ini|\.conf$|(?:^|[/\\])deploy[/\\]|(?:^|[/\\])config[/\\])
---

**Rule R1 — you are writing a configuration file.**

This is the moment a setting actually takes effect, so it is the moment the baseline must exist.

**Before saving:**

- Is there a `docs/baselines/<object>.md` covering this component and version?
- Is the setting you are about to write consistent with it?
- If it deviates, is the deviation recorded — with justification, risk accepted, and a **named
  Derayah approver**?

`pg_hba.conf` and `postgresql.conf` deserve particular care: authentication method, SSL enforcement,
role privileges, and connection-pool behavior are all security-relevant here, and
`docs/adr/0004-rls-and-pooling.md` depends on getting the role separation right — the application
role must not own the tables, or RLS is silently inert.

**Documentation recalled from memory is not a valid source.** Consult the vendor documentation for
the pinned version, the hardening guide, the CIS Benchmark, and Derayah's own standards — which win
wherever they are stricter.

Template: `docs/baselines/_TEMPLATE.md` · Skill: `configure-baseline`

*(CLAUDE.md rule 10)*
