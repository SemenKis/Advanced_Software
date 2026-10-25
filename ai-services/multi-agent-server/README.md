# Shared Multi-Agent Server

The server is a shared **local Python process**, not a Docker Compose service.
It serves the warehouse, orders, and transportation workflows on port `5005`.
Transportation workflows use the read-only shipment API on
`http://localhost:5004/api/shipments`; the transportation backend must be
running locally.

## Start locally

Start Ollama and ensure the configured models are available if model-generated
analysis is wanted. The Planner and Worker default to `qwen2.5:0.5b`; the
Reviewer defaults to `llama3.1:8b`. The workflow still returns data-backed
fallbacks when Ollama is unavailable, and marks those agents as fallback.

In a terminal, from the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -r ai-services/multi-agent-server/requirements.txt
cd ai-services/multi-agent-server
python3 app.py
```

Keep this terminal running. Check that the server is ready:

```bash
curl -fsS http://localhost:5005/health
```

In a second terminal, run a transportation workflow and make a human decision:

```bash
cd ~/Documents/Advanced_Software/ai-services/multi-agent-server
python3 workflow_runner.py --domain transportation "Review delayed shipments and recommend next steps"
```

The Transportation Management page at `http://localhost:3004` also provides a
workflow form. It displays Planner, Worker, and Reviewer results and shipment
evidence, then allows the user to approve, correct (with a correction note), or
reject the result. These actions record a decision; the agents never modify or
dispatch shipment records.

The HTTP API can also be called directly:

```bash
curl -fsS -X POST http://localhost:5005/workflow \
  -H 'Content-Type: application/json' \
  -d '{"domain":"transportation","request":"Review delayed shipments"}'
```

The workflow response includes a `workflow_id`. Submit the human decision to
`POST /workflow/decision` with `workflow_id`, `domain: "transportation"`,
`decision` (`Accept`, `Correct`, or `Reject`), and optional `note`. A correction
requires a non-empty note. Decisions are saved in the workflow history and
audit log.

Transportation evidence flows from Planner guidance to the Worker's read-only
shipment lookup, then to the Reviewer together with both agents' outputs.
Each stage has a coordinator deadline (`AGENT_STEP_TIMEOUT_SECONDS`, default
30 seconds). A failed or timed-out stage is recorded explicitly and the
workflow still requires human review. Model requests have their own HTTP
timeout; a coordinator timeout does not terminate an already running request.

Run the shared review loop with `python3 agentic-review/review_loop.py` from
the repository root. Select `student-4-sam` and `multi_agent`, `testing`, or
`cloud_deployment` for the Release 2 review modes. Existing Release 1 modes
remain available. Multi-agent history and human decisions are filtered to the
transportation domain. The cloud review reports readiness from available
files; it does not perform a deployment.

Run automated checks from the repository root:

```bash
python3 -m pip install -r student-4-sam/backend/requirements.txt -r ai-services/rag-server/requirements.txt
python3 -m pytest student-4-sam/tests ai-services/multi-agent-server/tests
```

The transportation CI workflow runs these tests and uploads a JUnit report on
pushes and pull requests affecting this implementation. Tests replace model
and external service calls, so they do not require a running Ollama instance.

To override local endpoints or models, set `MULTI_AGENT_SERVER_URL`,
`TRANSPORTATION_API_URL`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and
`OLLAMA_REVIEW_MODEL` before starting the server. Do not add this server as a
Docker Compose service; other local modules can call it over the host's port
`5005`.
