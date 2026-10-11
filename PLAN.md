# PLAN — Definition-Driven Agentic Workflow Engine (Phase 1 PoC)

Status: Draft v0.2 · Date: 2026-10-06 · Owner: Amal Gangodkar

Companion files: `REQUIREMENTS.md` (what must be true) and `AGENTS.md` (how the code agent builds it).

---

## 1. Goal

Prove that a YAML workflow definition can drive a sequence of generic agents end to end:
- an Executor and Evaluator loop for each step
- an email-based human-in-the-loop (HITL) gate
- conditional execution driven by system fields
- a final JSON output rendered to PDF and emailed to the initiator

**Demo workflow:** "Weather-aware plan".
1. The user names a country.
2. The system resolves a city, fetches the Open-Meteo forecast, and adds a safety advisory only if severe weather is forecast.
3. It drafts a 7-day plan, which a human approves.
4. It emails the plan as a PDF.

## 2. Scope

| In scope (Phase 1) | Deferred |
|---|---|
| Sequential steps; `run_when` conditional skip | Parallel / fan-out; `next` / `goto` routing |
| YAML definitions, validated at load | Visual definition builder; `resolve.mode: tool`; executor `signals` |
| Email HITL via Amazon SES; Google OAuth identity | Slack/Teams channels |
| AWS services: Bedrock, SES, S3 | Full AWS deployment (ECS/Fargate, Temporal Cloud) |
| Local runtime: Temporal dev server in Compose; worker and review app added at M4/M5 | Multi-tenant, RBAC beyond an email allowlist |
| PDF output | DOCX output (interface stubbed); OTEL; Jev.ai |

## 3. Key design decisions

| # | Decision | Reason |
|---|---|---|
| D1 | The orchestrator is a **deterministic Temporal workflow that interprets the definition**. No LLM controls flow. | Reproducible routing and full audit history. Temporal's documented pattern for user-defined workflows is a single interpreter workflow. **Not Airflow:** a 72h email gate needs signals, not a sensor/DB poll; a YAML interpreter is a poor fit for static DAGs; local Airflow is a heavier stack. **Not Step Functions:** AWS-only, opposite of the cloud-agnostic orchestrator goal. **Not Jev.ai:** Jev is a typed decision API, not an orchestrator or a generation model. Using it (or `jev-orchestration`) for routing would put a model back on the control path. |
| D2 | The validated definition is **passed as workflow input**, not read inside the workflow. | Temporal workflow code must be deterministic. A file edited mid-run must not change a running workflow. |
| D3 | Each agent run (resolver, executor, evaluator) is **one coarse Temporal activity**. Phase 1 does not use `TemporalAgent`. | Agents are configured at runtime from YAML, with per-step instructions, tools and schema. A coarse activity keeps that fully dynamic. A retry re-runs the whole agent call, which is acceptable for the PoC. |
| D4 | **Hub-and-spoke routing.** The evaluator returns a verdict to the engine, and the engine re-dispatches the executor. | Iteration caps, persistence of every attempt, single audit trail. |
| D5 | **The evaluator judges only.** It never edits or formats output. | Edits made by the evaluator would themselves go unevaluated. |
| D6 | **Deterministic checks run before the LLM evaluator.** | Facts that can be checked mechanically (for example, the forecast copied correctly) should never depend on an LLM judgement. |
| D7 | **Conditions use CEL**, evaluated by the engine. Roots depend on the site (REQUIREMENTS §1.1.1). | Safe, side-effect-free expressions. An LLM never decides a route. `env` is resolved only in the CLI. |
| D8 | **Tools are exposed through a local MCP server** (stdio), with an allowlist per step. Email, S3 and PDF are engine actions, never LLM tools. | Keeps the MCP pattern while giving the LLM no side-effecting tools. |
| D9 | **Location:** if `city` is set, geocode it (with `country_code` when `country` is ISO-2). Otherwise the resolver picks a `PPLC` result for that country. Verify PPLC when city is empty, and always verify country match. | Demonstrates "LLM proposes, deterministic check verifies". Open-Meteo search by `name=PT` is not reliable; pass ISO-2 as `country_code`. REST Countries is not used. |
| D10 | Final rendering is **template code** (Jinja2 HTML → WeasyPrint PDF). | Deterministic and testable; no LLM formatting. |

## 4. Architecture (Phase 1)

```
            +------------- local Docker Compose ----------------------------+
 wf CLI --->| Temporal dev server <--> Worker (interpreter + activities)    |
 (start)    |                          |  +- agents (Pydantic AI) -> Bedrock|
            |                          |  +- MCP weather (stdio) -> Open-Meteo
            |                          |  +- artifacts -> local FS or S3    |
            |                          |  +- email -> SES                   |
            | Review app (FastAPI) <-- reviewer clicks email link           |
            |   +- Google OAuth (OIDC)                                      |
            |   +- query status + signal decision                           |
            +---------------------------------------------------------------+
```

M0 Compose starts **only** Temporal + UI. Worker is added at M4; review app at M5.

Phase 1 limitation: review links point to `http://localhost:<port>`, so the reviewer opens them on the machine running the stack. Phase 2 moves the stack to AWS behind HTTPS.

## 5. Per-step lifecycle

1. **`run_when`**: if present and false, record status `skipped`, persist the envelope, and continue.
2. **Prerequisites**: for each one, evaluate `check`. If it is unmet, run `resolve` (`mode: agent`), validate against the schema, run `verify`, and bind the result into `ctx`. `ctx` starts as `{}`. Failed verify after `max_iterations` fails the run (no HITL).
3. **Build input** from `input:` CEL mappings.
4. **Executor agent**: runs with the step instructions, the allowlisted MCP tools and the output schema. Validation output is fed back to it on retry.
5. **Deterministic checks**: Pydantic validation, then CEL `checks`, then named Python checks. The tool-call trace is available to the checks.
6. **Evaluator agent**: scores against the rubric and the check results, and returns `pass` or `fail` plus feedback. Code forces `fail` if any deterministic check failed.
7. **Loop**: on `fail` with iterations below `max_iterations`, go back to step 4 with the feedback. When the cap is reached, apply `on_exhausted`, which defaults to `escalate_to_human` (uses `defaults.hitl` even if the step omitted `human_review`).
8. **Human gate**: if `human_review.required_when` is true, or the step escalated:
   - send the review email and wait for a signal, up to `timeout`
   - the review app **queries** `status()` for the pending payload (do not persist a non-terminal envelope)
   - `proceed` continues the workflow
   - `proceed_modified` re-validates the edited `data` and continues
   - `redo` increments `attempt` and returns to step 2, carrying the feedback
   - `stop` notifies the initiator and ends the run
   - ignore signals whose `attempt` or `nonce` do not match
9. **Persist** the envelope only when the step is `completed`, `skipped`, `stopped`, or `failed`, then add it to `steps.<id>`.
10. **Next step**: the next step in list order.

After the last step, the **output phase** renders the template to PDF, uploads it, and emails the initiator the PDF plus a presigned link (or local path).

HITL timeout strings parse as `h` / `m` / `s` only (for example `72h`).

## 6. Demo workflow definition (target)

Severe-day rule (advisory `run_when` and `advisory_covers_severe_days`) lives in one Python helper:
`weather_code in [65, 67, 75, 82, 86, 95, 96, 97, 99]` or `wind_speed_max_kmh >= 50`.

Poor-weather rule (`plan_respects_weather`) is different:
`precipitation_probability_max >= 60` or `weather_code >= 61`.

```yaml
apiVersion: wf/v1
workflow:
  id: weather-plan
  version: 0.1.0
  description: Weather-aware 7-day plan for a country, reviewed by a human.
  inputs:
    country: {type: string, required: true}      # name or ISO alpha-2
    city:    {type: string, required: false, default: ""}
    days:    {type: integer, default: 7, min: 1, max: 16}
  defaults:
    model: ${env.WF_EXECUTOR_MODEL}
    evaluator_model: ${env.WF_EVALUATOR_MODEL}
    max_iterations: 3
    hitl: {channel: email, timeout: 72h, on_timeout: stop}
  reviewers: ["${env.WF_REVIEWER_EMAIL}"]

steps:
  - id: get_forecast
    type: agent
    prerequisites:
      - id: location
        check: "has(ctx.location)"
        resolve:
          mode: agent
          instructions: >
            Resolve one location in ${inputs.country}. If city "${inputs.city}" is
            non-empty, geocode it (pass country_code when the country input is
            ISO alpha-2). Otherwise geocode the country and return the result
            whose feature_code is PPLC. Return one matching geocoding result.
          tools: [geocode_location]
          output_schema: ResolvedLocation@1
          verify:
            - "inputs.city != '' || data.feature_code == 'PPLC'"
            - "size(inputs.country) == 2 ? data.country_code == inputs.country : data.country.lowerAscii() == inputs.country.lowerAscii()"
        bind: ctx.location
    input:
      location: "ctx.location"
      days: "inputs.days"
    executor:
      instructions: >
        Call get_daily_forecast for the given location and days, using the
        location timezone when present. Copy every day exactly as the tool
        returned it, including weather_description. Write a short summary.
      tools: [get_daily_forecast]
      output_schema: WeatherReport@1
    evaluator:
      checks:
        - "size(data.days) == inputs.days"
      named_checks: [forecast_matches_source]
      rubric:
        - "Summary is consistent with the daily values."
    human_review:
      required_when: "system.eval.verdict == 'escalated'"

  - id: safety_advisory
    type: agent
    run_when: >
      steps.get_forecast.data.days.exists(d,
        d.weather_code in [65, 67, 75, 82, 86, 95, 96, 97, 99] || d.wind_speed_max_kmh >= 50.0)
    input: {forecast: "steps.get_forecast.data"}
    executor:
      instructions: "Write a short safety advisory for the severe-weather days only."
      tools: []
      output_schema: SafetyAdvisory@1
    evaluator:
      named_checks: [advisory_covers_severe_days]
      rubric: ["Advice is specific to the forecast hazards and not alarmist."]

  - id: create_plan
    type: agent
    input:
      forecast: "steps.get_forecast.data"
      advisory: "steps.safety_advisory.system.status == 'completed' ? steps.safety_advisory.data : null"
    executor:
      instructions: >
        Create a day-by-day plan for a visitor. For each forecast day, give morning,
        afternoon and evening activities that suit that day's weather, plus an indoor
        alternative and packing notes. Respect the advisory if present.
      tools: []
      output_schema: ActivityPlan@1
    evaluator:
      checks: ["size(data.days) == size(steps.get_forecast.data.days)"]
      named_checks: [plan_dates_match_forecast, plan_respects_weather]
      rubric:
        - "Activities are plausible for the resolved city."
        - "Poor-weather days lead with indoor options."
    human_review:
      required_when: "true"

output:
  from_step: create_plan
  formats: [pdf]
  template: templates/weather_plan.html
  deliver:
    to: initiator
    subject: "Your ${steps.get_forecast.data.location.name} plan"
    attach: true
    link: presigned_s3
```

## 7. Step envelope (system fields)

```json
{
  "system": {
    "run_id": "wf-...", "workflow_id": "weather-plan", "definition_version": "0.1.0",
    "step_id": "create_plan", "step_type": "agent", "schema": "ActivityPlan@1",
    "status": "completed",
    "attempt": 1,
    "eval": {"verdict": "pass", "score": 0.9, "iterations": 2,
             "unmet_criteria": [], "checks": [{"name": "...", "passed": true, "detail": ""}]},
    "human": {"required": true, "decision": "proceed", "reviewer": "x@gmail.com",
              "decided_at": "...", "feedback": "", "modified": false, "check_warnings": [],
              "diff": null},
    "model": {"executor": "...", "evaluator": "..."},
    "usage": {"input_tokens": 0, "output_tokens": 0},
    "artifact_uri": "s3://.../envelope.json",
    "started_at": "...", "completed_at": "..."
  },
  "data": { }
}
```

Status values: `completed` | `skipped` | `stopped` | `failed`. Only the engine writes `system`. No `signals` field in Phase 1.

## 8. HITL email flow

1. The engine sends a review email containing the step name, a short summary, the evaluator verdict, and a link to `/review/<token>`.
2. The token is signed and time-limited (expiry equals the HITL timeout) and carries `run_id`, `step_id`, `attempt` and a nonce.
3. The reviewer signs in with Google. Accept the decision only if `email_verified` is true and `email` is in `reviewers`.
4. The page loads pending output via Temporal `status()` and shows checks plus four actions.
5. The app sends a Temporal signal. The workflow ignores stale `attempt` or nonce. Single-use is the workflow nonce.
6. On timeout, `on_timeout: stop` notifies the initiator.

## 9. Milestones

| M | Deliverable | Exit test |
|---|---|---|
| M0 | Repo scaffold, config, Temporal-only Docker Compose, `wf --help` | `docker compose up` starts the Temporal dev server and its UI |
| M1 | Definition models and loader, CEL helpers, envelope, schema and check registries | `wf validate definitions/weather_plan.yaml` passes; invalid fixtures fail with clear errors |
| M2 | MCP weather server (`geocode_location`, `get_daily_forecast`) | Unit tests with mocked HTTP; a live smoke call returns the forecast |
| M3 | Resolver, executor and evaluator agents (Bedrock) | Tests with `TestModel`/`FunctionModel`; one live Bedrock call succeeds |
| M4 | Interpreter workflow: prerequisites, loop, checks, `run_when`, HITL wait, `--auto-approve` | Temporal time-skipping tests cover all four human decisions and timeout |
| M5 | Review app: Google OIDC, signed tokens, signal sending; SES review email | Manual: email received → sign-in → each action resumes the workflow correctly |
| M6 | Output phase: PDF render, artifact upload, delivery email with attachment | PDF opens; email received with attachment and working link or local path |
| M7 | End-to-end run plus README runbook | `wf run ... --input country=Portugal` delivers an approved PDF |

## 10. Risks and mitigations

| Risk | Mitigation |
|---|---|
| SES sandbox | Verify identities before M5; fail fast if unverified. |
| `@gmail.com` sender DMARC | Prefer a domain identity if available. |
| Bedrock access | Model IDs from config; M3 live smoke. |
| LLM mis-copies forecast | Tool maps to schema shape; `forecast_matches_source` compares to the trace. |
| Wrong capital / `name=PT` | Pass ISO-2 as `country_code`; verify PPLC + country. |
| Open-Meteo limits | Per-run URL cache on the artifact backend; CC-BY in the PDF. |
| Localhost review links | Accepted for Phase 1. |
| Temporal sandbox vs `celpy` | Compile at load; evaluate in a local activity if the sandbox rejects the import. |

## 11. Phase 2 (not built now)

- Deploy the worker and review app to ECS/Fargate behind an ALB with HTTPS, and choose Temporal Cloud or self-hosted.
- Parallel steps, `next`/`goto`, `resolve.mode: tool`, executor `signals`, DOCX, Slack/Teams HITL, SES production access.
- Optional Jev.ai as an evaluator backend only (map score/noul into `EvaluationVerdict`). Never use Jev for routing.
- Optional switch to `TemporalAgent` for per-tool-call durability.

## 12. Open questions for Amal

1. **Plan type.** Locked: 7-day visitor activity plan for one city.
2. **Location rule.** Locked: capital unless `city` is given.
3. **SES sender.** Still open for the human: domain identity vs verified personal address.
4. **Review app hosting.** Locked: localhost is acceptable for Phase 1.
5. **Bedrock models.** Still open for the human: which Claude models and region are enabled.
