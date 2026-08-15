# Enterprise Permission-Aware RAG Platform

A production platform letting Derayah Financial employees query enterprise knowledge through Claude
Desktop, where **authorization is enforced outside the LLM** and unauthorized content can never
enter the retrieval context.

Start with [`CLAUDE.md`](CLAUDE.md) for the working rules and repository map; the design lives under
[`docs/`](docs/). Current state: **Phase 0 — Architecture Validation**. No application code exists
yet. See [`docs/delivery/phases.md`](docs/delivery/phases.md) for the phase gates and
[`docs/adr/`](docs/adr/) for the open decisions.

## Ownership

Work product of **Derayah Financial**. This repository is hosted in a personal GitHub account for
development convenience only. That arrangement is not a transfer of ownership, licence, or any other
right in the material.

No `LICENSE` file is present, and that is deliberate — absent one, default copyright applies and all
rights are reserved. An open-source licence would be incorrect here.

## Confidentiality

This repository documents Derayah's internal security architecture: trust boundaries, threat model,
authorization design, named third-party components, and open security findings that have not yet
been remediated or reviewed.

**Keep it private.** Do not make this repository public, fork it to an organization, or share its
contents outside Derayah without sign-off from Derayah information security.

## Status of the decisions recorded here

Every ADR in `docs/adr/` is **Proposed**. None is Accepted. Recommendations in them are engineering
recommendations — they are not decisions, and they are not approvals. Six require named Derayah
owners to sign off before code may depend on them.

Nothing in this repository records an approval that has been given.
