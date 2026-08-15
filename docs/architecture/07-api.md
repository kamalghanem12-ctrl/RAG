# API Layer

> Source: original specification §11, §12. Content moved unchanged.

The API layer is the **primary application-level policy enforcement point**.

## Responsibilities

Authentication validation · authorization · RBAC / ABAC · identity and claims validation ·
department isolation · restricted entitlement evaluation · request validation · rate limiting ·
audit logging · security policy enforcement · calling controlled RAG operations.

## Never trust client-supplied

```text
department        allowed_groups      roles
sub_department    allowed_users       permissions
security_tier
```

These are derived server-side from validated identity. A request may carry a search query and
legitimate business filters; it may never carry an authorization value. Supplied authorization
parameters are ignored, validated away, or rejected — never honored.

Reading any of these off a request body is a blocked pattern.

## Endpoints are capabilities, not authorization

Do **not** create per-scope endpoints:

```text
/api/hr
/api/hr/talent
/api/hr/talent/restricted
/api/commercial/sales
```

URL paths must never be the authorization mechanism. A path-based scheme encodes the org chart into
routing, breaks the moment the org chart changes, and puts the authorization decision in a string
the client controls.

Prefer capability-oriented endpoints:

```text
POST /api/v1/knowledge/search
POST /api/v1/knowledge/context
GET  /api/v1/knowledge/source/{document_id}
```

The API receives the business request; the server independently determines the user's effective
scope from the authorization context. The client cannot elevate authorization by changing a path
any more than by changing a body field.

## Deny must be indistinguishable from not-found

`GET /api/v1/knowledge/source/{document_id}` for a document the user may not read must be
indistinguishable from the same request for a document that does not exist. Otherwise the endpoint
becomes an existence oracle: an attacker enumerates document IDs and learns what exists in
departments they cannot read.

The same applies to citations — titles and paths leak document existence even when content is
withheld. → `../adr/0006-deny-vs-notfound.md`

## Rate limiting

Per-user query-volume limits are an authorization control, not just a capacity control. Sensitive
aggregation leakage — reconstructing a restricted picture from many individually-permitted
retrievals — is in the threat model and has no other mitigation.
See `../security/threat-model.md`.
