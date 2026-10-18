---
paths:
  - "backend/**"
---

# Backend rules (Python 3.14 / FastAPI)

- Fully typed code; the type checker must pass. Prefer `X | None`, builtin generics, PEP 695 syntax.
- Async endpoints and async DB access. Never block the event loop (no sync I/O, no CPU-heavy work in handlers; offload to workers).
- Use `Annotated[...]` with `Depends` for dependencies; no global mutable state.
- Request/response models are Pydantic v2 schemas, separate from persistence models unless the ORM decision (ADR 0001) says otherwise.
- Settings via `pydantic-settings`, loaded once and injected.
- Config for lint/format/types lives in `pyproject.toml`. Lint and format with `ruff`.
- Tests with `pytest` + async support; test behaviour through the HTTP API where practical.
- Add dependencies with `uv add`, never edit the lockfile by hand.
