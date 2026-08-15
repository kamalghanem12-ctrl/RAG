# Architecture Decision Records

Every ADR here is **Proposed**. None is Accepted. Recommendations in them are engineering
recommendations, not decisions and not approvals.

Six require named Derayah owners to sign off before code may depend on them. Never record an
approval that has not actually been given.

| ADR | Decision | Status | Blocks |
|---|---|---|---|
| [0001](0001-implementation-language.md) | Implementation language and framework | Proposed | Phase 1 |
| [0002](0002-acl-source-of-truth.md) | FileCloud ACL vs. path-derived tier | Proposed — **needs security review** | Phase 2, 3 |
| [0003](0003-authentication-flows.md) | Flow 2 silent auth mechanism | Proposed — **needs identity review** | Phase 9 |
| [0004](0004-rls-and-pooling.md) | RLS context propagation and pooling | Proposed | Phase 2, 6 |
| [0005](0005-ann-recall-under-acl.md) | ANN recall under selective ACL filters | Proposed | Phase 7 |
| [0006](0006-deny-vs-notfound.md) | Deny indistinguishable from not-found | Proposed | Phase 7, 8 |
| [0007](0007-retrieval-eval.md) | Retrieval quality baseline and gate | Proposed | Phase 7 |
| [0008](0008-regulatory-scope.md) | Regulatory scope | Proposed — **needs compliance review** | Phase 0 |
| [0009](0009-entitlement-claims.md) | Entra app roles vs. security groups | Proposed — **needs identity review** | Phase 2 |
| [0010](0010-entitlement-invariants.md) | Entitlement invariants | Proposed — **needs security review** | Phase 2 |
| [0011](0011-filecloud-mcp-scope.md) | FileCloud MCP scope and credential model | Proposed — **needs security review** | FileCloud MCP track |

## `VERIFY` markers

Some ADRs contain claims about third-party behavior that must be checked against current official
documentation before ratification, per rule R1 and the delivery rules. They are marked inline:

```
VERIFY: <claim> — against <source>
```

An ADR with unresolved `VERIFY` markers must not be moved to Accepted.
