# AgriTrace — Logistics Warehouse Management System

AgriTrace is a modular logistics and supply chain application for managing inventory, orders, warehouse operations, and transportation. A shared landing page brings the four modules into one workspace, with AI-assisted analysis and review workflows alongside the operational features.

## Project structure

| Directory | Purpose |
| --- | --- |
| `shared/` | AgriTrace landing page, served by Nginx |
| `student-1-bea/` | Order management frontend, backend, and database service |
| `student-2-yuting/` | Warehouse management frontend, backend, and database service |
| `student-3-lois/` | Inventory management frontend, API, and database service |
| `student-4-sam/` | Transportation frontend and backend, with an embedded SQLite database |
| `ai-services/` | Retrieval-augmented generation (RAG) and multi-agent services |
| `mcp-server/` | Model Context Protocol (MCP) tools and HTTP server |
| `agentic-review/` | Interactive review loop and module-specific prompts |
| `.github/workflows/` | Module CI, AWS connection checks, and deployment workflow |

The application uses Python backends, SQLite databases, and web frontends. Docker Compose builds and runs the application services. AI features use Ollama and separately started Python services; the root Compose stack does not start these AI services.

## Prerequisites

- Git.
- Docker Engine or Docker Desktop with Docker Compose v2 supporting the `include` directive (Compose 2.20.0 or later).
- Python 3.12 and `pip` for local tests and AI services.
- Ollama with the required models if you want model-generated responses.

The transportation backend uses host networking. Linux is the most direct environment for the current configuration; other environments need Docker host-networking support enabled and may require endpoint adjustments.

## Build and run

From the repository root, create the external network used by the application. Run the network creation command once; skip it if `team-network` already exists.

```bash
docker network create team-network
docker compose config --quiet
docker compose build
docker compose up -d
```

Open the shared landing page at **http://localhost:8080**.

| Component | Browser URL / host endpoint |
| --- | --- |
| Shared landing page | http://localhost:8080 |
| Inventory frontend | http://localhost:8081 |
| Orders frontend | http://localhost:8082 |
| Warehouse frontend | http://localhost:5000 |
| Transportation frontend | http://localhost:3004 |
| Inventory API / database service | `localhost:5001` / `localhost:5002` |
| Orders API / database service | `localhost:5011` / `localhost:5012` |
| Warehouse API / database service | `localhost:5021` / `localhost:5020` |
| Transportation API | `localhost:5004` |

To build and run a single module instead, use its Compose file. For example:

```bash
docker compose -f student-4-sam/docker-compose.yml up -d --build
```

Use the same Compose file when stopping an individually started module.

### Manage the stack

```bash
# Show container status
docker compose ps

# Follow service logs
docker compose logs -f

# Rebuild and restart after source changes
docker compose up -d --build

# Stop and remove containers, retaining named database volumes
docker compose down
```

Orders, warehouse, and inventory data use named Docker volumes. `docker compose down -v` also deletes those volumes and their data. Transportation stores its database inside the backend container under the current Compose configuration, so recreating that container can reset transportation data.

## AI services and configuration

AI integrations are configured per module in its Compose file. Inspect each module's `environment` settings when changing endpoints or enabling features; variable names and defaults differ between modules.

| Service | Default host port | Notes |
| --- | --- | --- |
| Ollama | `11434` | Application model defaults commonly use `qwen2.5:0.5b` |
| RAG HTTP server | `5003` | Retrieves supporting context from the project corpus |
| Standalone MCP HTTP server | `5004` | Conflicts with the transportation API's default port |
| Shared multi-agent server | `5005` | Warehouse, orders, and transportation workflows |
| Inventory multi-agent server | `5006` | Separate inventory workflow service |

**Do not start the standalone MCP HTTP server on port `5004` while transportation is running.** Change `MCP_PORT` and the calling modules' `MCP_SERVER_URL` settings if both are needed. Transportation also mounts the shared MCP tools directly from `mcp-server/`.

To start the shared multi-agent server, use a separate terminal from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r ai-services/multi-agent-server/requirements.txt
cd ai-services/multi-agent-server
python3 app.py
```

Verify it with `curl -fsS http://localhost:5005/health`. The Planner and Worker default to `qwen2.5:0.5b`, while the Reviewer defaults to `llama3.1:8b`. Install those models with Ollama when using model-generated analysis:

```bash
ollama pull qwen2.5:0.5b
ollama pull llama3.1:8b
```

The shared workflow server can return data-backed fallback results when Ollama is unavailable. Its transportation workflow reads shipment evidence and records a human Accept, Correct, or Reject decision. See the [multi-agent server guide](ai-services/multi-agent-server/README.md) for API examples, configuration, and review behavior.

## Tests and code checks

Dependencies and tests are maintained per module. For the transportation and shared multi-agent tests, run the following from the repository root in an activated Python virtual environment:

```bash
python3 -m pip install -r student-4-sam/backend/requirements.txt \
  -r ai-services/multi-agent-server/requirements.txt \
  -r ai-services/rag-server/requirements.txt
python3 -m pytest student-4-sam/tests ai-services/multi-agent-server/tests
```

These tests replace model and external service calls, so Ollama does not need to be running. Refer to the module workflows in [`.github/workflows/`](.github/workflows/) for their individual build, test, and smoke-check commands.

The repository also defines pre-commit hooks for Ruff security checks, secret detection, dependency auditing, and selected order-management tests:

```bash
python3 -m pip install pre-commit
pre-commit install
pre-commit run --all-files
```

The order-management hook uses the active Python environment; install that module's test dependencies before running it.

## CI and AWS deployment

Each module has a GitHub Actions workflow for its own checks. Two manually triggered AWS workflows are also included:

- [Test AWS Connection](.github/workflows/aws-connection-test.yml) uses GitHub OIDC with repository variables `AWS_ROLE_ARN` and `AWS_REGION`, then checks AWS identity and the `advanced-software/shared-frontend` ECR repository.
- [Cloud Deployment](.github/workflows/cloud-deployment.yml) targets ECS Fargate in `ap-southeast-2`. It expects the `AWS_DEPLOY_ROLE_ARN` secret and repository variables `VPC_ID`, `PUBLIC_SUBNET_IDS`, and `TASK_EXECUTION_ROLE_ARN`.

The cloud workflow deploys transportation through CloudFormation after a successful transportation CI run, using the tested frontend/backend images. It provisions an ALB, ECS Fargate service, and persistent EFS storage for SQLite. It additionally requires `ALLOWED_CIDR` and the `aws-transportation` GitHub environment. See the [transportation DevOps guide](docs/transportation-devops.md) for the architecture, local security reports, post-commit testing evidence, agentic-loop Testing Review, and AWS setup.

## Troubleshooting

- **External network missing:** create `team-network` before starting Compose.
- **Compose rejects `include`:** check `docker compose version` and use a version that supports it.
- **Port already in use:** check the endpoint table and stop the conflicting process or update the relevant configuration. In particular, transportation and standalone MCP default to the same port.
- **AI service unreachable:** confirm the host service is running and inspect the module's configured URL. Most bridged containers use `host.docker.internal`; transportation uses host networking and loopback addresses. The warehouse backend currently has no explicit Linux `host-gateway` mapping, so add one if your Docker setup cannot resolve `host.docker.internal`.
- **Container exits or a page fails to load:** inspect `docker compose ps` and `docker compose logs <service-name>` for startup errors.

Transportation security hooks generate local reports under `student-4-sam/evidence/`. Stage the implementation, run the three transportation hooks, and stage their reports before committing; the Testing Review checks that these reports match the committed source. See the [complete evidence workflow](docs/transportation-devops.md).
