---
name: configure-baseline
description: Produce a configuration baseline before installing, configuring, or integrating any component (rule R1). Use when installing a package or service, writing a config file (postgresql.conf, pg_hba.conf, Dockerfile, docker-compose.yml), provisioning infrastructure, integrating a third party (Entra, FileCloud, Delinea), or bumping the version of anything already configured. Also use when asked to "check best practice", "harden", or "review the configuration" of a component.
---

# Configuration Baseline Verification (Rule R1)

No component is installed, configured, or integrated until current authoritative guidance for
**that object at that version** has been consulted and the outcome recorded.

Insecure defaults are how systems actually get compromised — rarely through exotic bugs, usually
through a component installed and left as it shipped. This procedure exists because that step is
the one that gets skipped under delivery pressure.

## Procedure

### 1. Identify the object precisely

Component **and exact version**. `PostgreSQL 16.4`, not `Postgres`. `postgres:16.4-alpine`, not
`latest`. A baseline against an unpinned version is not a baseline — the thing it describes can
change underneath it.

Check whether `docs/baselines/<object>.md` already exists:

- Exists, version matches → nothing to do; confirm settings still hold and stop.
- Exists, version differs → a version bump is a re-review trigger. Update, do not replace blindly:
  diff what the new version changed.
- Does not exist → continue.

### 2. Consult the source hierarchy

In order, **most authoritative last**:

| # | Source | Notes |
|---|---|---|
| 1 | Vendor official documentation | For the exact pinned version, not the latest docs |
| 2 | Vendor security / hardening guide | Where published separately |
| 3 | CIS Benchmark | PostgreSQL, RHEL, Docker, Kubernetes all have one. Expected reference for a regulated financial institution |
| 4 | **Derayah internal standards** | **Override all of the above wherever stricter** |

**Documentation recalled from memory is not a valid source.** Retrieve it. If retrieval is not
possible — no network access, no internal mirror — do not write the baseline from memory. Record
the gap explicitly:

```
NOT VERIFIED — no documentation access at time of configuration.
This baseline is provisional and must be revisited before the component
reaches any environment beyond local development.
```

An honest gap is useful. A confident-sounding baseline written from memory is worse than none,
because it will be trusted at review time.

### 3. Draft the baseline

Copy `docs/baselines/_TEMPLATE.md` to `docs/baselines/<object>.md` and fill every section:

- **Object** — component, pinned version, deployment target, owner, date
- **Sources consulted** — with URL and retrieval date for each
- **Settings applied** — each with a rationale and the source number it came from
- **Deviations** — see below
- **Re-review trigger** — version bump, benchmark revision, standard revision, or interval
- **Verification** — the command or query that confirms the setting on the running system, and its
  output

A baseline that records intent but not verification is a plan.

### 4. Record deviations honestly

Every deviation from the consulted guidance needs: what deviates, why, the risk accepted, and a
**named Derayah approver** with their role and the date.

**Leave the approver blank when approval has not actually been given.** A blank approver is an
open finding — that is the correct and useful state. Never infer an approver from context, never
predict who would approve, never write a name because a name is expected there. Fabricating an
approval is worse than the deviation it papers over.

Count open findings at the bottom of the file. That count must be zero before production.

### 5. Report

State plainly: which sources were reachable, which were not, what deviates, and how many findings
are open. If the baseline is provisional, say so in the summary — not only in the file.

## Objects in scope for this platform

`postgresql` · `pgvector` · `rhel` · `container-runtime` · `fastapi-uvicorn` · `bge-m3-serving` ·
`mcp-server` · `mcp-shim` · `entra-app-registration` · `filecloud-service-account` ·
`delinea-integration` · `api-gateway-tls`

## Security-relevant settings worth particular attention

- **PostgreSQL** — `ssl`, `password_encryption`, `pg_hba.conf` auth methods, role privileges, and
  the ownership separation that `docs/adr/0004-rls-and-pooling.md` depends on. If the application
  role owns its tables, RLS is silently inert.
- **pgvector** — index parameters interact with recall under selective ACL filters. See
  `docs/adr/0005-ann-recall-under-acl.md`.
- **Container runtime** — non-root user, read-only root filesystem, dropped capabilities, no
  secrets in image layers or build args.
- **Entra app registration** — redirect URIs, exposed API scope and audience, app roles, token
  lifetimes, and consent. See `docs/adr/0009-entitlement-claims.md`.
- **FileCloud service account** — read-only, scoped to the approved knowledge-base tree only.

## Related

`/CLAUDE.md` rule 10 · `docs/baselines/_TEMPLATE.md` ·
`.claude/hookify.configuration-baseline.local.md` · `.claude/hookify.config-file-write.local.md`
