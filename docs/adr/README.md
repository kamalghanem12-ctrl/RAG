# Architecture Decision Records

No ADR here is Accepted. Recommendations in them are engineering recommendations, not decisions and
not approvals. Never record an approval that has not actually been given.

Seven require named Derayah owners to sign off before code may depend on them.

| ADR | Decision | Status | Blocks |
|---|---|---|---|
| [0001](0001-implementation-language.md) | Implementation language and framework | Proposed | Phase 1 |
| [0002](0002-acl-source-of-truth.md) | FileCloud ACL vs. path-derived tier | **Superseded by 0012** | — |
| [0003](0003-authentication-flows.md) | Flow 2 silent auth mechanism | Proposed — **needs identity review** | Phase 9 |
| [0004](0004-rls-and-pooling.md) | RLS context propagation and pooling | Proposed | Phase 2, 6 |
| [0005](0005-ann-recall-under-acl.md) | ANN recall under selective ACL filters | Proposed — **escalated by 0012** | **Phase 6**, 7 |
| [0006](0006-deny-vs-notfound.md) | Deny indistinguishable from not-found | Proposed | Phase 7, 8 |
| [0007](0007-retrieval-eval.md) | Retrieval quality baseline and gate | Proposed | Phase 7 |
| [0008](0008-regulatory-scope.md) | Regulatory scope | Proposed — **needs compliance review** | Phase 0 |
| [0009](0009-entitlement-claims.md) | Entra app roles vs. security groups | **Largely dissolved by 0012** — failure mode relocated to 0013 | — |
| [0010](0010-entitlement-invariants.md) | Entitlement invariants | **Moot under 0012** | — |
| [0011](0011-filecloud-mcp-scope.md) | FileCloud MCP scope and credential model | Proposed — **needs security review** | FileCloud MCP track |
| [0012](0012-filecloud-acl-authoritative.md) | **FileCloud ACL is the authoritative authorization source** | Proposed — **needs security + information-governance ratification** | Phase 2, 3, 6, 7 |
| [0013](0013-principal-mapping.md) | Entra-to-FileCloud principal mapping, group expansion | Proposed — **needs identity review** | Phase 2, 3 |
| [0014](0014-rag-exceptions.md) | RAG authorization exceptions | Proposed — **needs security approval**; 1 open finding | Phase 2 |

## The 0012 change

ADR-0012 revises the authorization model: Entra ID authenticates, FileCloud decides document access,
and PostgreSQL holds a synchronized projection that the retrieval predicate reads under RLS. It
supersedes 0002, dissolves 0009, makes 0010 moot, and escalates 0005 from a Phase 7 question to a
Phase 6 design risk.

Current state, migration steps, and rollback: `../delivery/migration-filecloud-acl.md`.

**ADR-0014 carries one accepted risk with no approver recorded** — a wildcard exception granting a
principal read access to the entire indexed corpus, in all environments including production. It was
requested explicitly. A blank approver is an open finding, and it must be zero before production.

## `VERIFY` markers

Some ADRs contain claims about third-party behavior that must be checked against current official
documentation before ratification, per rule R1 and the delivery rules. They are marked inline:

```
VERIFY: <claim> — against <source>
```

An ADR with unresolved `VERIFY` markers must not be moved to Accepted.
