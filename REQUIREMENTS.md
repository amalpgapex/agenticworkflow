# REQUIREMENTS — Definition-Driven Agentic Workflow Engine (Phase 1)

Status: Draft v0.2 · Date: 2026-10-06 · Read with `PLAN.md` (design) and `AGENTS.md` (build rules).

**Priority:** **M** = must (Phase 1 exit), **S** = should, **C** = could.
Every requirement is meant to be verifiable by a test or by a manual check listed in §8.

Phase 1 is sequential only. `next`/`goto`, `resolve.mode: tool`, executor `signals`, parallel steps, DOCX, OTEL, and Jev.ai are out of scope.

---

## 1. Functional requirements

### 1.1 Workflow definition

| ID | Pri | Requirement |
|---|---|---|
| FR-01 | M | Definitions are YAML files (`apiVersion: wf/v1`) that are parsed into Pydantic models. Unknown keys are rejected (`extra="forbid"`). |
| FR-02 | M | The loader validates each condition below and reports **every** error with its YAML path:<br>• step `id`s are unique<br>• referenced schemas (`Name@version`), named checks and tools are registered<br>• all CEL expressions compile<br>• `${...}` placeholders resolve to roots allowed for that site (see §1.1.1) |
| FR-03 | M | Workflow `inputs` declare type, required flag, default and simple bounds. Run inputs are validated against them before the workflow starts. |
| FR-04 | M | Step types are `agent` (Phase 1). The model reserves `parallel` and `action` types: the loader rejects them with the message "not supported in Phase 1". |
| FR-05 | M | `wf validate <file>` exits 0 for a valid definition and non-zero with errors otherwise. |

#### 1.1.1 Expression roots (by evaluation site)

| Site | Allowed roots |
|---|---|
| Load-time `${...}` (CLI only) | `env`, `inputs` (defaults only) |
| `run_when` and `input:` mappings | `inputs`, `ctx`, `steps` |
| Prerequisite `check` / `verify` and evaluator CEL `checks` | `inputs`, `ctx`, `steps`, `data` |
| `human_review.required_when` | `inputs`, `ctx`, `steps`, `system` (current step, after eval) |

`env.*` is interpolated in the CLI before the workflow starts. The workflow never evaluates `env`.

### 1.2 Orchestration (interpreter workflow)

| ID | Pri | Requirement |
|---|---|---|
| FR-10 | M | A single Temporal workflow type interprets the validated definition. The definition is passed as workflow input. |
| FR-11 | M | Steps run sequentially in list order. Phase 1 has no `next` / `goto`. |
| FR-12 | M | `run_when` false ⇒ the step is recorded with `system.status = "skipped"`, and no agent is called. |
| FR-13 | M | Prerequisites: evaluate `check`. If it is false, run `resolve` (`mode: agent` only), validate the result against `output_schema`, then evaluate `verify`. Bind the result into `ctx`. If verification fails after `max_iterations`, the run fails and the initiator is notified. No HITL on a failed resolve. |
| FR-14 | M | Executor→evaluator loop runs up to `max_iterations`. Each retry receives:<br>• the evaluator feedback<br>• the failed check results<br>• the previous output |
| FR-15 | M | On loop exhaustion the default `on_exhausted: escalate_to_human` applies: set `system.eval.verdict = "escalated"` and force the human gate (using `defaults.hitl` even if the step has no `human_review` block). `fail` is also allowed; it ends the run and notifies the initiator. |
| FR-16 | M | Every completed, skipped or stopped step produces an envelope (PLAN §7), persisted to the artifact store and exposed to later expressions as `steps.<id>`. Persist only on those terminal statuses. While a human gate is open, the review app reads the pending payload from the Temporal `status()` query. |
| FR-17 | M | Only the engine writes `system.*`. Executor output supplies `data` only. Phase 1 has no executor `signals`. |
| FR-18 | S | `wf status <run_id>` shows the current step, its status and any pending human decision, using a Temporal query. |

### 1.3 Agents

| ID | Pri | Requirement |
|---|---|---|
| FR-20 | M | Executor, evaluator and resolver are generic Pydantic AI agents, built at runtime from step config:<br>• instructions<br>• tool allowlist<br>• output schema<br>• model ID |
| FR-21 | M | Agents can call only the tools in the step's allowlist, served from the MCP weather server. |
| FR-22 | M | Executor output is a typed Pydantic model. If schema validation fails, the agent retries inside the run before the activity returns. |
| FR-23 | M | The evaluator has no tools. It receives the following and returns `EvaluationVerdict {verdict: pass|fail, score: 0–1, unmet_criteria: [str], feedback: str}`:<br>• objective<br>• rubric<br>• executor output<br>• deterministic check results |
| FR-24 | M | The tool-call trace (tool name, arguments, return value) from each executor run is captured and passed to named checks. |
| FR-25 | M | Executor and evaluator model IDs are configured separately. Different models are recommended, but the same model is allowed. |
| FR-26 | M | Each agent run sets usage limits (requests and tokens) from config. Hitting a limit counts as a failed iteration. |

### 1.4 Tools (MCP server)

| ID | Pri | Requirement |
|---|---|---|
| FR-30 | M | `geocode_location(name, country_code?, count=10)` calls `https://geocoding-api.open-meteo.com/v1/search` and returns, per result:<br>• `name`, `latitude`, `longitude`<br>• `country`, `country_code`<br>• `feature_code`, `timezone`, `population`, `admin1` |
| FR-31 | M | `get_daily_forecast(latitude, longitude, days, timezone="auto")` calls `https://api.open-meteo.com/v1/forecast`.<br>• requests Open-Meteo `daily` variables: `weather_code, temperature_2m_max, temperature_2m_min, precipitation_sum, precipitation_probability_max, wind_speed_10m_max`<br>• **the tool maps** each day to the `WeatherReport@1` day shape (`date, weather_code, weather_description, temp_max_c, temp_min_c, precipitation_mm, precipitation_probability_max, wind_speed_max_kmh`) and attaches the WMO description<br>• `days` must be 1–16 |
| FR-32 | M | Tools return structured JSON. HTTP errors and API `{"error": true, "reason": ...}` responses become typed tool errors, not exceptions that crash the run. |
| FR-33 | S | Responses are cached per run, keyed by `run_id` + request URL on the artifact backend (filesystem or S3). In-memory cache is not sufficient because each activity may spawn a new MCP process. |

### 1.5 Deterministic checks (demo)

| ID | Pri | Requirement |
|---|---|---|
| FR-40 | M | `forecast_matches_source` passes only if every day in `data.days` matches the last `get_daily_forecast` return in the trace (exact date; numeric tolerance 0.05). Both sides use the schema day shape. |
| FR-41 | M | `plan_dates_match_forecast`: plan dates equal the forecast dates, in order. |
| FR-42 | M | `plan_respects_weather`: on any **poor-weather** day (`precipitation_probability_max ≥ 60` or `weather_code` ≥ 61), both conditions hold:<br>• `outdoor_suitability` ≠ `good`<br>• `indoor_alternative` is non-empty |
| FR-43 | M | `advisory_covers_severe_days`: every **severe** day (shared Python helper; same rule as the YAML `run_when` in PLAN §6) appears in the advisory. |
| FR-44 | M | Named checks are registered by name in a Python registry. YAML references them only by name; no code appears in YAML. |

Severe-day vs poor-weather are different rules (PLAN §6). Do not collapse them.

Location `verify` (demo): if `city` is empty, `data.feature_code == "PPLC"`; always, country matches (`country_code` when `country` is ISO alpha-2, else case-insensitive country name). If `country` is ISO alpha-2, pass it as `country_code` to `geocode_location`.

### 1.6 Human in the loop (email)

| ID | Pri | Requirement |
|---|---|---|
| FR-50 | M | When the gate opens, the engine emails each reviewer via Amazon SES with:<br>• the workflow, step and attempt<br>• a summary of the evaluator verdict<br>• a review link |
| FR-51 | M | Review links carry a signed, expiring token (`run_id`, `step_id`, `attempt`, `nonce`). Expiry equals the step's HITL timeout. |
| FR-52 | M | The review app requires Google sign-in (OIDC). It accepts a decision only if `email_verified` is true and `email` is in `reviewers`, compared case-insensitively. |
| FR-53 | M | Actions: `proceed`, `proceed_modified` (JSON editor), `redo` (feedback is required), `stop`. |
| FR-54 | M | `proceed_modified`: the edited `data` is validated against the step schema server-side; an invalid edit is rejected with field errors. Named checks are re-run and recorded as `system.human.check_warnings`; they do not block the decision. |
| FR-55 | M | Each decision is delivered as a Temporal signal. The workflow ignores a decision whose `attempt` or `nonce` does not match the pending gate. |
| FR-56 | M | `redo` increments `system.attempt` and re-runs prerequisites, executor and evaluator, with the feedback injected. |
| FR-57 | M | `stop`, or a timeout with `on_timeout: stop`, ends the run with status `stopped` and emails the initiator who stopped it and at which step. |
| FR-58 | M | Every decision is recorded in the envelope: reviewer, timestamp, feedback, and the diff when the output was modified. |

### 1.7 Output and delivery

| ID | Pri | Requirement |
|---|---|---|
| FR-60 | M | After the last step, the `output.from_step` data is rendered with the Jinja2 HTML `template` and converted to PDF with WeasyPrint. |
| FR-61 | M | The PDF includes:<br>• the location and the forecast table<br>• the advisory, if present<br>• the day-by-day plan<br>• the run ID and approval details<br>• the attribution "Weather data by Open-Meteo.com (CC BY 4.0)" |
| FR-62 | M | The PDF is uploaded to S3 (or the local artifact backend) at `runs/{run_id}/output/{workflow_id}.pdf`. |
| FR-63 | M | The initiator receives an email via SES with the PDF attached (raw MIME) and a presigned S3 link with a configurable expiry. When the backend is `local`, the email includes the local path instead of a presigned URL. |
| FR-64 | C | DOCX output via `docxtpl` is **not implemented**. Keep a renderer interface stub only. |

### 1.8 CLI

| ID | Pri | Requirement |
|---|---|---|
| FR-70 | M | `wf run <definition> --input k=v ... --initiator <email>` validates the definition and inputs, starts a run, and prints the `run_id`. |
| FR-71 | S | `wf run --auto-approve` (dev only; refused unless `WF_ENV=dev`) skips the email gate and records `decision: proceed` with reviewer `auto`. Implemented in M4 so local and workflow tests can finish without SES. |

## 2. Data schemas (registered, versioned)

| Schema | Key fields |
|---|---|
| `ResolvedLocation@1` | `name, latitude, longitude, country, country_code, feature_code, timezone` |
| `WeatherReport@1` | `location: ResolvedLocation`; `days: [ {date, weather_code, weather_description, temp_max_c, temp_min_c, precipitation_mm, precipitation_probability_max, wind_speed_max_kmh} ]`; `summary: str` |
| `SafetyAdvisory@1` | `severe_days: [ {date, hazards: [str], advice: str} ]`; `general_advice: str` |
| `ActivityPlan@1` | `location_name: str`; `days: [ {date, weather_summary, outdoor_suitability: good|fair|poor, morning, afternoon, evening, indoor_alternative, packing: [str]} ]`; `general_tips: [str]`; `assumptions: [str]` |
| `EvaluationVerdict@1` | `verdict, score, unmet_criteria, feedback` |
| `HumanDecision@1` | `action, reviewer, attempt, nonce, feedback?, modified_data?` |

The envelope's `system` field must be named `system`. Pydantic v2 treats names with a leading underscore as private attributes, not fields. Phase 1 envelopes have no `signals` field.

## 3. Non-functional requirements

| ID | Pri | Requirement |
|---|---|---|
| NFR-01 | M | Python 3.12; type-checked (`mypy --strict` on `src/wf/definition`, `src/wf/expressions` and `src/wf/engine`); linted with `ruff`. |
| NFR-02 | M | Workflow code is deterministic. All I/O (LLM, HTTP, S3, SES, time) happens in activities. |
| NFR-03 | M | Activities have explicit timeouts and retry policies. Agent activities: 5m start-to-close, at most 2 retries. Checks/persist: 30s. Email/render: 60s. Non-retryable errors are marked as such. |
| NFR-04 | M | No secrets in the repo. Config comes from environment variables or `.env` (`.env.example` committed). AWS credentials come from the standard boto3 credential chain. |
| NFR-05 | M | IAM least privilege for the worker:<br>• `bedrock:InvokeModel*` on the configured models<br>• `ses:SendRawEmail` / `ses:SendEmail`<br>• `s3:PutObject` / `s3:GetObject` on the artifact bucket prefix |
| NFR-06 | M | Logs are structured JSON with `run_id`, `step_id` and `attempt` on every line. Prompts and outputs go to S3 artifacts, not to logs. |
| NFR-07 | M | Test coverage ≥ 80% on `definition`, `expressions`, `engine` and `checks`. No test calls live AWS or Open-Meteo unless it is marked `@pytest.mark.live`. |
| NFR-08 | S | OpenTelemetry is **not implemented** in Phase 1. |
| NFR-09 | M | The review app sets secure session cookies, uses CSRF protection on decision POSTs, and treats every token as single use (workflow nonce; no separate nonce database). |
| NFR-10 | M | Open-Meteo use stays non-commercial and below the free-tier limits (< 600 calls/min, < 10,000/day). |

## 4. Configuration (environment variables)

| Variable | Purpose |
|---|---|
| `WF_ENV` | `dev` or `test`; enables `--auto-approve` only in `dev` |
| `AWS_REGION` | Region for Bedrock, SES and S3 |
| `WF_EXECUTOR_MODEL`, `WF_EVALUATOR_MODEL` | Bedrock model or inference-profile IDs (Pydantic AI `bedrock:` prefix) |
| `WF_AGENT_MAX_REQUESTS` | Per-run request limit for each agent call (default 20) |
| `WF_AGENT_MAX_TOKENS` | Per-run token limit for each agent call (default 20000) |
| `WF_ARTIFACT_BUCKET` | S3 bucket for envelopes and outputs (`local` = filesystem backend; default `local`) |
| `WF_SES_SENDER` | Verified SES sender identity |
| `WF_REVIEWER_EMAIL` | Reviewer allowlist entry for the demo |
| `WF_REVIEW_BASE_URL` | e.g. `http://localhost:8000` |
| `WF_TOKEN_SECRET` | HMAC secret for review tokens and sessions |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google OAuth web client |
| `TEMPORAL_ADDRESS`, `TEMPORAL_NAMESPACE`, `TEMPORAL_TASK_QUEUE` | Temporal connection |
| `WF_PRESIGN_EXPIRY_SECONDS` | Delivery link expiry |

## 5. Dependencies

Pin exact versions in `pyproject.toml` after resolving. Verify the extras names against current docs.

| Package | Use |
|---|---|
| `pydantic` (v2), `pydantic-settings` | Models, config |
| `pydantic-ai-slim[bedrock,mcp]` | Agents on Bedrock (Converse), MCP client |
| `mcp` | MCP server (FastMCP), stdio transport |
| `temporalio` | Workflow engine SDK; `temporalio.testing` for tests |
| `cel-python` | CEL expressions (`celpy`; not `cel-expr-python`) |
| `pyyaml` | YAML parsing (safe loader only) |
| `httpx` | Open-Meteo calls |
| `boto3` | S3, SES |
| `fastapi`, `uvicorn`, `jinja2`, `itsdangerous`, `authlib`, `python-multipart` | Review app, Google OIDC, signed tokens, templates |
| `weasyprint` | HTML → PDF (needs Pango system libraries; install in the Docker image) |
| `typer` | CLI |
| `structlog` | Structured logging |
| Dev: `pytest`, `pytest-asyncio`, `respx`, `moto[s3,ses]`, `ruff`, `mypy` | Tests and quality |

Do not add Jev.ai or `cel-expr-python`.

## 6. External prerequisites (Amal, before M5)

1. **Bedrock:** model access enabled for the chosen Claude models in `AWS_REGION`. Record the model or inference-profile IDs. Needed before the M3 live smoke.
2. **SES:** verify the sender identity, plus the initiator and reviewer addresses. The account is in the sandbox, so recipients must be verified.
3. **S3:** create the artifact bucket (private, encryption on, block public access). Optional until M6/M7 if `WF_ARTIFACT_BUCKET=local`.
4. **IAM:** create a user or role for local runs with the NFR-05 policy, and configure an AWS profile.
5. **Google Cloud:** create an OAuth 2.0 Client (type "Web application") with redirect URI `http://localhost:8000/auth/callback`, and copy its client ID and secret.
6. **Docker** installed locally. The Temporal dev server and its UI run in Compose.

The agent never creates AWS or Google resources.

## 7. Constraints and assumptions

- Public data only; no PII beyond reviewer and initiator email addresses.
- Phase 1 runs locally against AWS services. Review links work only on the host machine.
- "Plan" means a 7-day visitor activity plan for one city. Default location is the capital unless `city` is given.
- The country input accepts a name or an ISO alpha-2 code. Ambiguous names (for example "Georgia") should be given as codes.

## 8. Acceptance criteria (Phase 1 exit)

| ID | Criterion | How verified |
|---|---|---|
| AC-01 | `wf validate` passes the demo definition and fails each invalid fixture with the expected error path. | Unit tests |
| AC-02 | `country=PT`, no city: the prerequisite resolves Lisbon with `feature_code == "PPLC"`. | Live test (`-m live`) |
| AC-03 | Forecast step output matches the mapped tool response for every day (`forecast_matches_source` passes). | Live test plus a unit test with fixtures |
| AC-04 | `safety_advisory` is skipped when no day is severe, and runs when at least one is (fixture-driven). | Workflow tests |
| AC-05 | A forced evaluator `fail` triggers a retry with feedback. After `max_iterations` the gate opens with verdict `escalated`. | Workflow tests (`FunctionModel`) |
| AC-06 | Each human action (proceed, proceed_modified valid/invalid, redo, stop, timeout) produces the specified behaviour and envelope fields. | Workflow tests (time skipping) and a manual test |
| AC-07 | A decision from a non-allowlisted Google account, or with a stale token, is rejected and does not change the workflow. | Review-app tests and a manual test |
| AC-08 | End-to-end: the initiator receives an email with a PDF attachment that opens and contains every FR-61 element, and the presigned link (or local path) downloads the same file. | Manual run (M7) |
| AC-09 | Every step's envelope is in the artifact store under `runs/{run_id}/`, and the Temporal UI shows the full history. | Manual check |
