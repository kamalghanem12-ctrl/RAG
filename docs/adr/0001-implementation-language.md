# ADR-0001 — Implementation Language and Framework

**Status:** Proposed
**Blocks:** Phase 1

## Context

The original specification fixed the identity provider, embedding model, vector store, and
integration protocol, but never named an implementation language for the API layer, RAG service, or
ingestion worker. Phase 1 cannot start without it, and it determines the static-analysis and
enforcement tooling.

## Options

**Python.** FastAPI + SQLAlchemy/asyncpg + pgvector. Native fit for BGE-M3 (FlagEmbedding /
sentence-transformers), first-class MCP SDK, mature Entra/MSAL support, and the ecosystem most of
the security tooling targets.

**TypeScript / Node.** Strong MCP SDK, natural fit for the desktop shim. But BGE-M3 requires either
a separate Python service or an ONNX runtime path, adding a component to the critical path.

**Mixed.** Python core, TypeScript shim. Best-of-both, at the cost of two toolchains, two
dependency-scanning setups, and two sets of build infrastructure for a single product.

## Decision

**Python**, across API, RAG service, ingestion, and MCP server.

- API: FastAPI
- DB: SQLAlchemy 2.x + asyncpg, Alembic for migrations
- Embedding: BGE-M3 via FlagEmbedding
- MCP: the Python MCP SDK
- Quality: ruff, mypy, pytest

The shim is also Python initially. If desktop packaging proves painful it may be revisited as its
own ADR — but not before Phase 9, and not without measuring the actual pain.

## Consequences

- Single toolchain, single dependency-scanning surface, single set of hookify patterns.
- BGE-M3 runs in-process or as a local service without a language boundary.
- The shim ships to Windows and needs a packaging story regardless of language — see ADR-0003.

## VERIFY before ratification

```
VERIFY: current Python MCP SDK support for the client/shim role — against official MCP documentation
VERIFY: MSAL Python broker support on Windows (pymsalruntime) — against Microsoft identity platform docs
```
