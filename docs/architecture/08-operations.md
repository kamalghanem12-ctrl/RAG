# Secrets, Observability, and Operations

> Source: original specification §21, §24. Content moved unchanged.
>
> This material was removed from always-on context deliberately. It is a set of **acceptance
> criteria**, checked per phase — not guidance the model needs re-read on every turn.

## Secrets — Delinea PAM

Delinea PAM is the source of truth for production secrets and privileged credentials.

**Never:** hard-code secrets · commit secrets · store production credentials in Git · place
long-lived privileged credentials in the MCP Shim · put database service credentials in a user's
Claude configuration.

**Implement:** least-privileged service identities · secret retrieval · rotation · auditing ·
failure behavior · emergency recovery.

Failure behavior matters as much as retrieval: a service that cannot reach PAM must fail closed,
never fall back to a cached or embedded credential.

Writing an inline password, API key, or DSN with embedded credentials is a blocked pattern.
Integration configuration is subject to rule R1 — see `../baselines/delinea-integration.md`.

## Operations — implement from the start

Structured logging · metrics · tracing where justified · health checks · readiness checks ·
graceful shutdown · retry policies · dead-letter handling · idempotent ingestion · database
migrations · dependency and version pinning · security scanning · backup and recovery · monitoring ·
alerting · audit logging.

## Signals to track

### Identity
Authentication failures · token validation failures · authorization denials.

### Ingestion
New/modified/deleted documents · ACL changes · sync lag · processing failures · embedding failures.

### Retrieval
Query latency · retrieval latency · reranker latency · empty retrieval · retrieval quality ·
**ACL filtering impact** — including the minimum-recall guard from `05-retrieval.md`.

### Platform
MCP health · API latency · PostgreSQL health · pgvector performance · connection pool health ·
CPU / memory / storage.

### Security
Repeated authorization failures · cross-department attempts · restricted-content attempts ·
suspicious MCP activity.

Authorization denials are a security signal, not noise. A user steadily probing outside their
department looks exactly like a misconfigured client until someone reviews the pattern — so the
alerting has to distinguish them.

## Production readiness gate

Do not declare production readiness until every one of these holds:

- [ ] SSO / MFA works
- [ ] Identity and token validation works
- [ ] Authorization is independent of the LLM
- [ ] Department isolation works
- [ ] Internal inheritance works
- [ ] Restricted sub-department controls work
- [ ] PostgreSQL RLS works
- [ ] ACL synchronization works
- [ ] Revocation works
- [ ] Deleted content is no longer retrievable
- [ ] Prompt injection cannot bypass authorization
- [ ] MCP cannot bypass API authorization
- [ ] The client cannot directly access PostgreSQL
- [ ] Production secrets are managed through Delinea PAM
- [ ] Audit trails exist
- [ ] Backup and recovery is tested
- [ ] Failure modes are documented
- [ ] Security tests pass
- [ ] Every configured object has a current baseline in `../baselines/` (rule R1)

Most of this list is mechanized by `pytest tests/authz`. Prefer running the gate over reading it.
