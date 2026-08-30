# Configuration Baseline — FileCloud

> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.
>
> Scope: the **FileCloud platform, its user REST API, and the FileCloud Desktop/Sync client**, as
> consumed by the FileCloud MCP (`../architecture/09-filecloud-mcp.md`, `../adr/0011-filecloud-mcp-scope.md`)
> and — newly, as of this revision — as the **authoritative source of document authorization** under
> `../adr/0012-filecloud-acl-authoritative.md`.
>
> The RAG ingestion account is a **separate object** and needs its own baseline at
> `filecloud-service-account.md` before Phase 3. Nothing here covers it.

## Status

**PROVISIONAL — documentary verification complete, empirical verification pending.**

Revision 2 (2026-08-21) pins the deployed version, which was open finding #1 in revision 1. That
changes the confidence of every finding below and closes deviation D1.

What is now established: the deployed build, and the fact that FileCloud publishes **no
version-specific documentation channel**. What remains open: everything that can only be confirmed
against the running instance. A read-only admin account and API access have been offered but not
yet provisioned, so no claim below has been checked against Derayah's actual configuration.

This baseline must not be treated as verified until the "Verification" section holds real output.

## Object

| Field | Value |
|---|---|
| Component | FileCloud **Server** (self-hosted; not FileCloud Online) |
| Version pinned | **23.261.2.33071** — supplied by the project owner 2026-08-21 |
| Version currency | `latest` documentation channel corresponds to **23.262**. Deployed build is **one minor train behind current** |
| Where deployed | Derayah-hosted. Access paths in use: **web portal (GUI)** and **FileCloud Desktop** |
| Storage backends in use | **NOT ESTABLISHED — open finding #1.** Managed Storage vs. Network (LAN/NTFS) folders decides which authorization model applies. See F8 |
| Owner | **UNNAMED — open finding #2.** Needs a named Derayah FileCloud administrator. The version and access offer came from the project owner, which is not the same as a recorded configuration owner |
| Baseline date | Revision 1: 2026-08-14. **Revision 2: 2026-08-21** |

## Sources consulted

Most authoritative last. Documentation recalled from memory is not a valid source.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | FileCloud Developer Guide — API authentication | https://docs.filecloud.com/fcdoc/latest/server/filecloud-developer-guide/filecloud-api-authentication-exercise | `latest` (= 23.262) | 2026-08-14 |
| 2 | FileCloud Developer Guide (index) | https://docs.filecloud.com/fcdoc/latest/server/filecloud-developer-guide | `latest` | 2026-08-14 |
| 3 | FileCloud Administrator Guide — SAML SSO support | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/user-authentication-settings/single-sign-on-sso/saml-single-sign-on-support | `latest` | 2026-08-14 |
| 4 | FileCloud Sync — change sync folder location | https://www.filecloud.com/supportdocs/fcdoc/latest/server/filecloud-client-applications-and-add-ins/filecloud-sync/sync-troubleshooting-guide/change-sync-folder-location | `latest` | 2026-08-14 |
| 5 | FileCloud Desktop for Windows — offline files | https://docs.filecloud.com/fcdoc/latest/server/filecloud-client-applications-and-add-ins/filecloud-desktop-for-windows/make-files-and-folders-available-offline-in-filecloud-desktop-for-windows | `latest` | 2026-08-14 |
| 6 | **FileCloud Security Checklist** — vendor hardening guide | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-security-checklist | `latest` | **2026-08-21** |
| 7 | CIS Benchmark | **NOT APPLICABLE** — no CIS Benchmark published for FileCloud | — | — |
| 8 | Derayah internal standard | **NOT RETRIEVED** — no internal FileCloud standard supplied | — | — |
| 9 | Server release notes index | https://docs.filecloud.com/fcdoc/latest/server/release-notes/server-release-notes | `latest` | 2026-08-21 |
| 10 | Minor release 23.261.1 notes | https://docs.filecloud.com/fcdoc/latest/server/release-notes/server-release-notes/filecloud-version-23-261-release-notes/minor-filecloud-release-23-261-1 | 23.261.1.32981 | 2026-08-21 |
| 11 | Folder-Level Permissions (index) | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/folder-level-permissions | `latest` | 2026-08-21 |
| 12 | How Folder-Level and Share Permissions Work Together | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/folder-level-permissions/how-folder-level-permissions-and-share-permissions-work-together | `latest` | 2026-08-21 |
| 13 | Setting Folder-Level Permissions from the Admin Portal | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/folder-level-permissions/setting-folder-level-permissions-from-the-admin-portal | `latest` | 2026-08-21 |
| 14 | Guide to FileCloud Network Folders with NTFS Permissions | https://docs.filecloud.com/fcdoc/latest/server/filecloud-administrator-guide/filecloud-site-setup/storage-settings/setting-up-network-folders/lan-based-network-folders/network-folders-with-ntfs-permissions/guide-to-filecloud-network-folders-with-ntfs-permissions | `latest` | 2026-08-21 |

> Derayah internal standards override all external guidance wherever they are stricter. None was
> available at the time of writing; if one exists, this baseline is incomplete until it is applied.

### Note on the documentation channel

FileCloud serves **only** a `latest` documentation channel at `/fcdoc/latest/`. There is no version
selector and no per-release documentation set. Rule R1's requirement to consult guidance *for that
object at that version* therefore **cannot be satisfied from vendor documentation alone** for any
pinned FileCloud version — a structural limitation of the vendor, not of this baseline.

The mitigation adopted here: `latest` docs (= 23.262) + the release-notes diff to the deployed train
+ **empirical confirmation against the deployed instance**, which becomes the authority wherever
documentation cannot be version-pinned. This is why instance access is a baseline requirement and
not a convenience.

## Findings that drive the design

Recorded so a version bump forces a re-check rather than silent inheritance.

### Authentication and client (revision 1, re-confirmed at 23.261)

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| F1 | User API authentication is `loginguest` with `userid` + `password`, returning a session cookie the client replays | 1, 2 | Rules out an API-backed MCP as documented — a user password in MCP client configuration is forbidden by `../architecture/01-trust-boundaries.md` |
| F2 | No token, OIDC, or API-key path for user-delegated API access is documented | 1 | Stage 2 of ADR-0011 is gated pending a vendor answer |
| F3 | SAML 2.0 SSO with Entra ID is supported, FileCloud acting as Service Provider | 3 | Browser redirect flow for the web portal; **not** established as a non-browser API auth mechanism |
| F4 | Sync stores content locally; default `C:\Users\<user>\Documents\FileCloud`, configurable via `syncfolderlocation` in `syncclientconfig.xml` | 4 | The MCP reads the root from config, never hard-codes it |
| F5 | Desktop supports per-item "always keep on this device" offline pinning | 5 | Only synced/pinned content is visible to Stage 1 |
| F6 | Server-side content search covers txt, pdf, doc, docx, xls, xlsx, ppt, pptx; OCR from v20.3. Metadata search from 18.1+. Both administrator-enabled | 2 | Both version floors are **below 23.261**, so both are available at the deployed version — subject to the admin setting being on |
| F7 | No official FileCloud MCP server exists | 2 | This is a build, not an integration |

### Authorization model (revision 2 — new, for ADR-0012 and ADR-0013)

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| **F8** | **FileCloud has two distinct authorization models depending on storage backend.** Folder-Level Permissions (FLP) apply to **Managed Storage only — "not Network Storage"**. Network (LAN) folders are authorized by **NTFS ACLs from Active Directory** instead | 11, 14 | **ADR-0012 currently speaks of "FileCloud ACLs" as one model. It is two.** The ACL projection must record which model governs each document, and the retrieval predicate must be correct under both. This is the single largest finding in this revision |
| F9 | FLP permission types are exactly five: **Read** (download, preview), **Write** (upload, modify, create, rename), **Delete**, **Share**, **Manage** (manage FLP for the folder) | 13 | The projection needs only `Read` for retrieval authorization, but must not confuse "has any permission" with "has Read" |
| F10 | FLP principals are **individual users (by email)** and **groups** (separate Group tab). No `EVERYONE` catch-all is documented | 13 | Principal mapping in ADR-0013 must handle both, keyed on email for users |
| F11 | **FLP has no explicit DENY.** It is an enable/disable model — "check or uncheck levels of permissions" | 12, 13 | A projection modelling FLP does not need deny-precedence logic. **But NTFS does have explicit deny**, so deny semantics differ by storage backend (see F8) |
| F12 | **FLP default is allow:** "Users who do not appear on the list have all folder-level permissions" | 13 | **Critical.** FLP is a *restriction* layered on sharing, not a *grant* mechanism. A projection that treats "no FLP entry" as "no access" would be wrong; one that treats it as "full access" is correct for FLP but only safe if share-level scope is also projected (F14) |
| F13 | **Precedence: user overrides group.** "User permissions override permissions of a group the user is in." Across multiple groups, permissions are the **union**: "the effective permissions are the enabled permissions from all their groups combined" | 12 | Composition is union-across-groups, then user-level override. Not most-restrictive-wins. Any SQL projection must reproduce this exactly or it is not a faithful cache |
| F14 | **FLP composes with share permissions by intersection:** "Whichever is more restrictive, share permissions or folder-level permissions, apply" | 12 | Effective read access = (share perms) AND (FLP). Projecting FLP alone is insufficient — share scope is part of the authorization decision |
| F15 | **Inheritance is on by default**, subfolders inherit from their **immediate parent**. Disabling is per-folder via an `Inherit` / `Don't Inherit` radio, and "if you manually turn off inheritance for a folder, its subfolders still have inheritance turned on" | 12, 13 | Inheritance is not a simple tree walk — a `Don't Inherit` folder is a break point whose own children still inherit *from it*. The projection must materialise effective permissions per path, not store a rule and evaluate it later |
| F16 | For NTFS network folders, AD group membership changes are **not propagated immediately**: "it might take some time ranging (10 minutes to several hours) before the change is picked up by NTFS." Restarting the Helper service forces pickup | 14 | **Staleness compounds.** ADR-0012 says FileCloud is right and our projection is stale. For network folders the chain is AD to NTFS to FileCloud cache to our projection, so *FileCloud itself* can be hours stale relative to AD. The ADR's staleness bound must account for this, and revocation latency is not something our sync interval alone can fix |
| F17 | Permission caching for network folders is available via memcache, and **Access Based Enumeration (ABE)** can "automatically hide folders that users don't have access to" | 14 | ABE aligns with the not-found semantics under consideration in `../adr/0006-deny-vs-notfound.md`, and is prior art for that choice at the source system |
| F18 | Release 23.261 introduced the **Network Share Scanner** for advanced features on network folders, alongside additional MFA modes and document watermarking | 9 | Relevant to ingestion if network folders are in scope (F8). Watermarking may affect extracted text fidelity — worth checking during ingestion design |

**Confidence note.** F8–F18 are documentary, from the `latest` channel (= 23.262) against a deployed
23.261. Two specific items are weaker and are called out rather than presented as settled:

- A search result attributed to FileCloud documentation states NTFS group evaluation reads the
  `tokenGroupsGlobalAndUniversal` attribute, which would imply **transitive/nested** group
  resolution. A direct fetch of source 14 **did not confirm this**. Treated as unconfirmed; it is
  the crux of ADR-0013's remaining marker and must be settled on the instance or with FileCloud
  support.
- Search results referenced an "effective permissions calculator" in the admin portal. A direct
  fetch of source 12 **did not confirm** such a tool. If it exists it is significant — it would
  mean FileCloud can hand us computed effective permissions rather than raw entries we must compose
  ourselves through F13–F15. Must be confirmed in the admin portal.

## Settings applied

None. No FileCloud component has been installed, configured, or connected. This baseline still
precedes the work, which is the order rule R1 requires.

| Setting | Value | Rationale | Source # |
|---|---|---|---|
| *(none yet)* | | | |

Settings expected to land here when the track starts, each needing its own verification:

- Which storage backends are in use (F8) — Managed, Network/NTFS, or both
- Content search and metadata search enabled / disabled (F6)
- Whether SAML SSO with Entra is in use, or local/AD authentication (F3)
- Whether folder-level permissions are enabled for users at all (F11–F15 are moot if not)
- ABE enabled / disabled on network folders (F17)
- NTFS permission caching enabled, and its cache lifetime (F16, F17)
- Sync/Desktop deployment posture: which users, selective-sync scope, offline-pinning policy
- Read-only admin and API account scope, once provisioned — recorded in
  `filecloud-service-account.md`, not here

## Deviations from baseline

Every row needs a real, named approver. A blank approver is an open finding, and an open finding is
honest.

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| ~~D1~~ | ~~Baseline written against `latest` documentation rather than the deployed version~~ | **CLOSED 2026-08-21** — version pinned to 23.261.2.33071 | — | — | — |
| D2 | Guidance consulted at the `latest` channel (23.262) for a deployed 23.261 | FileCloud publishes no version-specific documentation channel. There is no compliant alternative | One minor train of undocumented drift. Mitigated by the release-notes diff and pending instance verification | *(blank — not approved)* | — |
| D3 | Authorization design proceeding on documentary findings not yet confirmed against the instance | Instance access offered but not yet provisioned | F8–F18 may differ in Derayah's configuration. ADR-0012 and ADR-0013 depend on them | *(blank — not approved)* | — |

**Open findings: 5** — must be zero before production.

1. Storage backends in use not established — decides whether FLP, NTFS, or both govern (F8).
2. No named Derayah owner for this configuration.
3. Deviation D2 has no approver.
4. Deviation D3 has no approver.
5. Two documentary claims unconfirmed on direct fetch — nested-group resolution via
   `tokenGroupsGlobalAndUniversal`, and the existence of an effective-permissions calculator. Both
   are load-bearing for ADR-0013 and ADR-0012 respectively.

## Re-review trigger

- [x] **Deployed version established** — done 2026-08-21 (23.261.2.33071)
- [ ] **Empirical verification against the instance** — mandatory next re-review; this document
      stays provisional until the Verification section holds real output
- [ ] Component version bump (server or Desktop/Sync client), including 23.261 to 23.262
- [x] Vendor hardening guide published or located — FileCloud Security Checklist, source 6
- [ ] Security Checklist reviewed section-by-section against the deployed configuration
- [ ] Derayah internal FileCloud standard issued or revised
- [ ] Vendor answers the Stage 2 authentication question in ADR-0011 (F2)
- [ ] Fixed interval: annually

## Verification

Nothing has been verified on the running system. No setting has been applied and no credential has
been provisioned, so this section records intent — which means this baseline is still a plan.

Checks to run once the read-only admin account and API access are available:

```
# Version and edition
#   Admin Portal -> Settings -> confirm build string is 23.261.2.33071

# F8 - which authorization model applies
#   Admin Portal -> Storage Settings -> enumerate Managed Storage vs Network Folders
#   For each folder in the intended knowledge-base tree, record which backend it sits on

# F11-F15 - FLP model, on Managed Storage
#   Admin Portal -> Folder Level Permissions -> confirm the five permission types (F9)
#   Confirm no ALLOW/DENY toggle exists, only enable/disable (F11)
#   Confirm "users not on the list have all permissions" default (F12)
#   Construct a user in two groups with differing permissions; confirm union (F13)
#   Construct a user permission conflicting with a group; confirm user wins (F13)
#   Set a folder to Don't Inherit; confirm its children still inherit from it (F15)
#   Locate the effective-permissions calculator, if it exists (open finding #5)

# F8/F16 - NTFS model, on Network Folders
#   Confirm whether nested AD groups resolve transitively (open finding #5)
#   Confirm explicit DENY is honoured and takes precedence
#   Record NTFS permission caching setting and its lifetime
#   Record whether ABE is enabled (F17)

# API surface - for ADR-0012
#   Determine whether the admin API returns EFFECTIVE permissions for a user+path,
#   or only raw ACL entries requiring us to compose F13/F14/F15 ourselves.
#   This single answer decides how much authorization logic the projection must carry.

# Credential handling
#   Confirm the account is read-only, scoped to the approved knowledge-base tree,
#   and that its secret lives in Delinea PAM and nowhere in this repository (rule 8)
```

A baseline that records intent but not verification is a plan. This one is a plan with a pinned
version and a documented model — better than revision 1, still not verified.
