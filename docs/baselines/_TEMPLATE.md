# Configuration Baseline — <object>

> Copy this file to `docs/baselines/<object>.md` when configuring a new component.
> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.

## Object

| Field | Value |
|---|---|
| Component | *e.g. PostgreSQL* |
| Version pinned | *exact version — `16.4`, not `16` or `latest`* |
| Where deployed | *e.g. RHEL 9, container image `postgres:16.4`* |
| Owner | *team or individual accountable for this configuration* |
| Baseline date | *YYYY-MM-DD* |

## Sources consulted

Most authoritative last. **Documentation recalled from memory is not a valid source** — if a source
could not be retrieved, say so here rather than citing it.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | Vendor official documentation | | | |
| 2 | Vendor security / hardening guide | | | |
| 3 | CIS Benchmark | | | |
| 4 | Derayah internal standard | | | |

> Derayah internal standards override all external guidance wherever they are stricter.

If no source could be consulted, state that plainly:

```
NOT VERIFIED — no documentation access at time of configuration.
This baseline is provisional and must be revisited before the component
reaches any environment beyond local development.
```

## Settings applied

| Setting | Value | Rationale | Source # |
|---|---|---|---|
| | | | |

## Deviations from baseline

Every row needs a real, named approver. **Leave the approver blank if approval has not actually
been given** — a blank approver is an open finding, and an open finding is honest. Never infer,
assume, or predict an approval.

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| | | | | | |

**Open findings:** *count of deviations with no approver — must be zero before production*

## Re-review trigger

- [ ] Component version bump
- [ ] Benchmark or hardening guide revision
- [ ] Derayah standard revision
- [ ] Fixed interval: *e.g. annually*

## Verification

How the applied settings were confirmed on the running system — the command or query, and its
output. A baseline that records intent but not verification is a plan, not a baseline.

```
# e.g. SHOW ssl; SHOW password_encryption;
```
