# Configuration Baseline — RHEL

> Required by **rule R1** in `/CLAUDE.md`. Produced by the `configure-baseline` skill.
>
> Scope: the Red Hat Enterprise Linux hosts running the RAG platform. This baseline covers the
> **operating system**; the components installed on it have their own baselines —
> `postgresql.md`, `pgvector.md`, and (when BGE-M3 is stood up) `container-runtime.md`.

## Status

**PROVISIONAL — thin on hardening sources.** The lifecycle position is established and good. The
hardening half is not: neither the CIS Benchmark for RHEL 9 nor the DISA STIG was consulted at
baseline time, and for a regulated financial institution one of those is the expected reference.
This baseline is adequate to justify *starting on the test server* and is **not** adequate for
production.

## Object

| Field | Value |
|---|---|
| Component | Red Hat Enterprise Linux Server |
| Version pinned | **9.8** |
| Lifecycle position | **ELC-eligible.** ELC is available for even-numbered RHEL 9 minor releases (9.2, 9.4, 9.6, **9.8**, 9.10), each carrying 6 years of support from its GA date |
| Hosts | **Two servers — one test, one production.** Test first; production is out of scope until the test baseline is verified |
| Architecture | **NOT ESTABLISHED** — x86_64 assumed, not confirmed |
| Package source | **NOT ESTABLISHED — open finding #1.** Direct Red Hat CDN vs. an internal Satellite/mirror. Decides how packages and patches arrive, and whether the host has egress at all |
| Owner | **UNNAMED — open finding #2** |
| Baseline date | 2026-08-21 |

## Sources consulted

Most authoritative last. Documentation recalled from memory is not a valid source.

| # | Source | URL | Version / edition | Retrieved |
|---|---|---|---|---|
| 1 | Red Hat Enterprise Linux Life Cycle | https://access.redhat.com/support/policy/updates/errata | current | 2026-08-21 |
| 2 | Vendor security / hardening guide (Red Hat security hardening documentation) | **NOT RETRIEVED** — **open finding #3** | — | — |
| 3 | CIS Benchmark for RHEL 9 | **NOT CONSULTED** — **open finding #4.** The expected reference for a regulated financial institution | — | — |
| 4 | DISA STIG for RHEL 9 | **NOT CONSULTED** — an alternative to #3; one of the two should be applied | — | — |
| 5 | Derayah internal RHEL build standard | **NOT RETRIEVED — open finding #5.** Derayah almost certainly has a standard server build. If one exists it **overrides everything above**, and this baseline is incomplete without it | — | — |

> Derayah internal standards override all external guidance wherever they are stricter.

**Be direct about what this means:** three of the five source rows are empty, and two of them are
the ones that matter for hardening. What follows is a lifecycle and platform record, not a hardened
build specification.

## Findings that drive the design

| # | Finding | Source # | Design consequence |
|---|---|---|---|
| R1 | RHEL 9 carries a **10-year life cycle** across Full Support, Maintenance Support, and Extended Life phases | 1 | Long-horizon platform. No forced migration inside this project's delivery window |
| R2 | **ELC replaces the former EUS / Enhanced EUS / E4S offerings** as a single extended-support model, and covers even-numbered minors only | 1 | 9.8 being even is not incidental — it is the reason this version can be pinned and held. Had the servers been built on 9.7, staying put would not have been supportable |
| R3 | ELC gives **6 years of support from the minor release GA date** | 1 | Pinning 9.8 is defensible for the life of this platform, provided ELC is actually subscribed. Entitlement is a procurement fact, not a technical one — confirm it |
| R4 | Specific calendar dates for the 9.x minor releases were **not** in the retrieved content | 1 | The exact ELC end date for 9.8 is unconfirmed. Needed before production sign-off |

### Platform note — Python

`pyproject.toml` requires **Python ≥ 3.11**. RHEL 9 ships an older Python as the system interpreter,
and the system interpreter is used by OS tooling. Two consequences:

- Python 3.11+ must come from an AppStream module or equivalent, installed **alongside** the system
  Python, never replacing it. Replacing or upgrading the system interpreter in place is a known way
  to break `dnf` and leave a host unmanageable.
- The application must run in a virtual environment, which `/CLAUDE.md` already prescribes.

The exact packaged Python version available in RHEL 9.8 AppStream was **not verified** — confirm on
the host before Phase 1.

### Platform note — SELinux

RHEL enforces SELinux by default and it should stay enforcing. Two places it will be felt:

- A native PostgreSQL install expects its data directory to carry the right context. A data
  directory relocated to a non-default path needs its context set, or PostgreSQL will fail to start
  in a way that does not obviously name SELinux as the cause.
- Containers bind-mounting host paths need the `:Z` / `:z` mount option.

`setenforce 0` is not a fix for either, and must not appear in any runbook.

### Platform note — where the repository lives

The working checkout belongs in a normal location such as `~/derayah-rag` or `/srv/derayah-rag`.
**Not `/opt`** — under the FHS `/opt` is for self-contained add-on application packages, not
development checkouts, and it carries its own SELinux labelling that a checkout does not need.

## Settings applied

None. No configuration has been applied to either host — this baseline precedes the work, which is
the order rule R1 requires.

| Setting | Value | Rationale | Source # |
|---|---|---|---|
| *(none yet)* | | | |

Settings expected to land here, each needing verification and a cited source before it counts:

- SELinux mode (expected: `enforcing`)
- `firewalld` state and the open port set
- SSH: root login, password authentication, permitted key types
- Subscription and patch cadence; ELC entitlement confirmed
- Time synchronisation (`chronyd`) — matters for token validation and audit correlation
- Audit daemon configuration and log forwarding
- Filesystem layout and separate mount points for `/var`, `/var/log`, and the database data directory

## Deviations from baseline

| # | Deviation | Justification | Risk accepted | Approver (name, role) | Date |
|---|---|---|---|---|---|
| D1 | No hardening guide, CIS Benchmark, or STIG consulted | Not retrieved at baseline time | The OS build is undocumented against any hardening standard. Unacceptable for production; tolerable for a test host that holds no Derayah data | *(blank — not approved)* | — |
| D2 | No Derayah internal build standard applied | None supplied | If a Derayah standard exists, this baseline conflicts with it by omission and the servers may already be non-compliant | *(blank — not approved)* | — |

**Open findings: 5** — must be zero before production.

1. Package source not established (Red Hat CDN vs. internal Satellite/mirror; egress unknown).
2. No named Derayah owner for these hosts.
3. Vendor hardening guide not retrieved (deviation D1).
4. CIS Benchmark / STIG not consulted (deviation D1).
5. Derayah internal build standard not retrieved (deviation D2).

**Explicit scope limit:** this baseline supports work on the **test** server only. The production
host must not be configured against it.

## Re-review trigger

- [ ] Minor version change (9.8 → 9.9 or later) — note that odd-numbered minors are not ELC-eligible
- [ ] Major version change (RHEL 9 → 10)
- [ ] CIS Benchmark, STIG, or Red Hat hardening guide obtained or revised
- [ ] **Derayah internal build standard supplied** — mandatory re-review; it overrides this document
- [ ] **Before the production host is configured** — mandatory; the open findings must be closed first
- [ ] Fixed interval: annually

## Verification

Nothing verified — no configuration applied. First checks to run on the test host:

```
# Version and architecture — confirms the pin
cat /etc/redhat-release
uname -m
subscription-manager release --show

# SELinux must be enforcing
getenforce

# Python availability for Phase 1 (>= 3.11 required, alongside system Python)
python3 --version
dnf module list python3* 2>/dev/null

# Patch state and where packages come from (open finding #1)
dnf repolist
subscription-manager status

# Network posture
firewall-cmd --list-all
chronyc tracking
```

Record the output here. A baseline that records intent but not verification is a plan — this one is
a plan, and a partial one, and says so.
