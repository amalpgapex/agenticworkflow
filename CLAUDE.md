# AGENTS.md — Instructions for the Code Agent

You are building Phase 1 of a definition-driven agentic workflow engine. Read these three files in full before writing code:

1. `PLAN.md`: design, decisions (D1–D10), demo definition, envelope, milestones.
2. `REQUIREMENTS.md`: FR/NFR IDs, schemas, configuration, acceptance criteria (AC).
3. This file: how to build it.

If the files conflict, the order of precedence is `REQUIREMENTS.md` > `PLAN.md` > this file. Report each conflict; do not resolve it silently.

If you use Claude Code, copy or symlink this file to `CLAUDE.md` so it loads automatically.

---

## 1. Working rules

- **Build milestone by milestone** (PLAN §9: M0 → M7). Finish a milestone, then do all of the following before starting the next:
  - make its tests pass
  - run `ruff check`, `ruff format --check` and `mypy`
  - report a short summary: what you built, which tests you ran, which REQUIREMENT IDs it covers, and any open issues
- **Stop and ask the human** before you:
  - change a design decision (D1–D10), the envelope shape, or a schema field
  - add a dependency not listed in REQUIREMENTS §5
  - do anything that creates, modifies or deletes cloud resources
- **Never create AWS or Google resources.** The human does REQUIREMENTS §6. Your code only *uses* resources named in the configuration.
- **Never run live calls by default.** Live tests are marked `@pytest.mark.live` and excluded from the default `pytest` run (configure `addopts = "-m 'not live'"`).
- **Verify library APIs against current docs** before using them. These libraries move fast: Pydantic AI, Temporal Python SDK, the MCP Python SDK and cel-python. If an API named in these files does not exist or has changed, use the current equivalent and note it in your milestone report. Do not invent APIs.
- **No secrets in code, tests, logs or commits.** Use `.env` (git-ignored) and commit `.env.example`.
- Keep functions small and typed, and write a docstring for each public function. Prefer explicit code over clever code.
- Do not add Jev.ai, Airflow, Step Functions, `next`/`goto`, `resolve.mode: tool`, executor `signals`, DOCX, or OTEL.

## 2. Repository layout

```
.
├── pyproject.toml              # deps, ruff, mypy, pytest config; console script `wf`
├── docker-compose.yml          # Temporal dev server (+UI) in M0; worker M4; review-app M5
├── Dockerfile                  # python:3.12-slim + WeasyPrint system libs
├── .env.example
├── README.md                   # runbook (written in M7)
├── definitions/
│   └── weather_plan.yaml       # PLAN §6, unless a requirement forces a change
├── templates/
│   ├── weather_plan.html       # PDF template
│   └── email/                  # review.html, delivered.html, stopped.html, failed.html
├── src/wf/
│   ├── config.py               # pydantic-settings; REQUIREMENTS §4
│   ├── logging.py              # structlog JSON; binds run_id/step_id/attempt
│   ├── definition/
│   │   ├── models.py           # Definition, Step, Prerequisite, Executor, Evaluator, HumanReview, Output
│   │   └── loader.py           # YAML (safe_load) → models; cross-reference validation; error paths
│   ├── expressions/
│   │   ├── cel.py              # compile/evaluate CEL over the site-specific roots
│   │   └── template.py         # ${...} interpolation (each placeholder is a CEL expression)
│   ├── schemas/
│   │   ├── registry.py         # "Name@version" → Pydantic model
│   │   ├── weather.py          # ResolvedLocation, WeatherReport, SafetyAdvisory, ActivityPlan
│   │   └── core.py             # Envelope, SystemMeta, EvalResult, HumanInfo, EvaluationVerdict, HumanDecision
│   ├── checks/
│   │   ├── registry.py         # name → callable(data, context, tool_trace) -> CheckResult
│   │   └── weather.py          # FR-40..FR-43 plus shared severe-day helper
│   ├── tools/
│   │   ├── mcp_weather_server.py   # FastMCP stdio server: geocode_location, get_daily_forecast
│   │   └── openmeteo.py            # httpx client, WMO code map, per-run cache
│   ├── agents/
│   │   ├── factory.py          # build Pydantic AI agents from step config
│   │   ├── executor.py
│   │   ├── evaluator.py
│   │   ├── resolver.py
│   │   └── trace.py            # extract tool calls/returns from agent messages
│   ├── engine/
│   │   ├── workflow.py         # InterpreterWorkflow (deterministic)
│   │   ├── activities.py       # agent runs, checks, persistence, email, render
│   │   ├── worker.py
│   │   └── client.py           # start / signal / query helpers
│   ├── hitl/
│   │   ├── app.py              # FastAPI review app
│   │   ├── auth.py             # Google OIDC (authlib), allowlist check
│   │   ├── tokens.py           # itsdangerous signed, expiring tokens
│   │   └── templates/          # review page
│   ├── notify/email.py         # SES raw MIME (attachments)
│   ├── render/pdf.py           # Jinja2 → WeasyPrint; DOCX interface stub
│   ├── storage/artifacts.py    # S3 backend + local filesystem backend
│   └── cli.py                  # typer: validate, run, status
└── tests/
    ├── unit/ ...
    ├── workflow/ ...           # temporalio.testing time-skipping env
    ├── fixtures/               # Open-Meteo JSON, invalid definitions, envelopes
    └── live/ ...               # @pytest.mark.live only
```

## 3. Build order and specifics per milestone

### M0 — Scaffold
- `pyproject.toml` with `src/` layout and Python 3.12. Pin versions after resolving.
- Docker Compose: **Temporal dev server only** (`temporal server start-dev`, persistent `--db-filename` volume, UI exposed). Do not add empty worker/review-app services yet.
- `wf --help` works. `config.py` loads every REQUIREMENTS §4 variable; missing required values fail with a clear message when those values are needed. Defaults: `WF_ARTIFACT_BUCKET=local`, usage limits 20 requests / 20000 tokens.

### M1 — Definition, expressions, envelope, registries
- Models use `ConfigDict(extra="forbid")`. No `next`, no `signals`, no `resolve.mode: tool`. Implement FR-01–FR-05 as revised.
- Collect **all** loader errors with YAML paths. Do not stop at the first error.
- CEL: compile every expression at load time; evaluate only in the engine; context is plain JSON. Use `celpy.adapter.json_to_cel`.
- `${...}` interpolation: each placeholder is a CEL expression; `env.*` is resolved **at load time in the CLI**.
- Parse HITL timeouts as `h` / `m` / `s` only.
- `Envelope.system` is a field named `system`. No `signals` field.
- Invalid-definition fixtures, one per remaining FR-02 rule, for AC-01.

### M2 — MCP weather server
- FastMCP server over stdio with exactly two tools (FR-30, FR-31). Validate `days` to 1–16.
- Map Open-Meteo daily columns into the `WeatherReport@1` day shape, including WMO `weather_description`.
- Typed tool errors (FR-32). Per-run filesystem cache keyed by `run_id` + URL (FR-33).
- Tests use `respx` with recorded fixtures. Add one live smoke test.

### M3 — Agents
- `factory.py` builds a Pydantic AI `Agent` per call. Filter MCP tools with the current API (`toolset.filtered(...)` or `allowed_tools=`).
- Set usage limits on every run (FR-26).
- Executor prompt order: instructions, JSON input, retry extras, redo human feedback.
- Evaluator: no tools; `output_type=EvaluationVerdict`; judge, do not rewrite. Enforce in code: `verdict` cannot be `pass` if any deterministic check failed.
- `trace.py` extracts `(tool_name, args, return_value)`.
- Tests use `TestModel` or `FunctionModel`. Add one live Bedrock smoke test.

### M4 — Interpreter workflow
- One workflow type, `InterpreterWorkflow`. Input is `{definition_json, inputs, initiator, run_id}`. Follow PLAN §5 as revised (sequential, query-before-persist).
- Determinism (NFR-02): no I/O / `datetime.now()` / `random` / `uuid` in workflow code. If the Temporal sandbox rejects `celpy`, evaluate CEL in a local activity and report which option you used.
- Activities listed in the original M4 section, with NFR-03 timeouts.
- HITL: signal `human_decision`, query `status()`, `wait_condition` with timeout, ignore stale attempt/nonce.
- `--auto-approve` when `WF_ENV=dev`.
- Time-skipping tests for AC-04, AC-05, AC-06.

### M5 — HITL email and review app
- Signed token `{run_id, step_id, attempt, nonce}`; max age equals the step timeout.
- Google OIDC via authlib; `email_verified` + allowlist.
- Review page from Temporal `status()`; four actions; CSRF; `proceed_modified` validation + check warnings + JSON diff.
- SES raw MIME. Fail fast if the sender is unverified.
- Tests for AC-07.

### M6 — Output and delivery
- Render `templates/weather_plan.html` with FR-61 fields.
- WeasyPrint → `runs/{run_id}/output/{workflow_id}.pdf`.
- Email with attachment + presigned link or local path.
- Renderer interface with a `docx` stub only.

### M7 — End to end and runbook
- `README.md` with prerequisites, `.env`, compose, CLI, artifacts, Temporal UI, troubleshooting.
- Record that AC-08/AC-09 need a human with AWS/Google configured.

## 4. Coding conventions

- Python 3.12, async throughout the worker and app, type hints everywhere.
- Pydantic v2 models for all boundary data. Use no untyped dicts across module boundaries, except the CEL context.
- Errors: define `wf.errors` with `DefinitionError`, `ExpressionError`, `ToolError`, `CheckError`, `DeliveryError`. Mark non-retryable Temporal failures explicitly.
- Logging: structlog JSON. Bind `run_id`, `step_id` and `attempt`. Never log prompts, model outputs, tokens or email bodies (NFR-06).
- Tests: `pytest` and `pytest-asyncio`. Name tests after behaviour. Reference requirement IDs in the docstrings.

## 5. Definition of done (Phase 1)

- AC-01 to AC-09: automated ones pass; AC-02/AC-03/AC-08 recorded as live-with-human when credentials are absent.
- `pytest` (non-live) is green; coverage ≥ 80% on the modules listed in NFR-07.
- `ruff` and `mypy` are clean on the paths in NFR-01.
- README runbook lets a new person run the demo end to end.
