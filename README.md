# wf — Definition-driven agentic workflow engine (Phase 1)

A YAML workflow definition drives a Temporal interpreter, generic Pydantic AI agents, deterministic checks, an email human gate, and a PDF plan.

Read `REQUIREMENTS.md`, `PLAN.md`, and `AGENTS.md` for the contract.

## Prerequisites (human)

Do not let the agent create cloud resources. Before a live M5–M7 run:

1. **Docker** for the Temporal dev server (`docker compose up`).
2. **Python 3.12**.
3. **Bedrock** (before the M3 live smoke): enable the chosen Claude models in `AWS_REGION` and put the IDs in `.env`.
4. **SES** (before M5): verify the sender, initiator, and reviewer. Sandbox accounts can only mail verified addresses.
5. **S3** (before M6/M7 if not using local artifacts): private bucket, encryption on, block public access.
6. **IAM**: `bedrock:InvokeModel*`, `ses:SendEmail` / `ses:SendRawEmail`, `s3:PutObject` / `s3:GetObject` on the artifact prefix.
7. **Google OAuth** web client with redirect `http://localhost:8000/auth/callback`.

Until those exist, use `WF_ARTIFACT_BUCKET=local`, `--auto-approve`, `TestModel` tests, and mocked HTTP.

## Setup

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
# edit .env — at least WF_REVIEWER_EMAIL and models for a real run
```

WeasyPrint needs Pango on the host (`brew install pango` on macOS) for PDF generation. The `Dockerfile` installs those libraries.

## Run Temporal

```bash
docker compose up -d
```

UI: http://localhost:8233  
gRPC: `localhost:7233`

Default compose starts **only** Temporal. Worker and review app:

```bash
# from the venv, after Temporal is up
python -m wf.engine.worker
python -m wf.hitl.app
```

Or `docker compose --profile full up --build` once `.env` is filled.

## CLI

```bash
wf --help
wf validate definitions/weather_plan.yaml
wf run definitions/weather_plan.yaml --input country=PT --initiator you@example.com --auto-approve
wf status <run_id>
```

`--auto-approve` is refused unless `WF_ENV=dev`. It records `decision: proceed` with reviewer `auto`.

## Artifacts and history

- Local artifacts: `./artifacts/runs/<run_id>/` (envelopes and `output/<workflow_id>.pdf`).
- S3: `s3://$WF_ARTIFACT_BUCKET/runs/<run_id>/`.
- Temporal history: http://localhost:8233

## Tests

```bash
pytest                 # excludes @pytest.mark.live
ruff check src tests
ruff format --check src tests
mypy
```

Live smokes (need network / AWS):

```bash
pytest -m live tests/live/test_openmeteo_live.py
pytest -m live tests/live/test_bedrock_live.py
```

## Manual e2e (AC-08, AC-09)

1. `docker compose up -d` and start the worker + review app.
2. `wf run definitions/weather_plan.yaml --input country=Portugal --initiator <verified>` (no `--auto-approve`).
3. Open the SES review mail on this machine (`localhost` link), sign in with an allowlisted Google account, **Proceed**.
4. Confirm the initiator mail has a PDF that contains: location, forecast table, advisory if any, day-by-day plan, run ID, approval details, and `Weather data by Open-Meteo.com (CC BY 4.0)`.
5. Confirm envelopes under `runs/<run_id>/` and a full history in the Temporal UI.

**Recorded 2026-10-06:** AC-08 and AC-09 were not executed live in this session (no SES/Google/Bedrock credentials in the agent environment). Automated non-live tests cover AC-01 and AC-04–AC-07.

## Troubleshooting

| Symptom | What to check |
|---|---|
| SES `MessageRejected` | Sender and recipient must be verified in the sandbox. |
| Bedrock `AccessDenied` / `UnrecognizedClient` | Model access in the region; inference-profile ID; AWS credentials. |
| OAuth redirect mismatch | Google client redirect must be exactly `http://localhost:8000/auth/callback`. |
| `--auto-approve` refused | `WF_ENV` must be `dev`. |
| WeasyPrint / Pango errors | Install system libraries or render inside the Docker image. |
| Open-Meteo 429 | Per-run URL cache is on; wait and retry. Non-commercial use only. |

## Layout

See `AGENTS.md` §2. Demo definition: `definitions/weather_plan.yaml`.
