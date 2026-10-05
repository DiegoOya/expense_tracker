# 1. Functional core, imperative shell, one port for the LLM

- Status: accepted
- Date: 2026-10-05

## Context

The project is a small monolith. The aim is to keep business rules
testable without I/O, with no ceremony beyond that.

## Decision

- `domain/` holds pure functions and value types. It imports only the
  standard library (minus I/O modules) and itself.
- `server.py` (MCP) and `adapters/` (SQLite, categorizers) form the
  shell: they load data, call the domain and persist the result.
- There is no repository interface: storage is called from the shell,
  and the domain receives and returns plain data.
- The only port is `Categorizer` (a `typing.Protocol` in the domain),
  because it is the only real swap: a fake for tests and CI, an LLM
  later.
- `tests/test_domain_purity.py` enforces the import rule with `ast`
  (no import-linter).

## Consequences

- Domain tests need no fixtures, mocks or database.
- If a second real swap appears (e.g. another storage), we add a port
  then, with a new ADR. Not before.
