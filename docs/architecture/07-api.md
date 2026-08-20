# API Layer

> Source: original specification §11, §12. Content moved unchanged.

The API layer is the **primary application-level policy enforcement point**.

## Responsibilities

Authentication validation · authorization · identity and claims validation · **principal resolution
against the FileCloud ACL projection** · request validation · rate limiting · audit logging ·
security policy enforcement · calling controlled RAG operations.

> Revised by `../adr/0012-filecloud-acl-authoritative.md`. The API no longer evaluates department
> isolation or restricted entitlements — it resolves *who the caller is* and lets the projection and
> RLS resolve what that entitles them to. See `02-authorization-model.md`.

## Never trust client-supplied

```text
principal_id              exception_id      allowed_groups
filecloud_principal_id    exception_scope   allowed_users
grant / grants            exception_effect  roles / permissions
```

These are derived server-side from validated identity, or from the governed exception store. A
request may carry a search query and legitimate business filters; it may never carry an
authorization value. Supplied authorization parameters are ignored, validated away, or rejected —
never honored.

Reading any of these off a request body is a blocked pattern.

**`department`, `sub_department`, and `security_tier` are now metadata, not authorization.** A client
may legitimately send them as business filters — "search only Commercial documents" — and the API
may honor that as a *narrowing* filter. It must never widen access: applying a metadata filter can
only reduce the authorized result set, never add to it. The authorization predicate runs regardless
of what filters the client sent.

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
becomes an existence oracle: an attacker enumerates document IDs and learns what exists in parts of
the estate they cannot read.

This is more load-bearing under the ACL model than it was under the department model. Where a
department-scoped denial leaked one bit about a whole department, per-document ACLs mean each denial
leaks one bit about one specific document — so an enumeration attack maps the corpus at document
granularity. An error that names the document, or a citation that leaks its title or path, is the
whole vulnerability.

The same applies to citations — titles and paths leak document existence even when content is
withheld. → `../adr/0006-deny-vs-notfound.md`

## Rate limiting

Per-user query-volume limits are an authorization control, not just a capacity control. Sensitive
aggregation leakage — reconstructing a restricted picture from many individually-permitted
retrievals — is in the threat model and has no other mitigation.
See `../security/threat-model.md`.
