# ECS Fargate deployment

This deployment is prepared but has **not** been run against AWS. Running the
deployment command creates billable AWS resources and should be an explicit
operator decision.

## Routing and task layout

`ecs-fargate.yaml` creates one public HTTP Application Load Balancer. It routes:

| Path | Module |
| --- | --- |
| `/` | Shared dashboard |
| `/inventory/` | Inventory |
| `/orders/` | Order management |
| `/warehouse/` | Warehouse |
| `/transportation/` | Transportation |

The twelve existing ECR images run in five Fargate services/task definitions:
one shared frontend task plus one task per module. Each module's frontend,
backend, and database containers share that task's `awsvpc` network namespace
and communicate over `127.0.0.1`. This keeps duplicate ports in different
modules isolated. Only frontend ports are allowed from the ALB security group;
database and backend ports are not allowed through the task security group.

Container listeners and ALB health checks are configured as follows:

| Task/container | Listener | ALB target port | ALB health path |
| --- | ---: | ---: | --- |
| Shared Nginx frontend | 80 | 80 | `/` |
| Inventory database API | 5002 | — | ECS check: `/` (HTTP 2xx) |
| Inventory backend API | 5001 | — | ECS check: `/health` |
| Inventory Nginx frontend | 80 | 80 | `/inventory/healthz` |
| Orders database API | 5002 | — | ECS check: `/` (HTTP 2xx) |
| Orders backend API | 5001 | — | ECS check: `/health` |
| Orders Nginx frontend | 80 | 80 | `/orders/healthz` |
| Warehouse database API | 5002 | — | ECS check: `/health` |
| Warehouse backend API | 5001 | — | ECS check: `/health` |
| Warehouse Flask frontend | 5000 | 5000 | `/warehouse/health` |
| Transportation backend API | 5004 | — | ECS check: `/health` |
| Transportation Nginx frontend | 80 | 80 | `/transportation/healthz` |

The Inventory and Orders database containers return HTTP 200 from their Flask
root routes. Their ECS checks assert a 2xx response. The Inventory and Orders
frontend checks are static Nginx 200 responses; the Warehouse check is handled
by its prefix-aware Flask middleware.

Tasks use public subnets and public IP assignment to avoid a NAT Gateway charge.
Their security group accepts inbound frontend traffic only from the ALB, so
clients must use the ALB URL. For stronger isolation, use private task subnets
and the required VPC endpoints or a NAT Gateway instead.

The ECS service names use an `integrated-` prefix. The already-running
`shared-frontend-service` is left untouched; a new integrated dashboard service
is created behind the ALB. After verifying the ALB URL, the old standalone
service can be stopped separately if desired.

## Databases and costs

All four databases are SQLite files. The stack uses one encrypted EFS file
system with separate access points for Inventory, Orders, Warehouse, and
Transportation. Each access point maps to a separate directory, forces UID/GID
1000, and creates that directory with mode `0750`. Each task role is limited to
mount/write through its own access point; the containers do not need EFS root
access. The mounts align with the database paths: Inventory and Orders mount at
`/app/data`, Warehouse at `/data`, and Transportation at `/app/data`. Seed
initialization uses `CREATE IF NOT EXISTS`/`INSERT OR IGNORE` or seeds only an
empty database, so restarts do not intentionally erase existing rows. SQLite
on EFS is for a single-task demonstration, not a production database design.
Automated EFS backups are disabled in this temporary stack; export data that
must be retained before deleting the filesystem.

Inventory, Orders, and Warehouse task definitions allocate 1 vCPU and 2 GiB
RAM each for their three containers; Transportation allocates 0.5 vCPU and
1 GiB for its two containers. These are shared task budgets, not per-container
reservations. They provide headroom for Python startup and AI-related
dependencies, but peak usage has not been measured; inspect ECS CPU/memory
metrics during the demonstration and increase allocations if tasks approach
their limits. Every task definition explicitly selects Linux `X86_64`, and the
image-publish script rejects anything other than `linux/amd64`.

The stack also creates an ALB, five Fargate services, log group, security
groups, EFS mount targets/access points, and a task IAM role. The template
retains logs for seven days and configures one task per service. To avoid
concurrent writers on the SQLite files, a service deployment replaces its
single task with a short interruption rather than running two copies at once.
The ALB, EFS,
and running Fargate tasks are billable. Stop/delete the demo resources after
use; preserve or deliberately remove the retained EFS file system as required.
The listener is HTTP-only because no domain or certificate ARN was provided.
Use ACM and an HTTPS listener before treating the site as production-ready.

## AI and optional services

No Ollama service is included in the twelve existing images. AI mode remains
available in the applications, but requests require a separately deployed,
reachable Ollama runtime. The CloudFormation parameters
`OllamaOpenAIBaseUrl` and `OllamaGenerateBaseUrl` are empty by default; model
requests will fail clearly until reachable endpoints are configured. Do not
set them to `localhost` or `host.docker.internal`.

MCP and RAG are explicitly disabled in the AWS task definitions. Their UI
controls remain visible and report that they are disabled. The locally used
RAG service is not one of the twelve published ECR images and is not deployed
by this template. The local Compose configuration retains its existing
development endpoints and feature defaults.

## First deployment

Prerequisites:

- AWS CLI configured with the named `advanced-software` profile (never use the
  root user).
- Docker and Docker Compose installed.
- The existing `advanced-software-cluster` and all twelve ECR repositories
  under `advanced-software/`.
- Two public subnet IDs in the same VPC, in different Availability Zones.
- The ARN of an ECS task execution role trusted by `ecs-tasks.amazonaws.com`
  with ECR image-pull and CloudWatch Logs permissions (normally
  `ecsTaskExecutionRole` with `AmazonECSTaskExecutionRolePolicy` attached).

The execution role needs `ecr:GetAuthorizationToken` on `*`, ECR image-pull
actions (`ecr:BatchCheckLayerAvailability`, `ecr:GetDownloadUrlForLayer`, and
`ecr:BatchGetImage`) on the twelve `advanced-software/*` repositories, and
`logs:CreateLogStream`/`logs:PutLogEvents` on the stack's log group. The stack
creates the log group itself, so the execution role does not need
`logs:CreateLogGroup`. This is separate from the per-task roles that authorize
EFS access.

Before deployment, verify the actual external role (this project cannot
validate its attached policies without querying the AWS account):

```bash
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query 'Role.AssumeRolePolicyDocument' \
  --output json \
  --profile advanced-software
aws iam list-attached-role-policies \
  --role-name ecsTaskExecutionRole \
  --query 'AttachedPolicies[].PolicyArn' \
  --output table \
  --profile advanced-software
aws iam simulate-principal-policy \
  --policy-source-arn "$TASK_EXECUTION_ROLE_ARN" \
  --action-names ecr:GetAuthorizationToken \
  --resource-arns '*' \
  --query 'EvaluationResults[].{Action:EvalActionName,Decision:EvalDecision}' \
  --output table \
  --profile advanced-software
```

Also simulate the three ECR image-pull actions against
`arn:aws:ecr:ap-southeast-2:364546113688:repository/advanced-software/*`,
and the two log actions against
`arn:aws:logs:ap-southeast-2:364546113688:log-group:/ecs/advanced-software/integrated:*`.
All required actions must show `allowed`; a role name or ARN alone does not
prove the permissions are present.

Read-only discovery examples (replace the VPC selector with the existing
network's VPC ID):

```bash
aws sts get-caller-identity --profile advanced-software
aws ecs describe-clusters \
  --clusters advanced-software-cluster \
  --region ap-southeast-2 \
  --profile advanced-software
aws iam get-role \
  --role-name ecsTaskExecutionRole \
  --query 'Role.Arn' \
  --output text \
  --profile advanced-software
aws ec2 describe-subnets \
  --filters Name=vpc-id,Values="$VPC_ID" \
  --query 'Subnets[].{Subnet:SubnetId,AZ:AvailabilityZone,PublicIP:MapPublicIpOnLaunch}' \
  --output table \
  --region ap-southeast-2 \
  --profile advanced-software
```

After reviewing the template and cost, explicitly set the required values and
run the stack deployment:

```bash
export VPC_ID="vpc-..."
export PUBLIC_SUBNET_IDS="subnet-...,subnet-..."
export TASK_EXECUTION_ROLE_ARN="arn:aws:iam::364546113688:role/ecsTaskExecutionRole"

bash scripts/deploy-ecs.sh --deploy-stack
```

The script creates a unique timestamp/commit image tag and refuses to overwrite
an existing tag. For image-only runs, it checks each resolved Docker build
context, Dockerfile, root Compose file, and owning module Compose file to
select images to rebuild. The shared dashboard now uses the narrow `shared/`
build context. For `--deploy-stack` and `--update-existing`, the script rebuilds and
pushes all twelve images under the new tag. It never copies mutable `latest`
manifests into a new deployment tag. Every built image is checked for
`linux/amd64` before push, matching the task definitions' Linux `X86_64`
runtime platform. ECR repositories are not auto-created.

Use `--plan` to inspect the selected image set without invoking AWS, building,
or pushing:

```bash
bash scripts/deploy-ecs.sh --plan --since HEAD
``` Supply
reachable Ollama URLs at deployment time if available:

```bash
OLLAMA_OPENAI_BASE_URL="http://<reachable-ollama-host>:11434/v1" \
OLLAMA_GENERATE_BASE_URL="http://<reachable-ollama-host>:11434" \
bash scripts/deploy-ecs.sh --deploy-stack
```

To build/push only images affected by changes without creating or changing ECS
resources:

```bash
bash scripts/deploy-ecs.sh
```

To update only explicitly named, already-existing ECS services (for example,
after a successful stack deployment):

```bash
bash scripts/deploy-ecs.sh --update-existing \
  --services integrated-inventory-service,integrated-order-service
```

This option registers task-definition revisions and forces only those selected
services to redeploy. The old standalone `shared-frontend-service` is not
selected implicitly; only name a service if you deliberately intend to update
it. A name must match exactly what ECS returns for the cluster.

## Deleting the demonstration stack

Deleting the CloudFormation stack removes the ALB, listeners/rules, ECS
services/task definitions, mount targets, access points, task roles, security
groups, and log group. The encrypted EFS file system has both
`DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain`; stack deletion
deliberately preserves it and its database files, so it remains billable.
Record the `EfsFileSystemId` stack output before deleting the stack.

After the demonstration, delete the stack and then deliberately delete the
retained EFS filesystem if the data is no longer needed:

```bash
aws cloudformation delete-stack \
  --stack-name advanced-software-integrated \
  --region ap-southeast-2 \
  --profile advanced-software
aws cloudformation wait stack-delete-complete \
  --stack-name advanced-software-integrated \
  --region ap-southeast-2 \
  --profile advanced-software

# Confirm this is the recorded ID and stack deletion removed its mount targets.
aws efs describe-mount-targets \
  --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --region ap-southeast-2 \
  --profile advanced-software
aws efs delete-file-system \
  --file-system-id "$EFS_FILE_SYSTEM_ID" \
  --region ap-southeast-2 \
  --profile advanced-software
```

Only run `delete-file-system` after confirming the ID belongs to this
demonstration and the data can be discarded. EFS refuses deletion while mount
targets remain. Verify the file system is gone in the EFS console or with
`aws efs describe-file-systems`; deleting the ECS stack alone does not stop
EFS charges.

## Validation

Local Compose behavior and cloud path routing can be checked separately.
These local commands do not prove AWS deployment:

```bash
docker compose up -d --build
docker compose ps
curl -fsS http://localhost:8080/ -o /dev/null
curl -fsS http://localhost:8080/runtime-config.js
curl -fsS http://localhost:8081/ -o /dev/null
curl -fsS http://localhost:8081/api/products -o /dev/null
curl -fsS http://localhost:8082/ -o /dev/null
curl -fsS http://localhost:8082/api/orders -o /dev/null
curl -fsS -L http://localhost:5000/ -o /dev/null
curl -fsS http://localhost:5000/health
curl -fsS http://localhost:3004/ -o /dev/null
curl -fsS http://localhost:3004/transportation/api/transportation/htmx/shipments -o /dev/null
```

After the CloudFormation stack reaches `CREATE_COMPLETE` or
`UPDATE_COMPLETE`, copy its `ApplicationUrl` output into `BASE`:

```bash
export BASE="http://<ApplicationLoadBalancer-DNS>"
curl -fsS "$BASE/" -o /dev/null
curl -fsS "$BASE/runtime-config.js"
curl -fsS "$BASE/inventory/" -o /dev/null
curl -fsS "$BASE/inventory/api/products" -o /dev/null
curl -fsS "$BASE/orders/" -o /dev/null
curl -fsS "$BASE/orders/api/orders" -o /dev/null
curl -fsS -L "$BASE/warehouse/" -o /dev/null
curl -fsS "$BASE/warehouse/health"
curl -fsS "$BASE/transportation/" -o /dev/null
curl -fsS "$BASE/transportation/api/transportation/htmx/shipments" -o /dev/null
```

Each `curl -f` should exit zero. The JSON endpoints should return data, the
frontend requests should return HTML, and the health endpoint should return
`{"status":"ok",...}`. In a browser, open each module and verify its list loads,
then inspect DevTools Network: requests should remain on the same ALB host and
use the module path prefixes. Target health and application logs are available
in the ECS and CloudWatch consoles. Stop local Compose before this AWS check to
ensure the AWS app is not accidentally depending on the local machine.
