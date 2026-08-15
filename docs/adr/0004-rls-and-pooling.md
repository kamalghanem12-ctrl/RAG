# ADR-0004 — RLS Context Propagation and Connection Pooling

**Status:** Proposed
**Blocks:** Phase 2, Phase 6

## Context

The original §15 correctly listed the concerns — RLS policies, secure roles, request/session
context, pooling behavior, transaction boundaries, privilege separation, bypass prevention, failure
behavior — but stated no rule for any of them.

Two failure modes deserve to be settled now rather than discovered in production, because **both
fail silently**: the query returns rows, the application works, and nothing looks wrong.

## Decision

### 1. Request context uses `SET LOCAL` inside an explicit transaction

```sql
BEGIN;
SET LOCAL app.user_id = '...';
SET LOCAL app.departments = '...';
SET LOCAL app.restricted_entitlements = '...';
-- query
COMMIT;
```

Or equivalently `set_config('app.user_id', $1, true)` — the third argument `true` meaning
transaction-local.

**Never** session-scoped `SET`, and never `set_config(..., false)`. On a pooled connection, session
scope outlives the request that set it: the next request to borrow that connection inherits the
previous user's authorization context. Under RLS that is a silent cross-user data leak, and it is
load-dependent — it will not reproduce under single-user testing.

Enforcement: blocked pattern in `.claude/hookify.session-scoped-db-context.local.md`.

### 2. The application role cannot bypass RLS

The role used by the application must:

- not be `SUPERUSER`
- not hold `BYPASSRLS`
- **not own the tables it queries**

The third is the one that gets missed. A table owner bypasses that table's RLS policies entirely
unless the table is declared `FORCE ROW LEVEL SECURITY`. If migrations and the application share a
role — the default in most setups — RLS is silently inert.

Therefore: separate roles. A migration/owner role that owns the schema, and a least-privileged
application role that holds only `SELECT`/`INSERT`/`UPDATE` as needed. Declare
`ALTER TABLE ... FORCE ROW LEVEL SECURITY` regardless, as belt and braces.

### 3. Failure is closed

A request that cannot establish a complete authorization context must fail — never fall through to
a query without context. An RLS policy that reads an unset `app.*` setting must deny, not permit.
Test that the unset case denies, not merely that the set case permits.

## Consequences

- Every data-path query runs inside an explicit transaction. Read-only queries included.
- Alembic runs as the owner role; the application never does.
- Connection-pool configuration becomes security-relevant and belongs in
  `../baselines/postgresql.md` under rule R1.

## Verification

- `tests/authz/` must include a pooled-connection case that borrows the same connection for two
  different users in sequence and asserts no leakage.
- Confirm the application role: `SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = ...`
- Confirm ownership is separate: `\dt` ownership column vs. the application role.

## VERIFY before ratification

```
VERIFY: PostgreSQL 16 RLS + FORCE ROW LEVEL SECURITY semantics for table owners
        — against official PostgreSQL documentation for the pinned version
VERIFY: pooler behavior (pgbouncer transaction vs. session mode) and its interaction
        with SET LOCAL — against pgbouncer documentation
```
