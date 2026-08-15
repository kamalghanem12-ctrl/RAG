# Configuration Baseline — FileCloud

> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.
>
> Scope: the **FileCloud platform, its user REST API, and the FileCloud Desktop/Sync client**, as
> consumed by the FileCloud MCP (`../architecture/09-filecloud-mcp.md`, `../adr/0011-filecloud-mcp-scope.md`).
>
> The RAG ingestion account is a **separate object** and needs its own baseline at
> `filecloud-service-account.md` before Phase 3. Nothing here covers it.

## Status

**PROVISIONAL — the deployed version is unknown.**

Vendor documentation was reachable and was consulted, but only at the `latest` channel. Rule R1
requires guidance *for that object at that version*. Every version-sensitive claim below is
therefore unconfirmed against what Derayah actually runs, and is marked accordingly.

This baseline must be re-done against the pinned version before the FileCloud MCP reaches any
environment beyond local development.

## Object

| Field | Value |
|---|---|
| Component | FileCloud (Server or Online — not yet established which) |
| Version pinned | **UNKNOWN — open finding #1.** Documentation consulted at `latest` |
| Where deployed | Not established. Client component: FileCloud Desktop / Sync on Windows workstations |
| Owner | **UNNAMED — open finding #2.** Needs a Derayah FileCloud administrator |
| Baseline date | 2026-08-14 |

## Sources consulted

Most authoritative last. Documentation recalled from memory is not a valid source.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | FileCloud Developer Guide — API authentication | https://docs.filecloud.com/fcdoc/latest/server/filecloud-developer-guide/filecloud-api-authentication-exercise | `latest` — **not** the deployed version | 2026-08-14 |
| 2 | FileCloud Developer Guide (index) | https://docs.filecloud.com/fcdoc/latest/server/filecloud-developer-guide | `latest` | 2026-08-14 |
| 3 | FileCloud Administrator Guide — SAML SSO support | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/user-authentication-settings/single-sign-on-sso/saml-single-sign-on-support | `latest` | 2026-08-14 |
| 4 | FileCloud Sync — change sync folder location | https://www.filecloud.com/supportdocs/fcdoc/latest/server/filecloud-client-applications-and-add-ins/filecloud-sync/sync-troubleshooting-guide/change-sync-folder-location | `latest` | 2026-08-14 |
| 5 | FileCloud Desktop for Windows — offline files | https://docs.filecloud.com/fcdoc/latest/server/filecloud-client-applications-and-add-ins/filecloud-desktop-for-windows/make-files-and-folders-available-offline-in-filecloud-desktop-for-windows | `latest` | 2026-08-14 |
| 6 | Vendor security / hardening guide | **NOT RETRIEVED** — not located as a separately published document | — | — |
| 7 | CIS Benchmark | **NOT APPLICABLE** — no CIS Benchmark published for FileCloud | — | — |
| 8 | Derayah internal standard | **NOT RETRIEVED** — no internal FileCloud standard supplied | — | — |

> Derayah internal standards override all external guidance wherever they are stricter. None was
> available at the time of writing; if one exists, this baseline is incomplete until it is applied.

## Findings that drive the design

These are the retrieved facts the MCP design depends on. Recorded here so a version bump forces
them to be re-checked rather than silently inherited.

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| F1 | User API authentication is `loginguest` with `userid` + `password`, returning a session cookie the client replays | 1, 2 | Rules out an API-backed MCP as documented — a user password in MCP client configuration is forbidden by `../architecture/01-trust-boundaries.md` |
| F2 | No token, OIDC, or API-key path for user-delegated API access is documented | 1 | Stage 2 of ADR-0011 is gated pending a vendor answer |
| F3 | SAML 2.0 SSO with Entra ID is supported, FileCloud acting as Service Provider | 3 | Browser redirect flow for the web portal; **not** established as a non-browser API auth mechanism |
| F4 | Sync stores content locally; default `C:\Users\<user>\Documents\FileCloud`, configurable via `syncfolderlocation` in `syncclientconfig.xml` | 4 | The MCP reads the root from config, never hard-codes it |
| F5 | Desktop supports per-item "always keep on this device" offline pinning | 5 | Only synced/pinned content is visible to Stage 1 |
| F6 | Server-side content search covers txt, pdf, doc, docx, xls, xlsx, ppt, pptx; OCR from v20.3. Metadata search from 18.1+. Both administrator-enabled | 2 | Unavailable to Stage 1; a Stage 2 benefit only |
| F7 | No official FileCloud MCP server exists | 2 | This is a build, not an integration |

**Every row above is `latest`-channel and unconfirmed against the deployed version.**

## Settings applied

None. No FileCloud component has been installed, configured, or connected — this baseline precedes
the work rather than recording it, which is the order rule R1 requires.

| Setting | Value | Rationale | Source # |
|---|---|---|---|
| *(none yet)* | | | |

Settings expected to land here when the MCP track starts, each needing its own verification:

- Content search enabled / disabled at the deployed instance (F6 depends on an admin setting)
- Metadata search enabled / disabled
- Whether SAML SSO is actually in use for Derayah's FileCloud, or local/AD authentication
- Sync client deployment posture: which users have it, selective-sync scope, offline-pinning policy

## Deviations from baseline

Every row needs a real, named approver. A blank approver is an open finding, and an open finding is
honest.

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| D1 | Baseline written against `latest` documentation rather than the deployed version | Deployed version not supplied at time of writing | Version-specific behavior may differ from every finding above | *(blank — not approved)* | — |

**Open findings: 3** — must be zero before production.

1. Version not pinned; all findings unconfirmed against the deployed release.
2. No named Derayah owner for this configuration.
3. Deviation D1 has no approver.

## Re-review trigger

- [x] **Deployed version established** — mandatory first re-review; the current document is
      provisional until then
- [ ] Component version bump (server or Desktop/Sync client)
- [ ] Vendor hardening guide published or located
- [ ] Derayah internal FileCloud standard issued or revised
- [ ] Vendor answers the Stage 2 authentication question in ADR-0011
- [ ] Fixed interval: annually

## Verification

Nothing to verify on a running system yet — no setting has been applied. When the track starts, this
section records the command and its output, not the intent.

```
# Pending. Expected first checks:
#   - deployed FileCloud server version (admin portal → About / version endpoint)
#   - FileCloud Desktop/Sync client version on a representative workstation
#   - resolved value of syncfolderlocation in syncclientconfig.xml
#   - whether content search and metadata search are enabled for the tenant
```

A baseline that records intent but not verification is a plan. This one is currently a plan, and
says so.
