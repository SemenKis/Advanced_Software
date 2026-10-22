#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REGION="ap-southeast-2"
PROFILE="advanced-software"
ACCOUNT="364546113688"
CLUSTER="advanced-software-cluster"
REPOSITORY_PREFIX="advanced-software"
STACK_NAME="advanced-software-integrated"
TEMPLATE="$ROOT_DIR/cloud/ecs-fargate.yaml"

DEPLOY_STACK=false
UPDATE_EXISTING=false
SINCE_REF=""
IMAGE_TAG=""
SELECTED_ECS_SERVICES=""
PLAN_ONLY=false

ALL_SERVICES=(
  shared-frontend frontend-service inventory-service database-service
  order-frontend order-backend order-database
  warehouse-frontend warehouse-backend warehouse-database
  frontend backend
)

usage() {
  cat <<'EOF'
Usage: scripts/deploy-ecs.sh [options]

Builds images affected by changes in their resolved Docker build contexts.
Deployment operations build all twelve images so a version tag never inherits
an image from a mutable latest tag.

Options:
  --since REF          Compare changes against REF (default: most recent Git tag)
  --image-tag TAG      Use an explicit immutable image tag
  --deploy-stack       Create/update the integrated ALB, EFS, and ECS services
  --update-existing    Update explicitly selected ECS services
  --services NAMES     Comma-separated service names; required with
                       --update-existing (for example, integrated-order-service)
  --plan               Show the selected images without calling AWS or building
  -h, --help           Show this help

For a first stack deployment, set VPC_ID, PUBLIC_SUBNET_IDS (two subnet IDs
separated by a comma), and TASK_EXECUTION_ROLE_ARN. Ollama is optional:
OLLAMA_OPENAI_BASE_URL and OLLAMA_GENERATE_BASE_URL must point to a deployed,
reachable Ollama service if supplied.
EOF
}

while (($#)); do
  case "$1" in
    --since)
      SINCE_REF="${2:?--since requires a Git reference}"
      shift 2
      ;;
    --image-tag)
      IMAGE_TAG="${2:?--image-tag requires a tag}"
      shift 2
      ;;
    --deploy-stack)
      DEPLOY_STACK=true
      shift
      ;;
    --update-existing)
      UPDATE_EXISTING=true
      shift
      ;;
    --services)
      SELECTED_ECS_SERVICES="${2:?--services requires a comma-separated service list}"
      shift 2
      ;;
    --plan)
      PLAN_ONLY=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$UPDATE_EXISTING" == true && -z "$SELECTED_ECS_SERVICES" ]]; then
  echo "--update-existing requires --services with one or more exact ECS service names." >&2
  exit 2
fi
if [[ "$UPDATE_EXISTING" != true && -n "$SELECTED_ECS_SERVICES" ]]; then
  echo "--services can only be used with --update-existing." >&2
  exit 2
fi
if [[ "$DEPLOY_STACK" == true && "$UPDATE_EXISTING" == true ]]; then
  echo "Choose either --deploy-stack or --update-existing, not both." >&2
  exit 2
fi
if [[ "$UPDATE_EXISTING" == true ]]; then
  ALLOWED_ECS_SERVICES=(
    integrated-shared-frontend-service integrated-inventory-service
    integrated-order-service integrated-warehouse-service
    integrated-transportation-service shared-frontend-service
  )
  IFS=',' read -r -a REQUESTED_SERVICES <<< "$SELECTED_ECS_SERVICES"
  if ((${#REQUESTED_SERVICES[@]} == 0)); then
    echo "Select at least one ECS service with --services." >&2
    exit 2
  fi
  declare -A REQUESTED=()
  for SERVICE_NAME in "${REQUESTED_SERVICES[@]}"; do
    if [[ -z "$SERVICE_NAME" || "$SERVICE_NAME" == *[[:space:]]* ]]; then
      echo "Invalid ECS service name in --services: '$SERVICE_NAME'." >&2
      exit 2
    fi
    SERVICE_ALLOWED=false
    for ALLOWED_SERVICE in "${ALLOWED_ECS_SERVICES[@]}"; do
      if [[ "$SERVICE_NAME" == "$ALLOWED_SERVICE" ]]; then
        SERVICE_ALLOWED=true
        break
      fi
    done
    if [[ "$SERVICE_ALLOWED" != true ]]; then
      echo "Unsupported ECS service in --services: $SERVICE_NAME." >&2
      echo "Choose an integrated service name; select shared-frontend-service only deliberately." >&2
      exit 2
    fi
    if [[ -n "${REQUESTED[$SERVICE_NAME]:-}" ]]; then
      echo "Duplicate ECS service in --services: $SERVICE_NAME." >&2
      exit 2
    fi
    REQUESTED["$SERVICE_NAME"]=1
  done
fi

for command in aws docker git python3; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Required command not found: $command" >&2
    exit 1
  fi
done

cd "$ROOT_DIR"

if [[ -z "$IMAGE_TAG" ]]; then
  SHORT_SHA="$(git rev-parse --short HEAD)"
  IMAGE_TAG="$(date -u +%Y%m%dT%H%M%S%N)-${SHORT_SHA}"
  if [[ -n "$(git status --porcelain)" ]]; then
    IMAGE_TAG="${IMAGE_TAG}-worktree"
  fi
fi
if [[ ! "$IMAGE_TAG" =~ ^[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}$ ]]; then
  echo "Invalid Docker/ECR image tag: $IMAGE_TAG" >&2
  exit 2
fi

if [[ -z "$SINCE_REF" ]]; then
  SINCE_REF="$(git describe --tags --abbrev=0 2>/dev/null || true)"
fi

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
CONFIG_JSON="$(mktemp)"
CHANGED_PATHS="$(mktemp)"
SELECTED_IMAGES="$(mktemp)"
TASK_DEFINITION_JSON="$(mktemp)"
REGISTERED_TASK_DEFINITION="$(mktemp)"
trap 'rm -f "$CONFIG_JSON" "$CHANGED_PATHS" "$SELECTED_IMAGES" "$TASK_DEFINITION_JSON" "$REGISTERED_TASK_DEFINITION"' EXIT

docker compose config --format json > "$CONFIG_JSON"

if [[ -n "$SINCE_REF" ]]; then
  git diff --no-renames --name-only "$SINCE_REF" -- > "$CHANGED_PATHS"
  git ls-files --others --exclude-standard >> "$CHANGED_PATHS"
  git diff --cached --no-renames --name-only >> "$CHANGED_PATHS"
  echo "Selecting images changed since $SINCE_REF."
else
  echo "No Git tag/reference found; selecting all twelve application images."
fi

if [[ "$DEPLOY_STACK" == true || "$UPDATE_EXISTING" == true ]]; then
  SERVICES=("${ALL_SERVICES[@]}")
  echo "A deployment was requested; building all twelve images for this new version tag."
else
  python3 - "$CONFIG_JSON" "$CHANGED_PATHS" "$SINCE_REF" "$ROOT_DIR" > "$SELECTED_IMAGES" <<'PY'
import json
import pathlib
import sys

config_path, changed_path, since_ref, root_dir = sys.argv[1:]
root = pathlib.Path(root_dir).resolve()
with open(config_path, encoding="utf-8") as stream:
    compose = json.load(stream)

services = (
    "shared-frontend", "frontend-service", "inventory-service", "database-service",
    "order-frontend", "order-backend", "order-database",
    "warehouse-frontend", "warehouse-backend", "warehouse-database",
    "frontend", "backend",
)

def is_within(path, directory):
    try:
        path.relative_to(directory)
        return True
    except ValueError:
        return False

if since_ref:
    with open(changed_path, encoding="utf-8") as stream:
        changed = {
            (root / line.strip()).resolve()
            for line in stream
            if line.strip()
        }
else:
    changed = None

compose_services = {
    "docker-compose.yml": set(services),
    "student-1-bea/docker-compose.yml": {
        "order-frontend", "order-backend", "order-database",
    },
    "student-2-yuting/docker-compose.yml": {
        "warehouse-frontend", "warehouse-backend", "warehouse-database",
    },
    "student-3-lois/docker-compose.yml": {
        "frontend-service", "inventory-service", "database-service",
    },
    "student-4-sam/docker-compose.yml": {"frontend", "backend"},
}
compose_changes = {
    path for path in changed or ()
    if is_within(path, root)
    and str(path.relative_to(root)) in compose_services
}

for service in services:
    if service not in compose["services"]:
        raise SystemExit(f"Compose service missing: {service}")
    build = compose["services"][service].get("build")
    if not isinstance(build, dict) or "context" not in build:
        raise SystemExit(f"Compose service has no resolved build context: {service}")
    context = pathlib.Path(build["context"]).resolve()
    dockerfile = pathlib.Path(build.get("dockerfile", "Dockerfile"))
    if not dockerfile.is_absolute():
        dockerfile = context / dockerfile
    if changed is None or any(
        is_within(path, context) or path == dockerfile.resolve()
        for path in changed
    ) or any(service in compose_services[str(path.relative_to(root))] for path in compose_changes):
        print(service)
PY
  mapfile -t SERVICES < "$SELECTED_IMAGES"
  if ((${#SERVICES[@]} == 0)); then
    echo "No application image build contexts changed; no images or AWS resources were modified."
    exit 0
  fi
fi

echo "Image tag: $IMAGE_TAG"
echo "Changed images: ${SERVICES[*]:-(none)}"
if [[ "$UPDATE_EXISTING" == true ]]; then
  echo "ECS services selected for update: $SELECTED_ECS_SERVICES"
fi
if [[ "$DEPLOY_STACK" == true ]]; then
  echo "CloudFormation stack selected for deployment: $STACK_NAME"
fi
if [[ "$PLAN_ONLY" == true ]]; then
  echo "Plan only: no AWS commands, Docker builds, image pushes, or service updates were run."
  exit 0
fi

if [[ "$DEPLOY_STACK" == true ]]; then
  : "${VPC_ID:?Set VPC_ID before creating/updating the CloudFormation stack.}"
  : "${PUBLIC_SUBNET_IDS:?Set PUBLIC_SUBNET_IDS to two public subnet IDs.}"
  : "${TASK_EXECUTION_ROLE_ARN:?Set TASK_EXECUTION_ROLE_ARN to the ECS task execution role ARN.}"
fi

aws sts get-caller-identity --profile "$PROFILE" --region "$REGION" >/dev/null
aws ecr get-login-password --region "$REGION" --profile "$PROFILE" |
  docker login --username AWS --password-stdin "$REGISTRY" >/dev/null

for SERVICE in "${ALL_SERVICES[@]}"; do
  REPOSITORY="${REPOSITORY_PREFIX}/${SERVICE}"
  if ! aws ecr describe-repositories \
    --repository-names "$REPOSITORY" \
    --region "$REGION" \
    --profile "$PROFILE" >/dev/null; then
    echo "ECR repository is missing: $REPOSITORY (create it explicitly before deploying)." >&2
    exit 1
  fi
  EXISTING_TAG="$(
    aws ecr list-images \
      --repository-name "$REPOSITORY" \
      --filter tagStatus=TAGGED \
      --query "imageIds[?imageTag=='${IMAGE_TAG}'].imageTag | [0]" \
      --output text \
      --region "$REGION" \
      --profile "$PROFILE"
  )"
  if [[ "$EXISTING_TAG" != "None" && -n "$EXISTING_TAG" ]]; then
    echo "Refusing to overwrite existing ECR tag $REPOSITORY:$IMAGE_TAG." >&2
    echo "Choose a new --image-tag and retry." >&2
    exit 1
  fi
done

declare -A BUILT=()

for SERVICE in "${SERVICES[@]}"; do
  REPOSITORY="${REPOSITORY_PREFIX}/${SERVICE}"

  echo "Building $SERVICE"
  docker compose build "$SERVICE"

  # Resolve the explicit image name or Docker Compose's generated name.
  IMAGE_NAME="$(python3 - "$CONFIG_JSON" "$SERVICE" <<'PYIMAGE'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as stream:
    config = json.load(stream)

service = sys.argv[2]
image = config["services"][service].get("image")
if not image:
    image = f"{config['name']}-{service}:latest"
print(image)
PYIMAGE
)"

  # Verify that the image exists
  if ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Could not find the built image: $IMAGE_NAME" >&2
    exit 1
  fi

  # Verify the image architecture
  IMAGE_PLATFORM="$(docker image inspect "$IMAGE_NAME" --format '{{.Os}}/{{.Architecture}}')"

  if [[ "$IMAGE_PLATFORM" != "linux/amd64" ]]; then
    echo "Built $SERVICE for $IMAGE_PLATFORM; ECS Fargate requires linux/amd64." >&2
    exit 1
  fi

  # Tag and push the image to AWS ECR
  REMOTE_IMAGE="${REGISTRY}/${REPOSITORY}:${IMAGE_TAG}"

  docker tag "$IMAGE_NAME" "$REMOTE_IMAGE"
  docker push "$REMOTE_IMAGE"

  BUILT["$SERVICE"]=1
done

if [[ "$DEPLOY_STACK" == true || "$UPDATE_EXISTING" == true ]] \
  && ((${#BUILT[@]} != ${#ALL_SERVICES[@]})); then
  echo "Internal error: deployment tag does not contain all twelve freshly built images." >&2
  exit 1
fi

if [[ "$DEPLOY_STACK" == true ]]; then
  echo "Deploying CloudFormation stack $STACK_NAME (this creates billable ALB, ECS, and EFS resources)."
  aws cloudformation deploy \
    --template-file "$TEMPLATE" \
    --stack-name "$STACK_NAME" \
    --region "$REGION" \
    --profile "$PROFILE" \
    --capabilities CAPABILITY_IAM \
    --parameter-overrides \
      ClusterName="$CLUSTER" \
      ImageTag="$IMAGE_TAG" \
      VpcId="$VPC_ID" \
      PublicSubnets="$PUBLIC_SUBNET_IDS" \
      TaskExecutionRoleArn="$TASK_EXECUTION_ROLE_ARN" \
      OllamaOpenAIBaseUrl="${OLLAMA_OPENAI_BASE_URL:-}" \
      OllamaGenerateBaseUrl="${OLLAMA_GENERATE_BASE_URL:-}"

  aws ecs wait services-stable \
    --cluster "$CLUSTER" \
    --services \
      integrated-shared-frontend-service \
      integrated-inventory-service \
      integrated-order-service \
      integrated-warehouse-service \
      integrated-transportation-service \
    --region "$REGION" \
    --profile "$PROFILE"

  aws cloudformation describe-stacks \
    --stack-name "$STACK_NAME" \
    --query 'Stacks[0].Outputs' \
    --output table \
    --region "$REGION" \
    --profile "$PROFILE"
fi

if [[ "$UPDATE_EXISTING" == true ]]; then
  SERVICE_ARN_OUTPUT="$(
    aws ecs list-services \
      --cluster "$CLUSTER" \
      --query 'serviceArns[]' \
      --output text \
      --region "$REGION" \
      --profile "$PROFILE"
  )"
  mapfile -t SERVICE_ARNS < <(
    printf '%s\n' "$SERVICE_ARN_OUTPUT" |
      tr '\t' '\n' |
      sed '/^$/d;/^None$/d'
  )

  SELECTED_SERVICE_ARNS=()
  for SERVICE_ARN in "${SERVICE_ARNS[@]}"; do
    SERVICE_NAME="${SERVICE_ARN##*/}"
    if [[ -n "${REQUESTED[$SERVICE_NAME]:-}" ]]; then
      SELECTED_SERVICE_ARNS+=("$SERVICE_ARN")
      unset 'REQUESTED[$SERVICE_NAME]'
    fi
  done
  if ((${#REQUESTED[@]} > 0)); then
    printf 'Selected ECS service(s) not found in cluster %s: %s\n' \
      "$CLUSTER" "${!REQUESTED[*]}" >&2
    exit 1
  fi
  if ((${#SELECTED_SERVICE_ARNS[@]} == 0)); then
    echo "No ECS services selected for update." >&2
    exit 1
  fi

  UPDATED_SERVICE_COUNT=0
  for SERVICE_ARN in "${SELECTED_SERVICE_ARNS[@]}"; do
    TASK_DEFINITION_ARN="$(
      aws ecs describe-services \
        --cluster "$CLUSTER" \
        --services "$SERVICE_ARN" \
        --query 'services[0].taskDefinition' \
        --output text \
        --region "$REGION" \
        --profile "$PROFILE"
    )"

    aws ecs describe-task-definition \
      --task-definition "$TASK_DEFINITION_ARN" \
      --query 'taskDefinition' \
      --output json \
      --region "$REGION" \
      --profile "$PROFILE" > "$TASK_DEFINITION_JSON"

    UPDATE_STATUS="$(python3 - "$TASK_DEFINITION_JSON" "$REGISTERED_TASK_DEFINITION" "$REGISTRY" "$REPOSITORY_PREFIX" "$IMAGE_TAG" <<'PY'
import json
import sys

source, target, registry, prefix, tag = sys.argv[1:]
with open(source, encoding="utf-8") as stream:
    task = json.load(stream)

for key in (
    "taskDefinitionArn", "revision", "status", "requiresAttributes",
    "compatibilities", "registeredAt", "registeredBy",
):
    task.pop(key, None)

prefix = f"{registry}/{prefix}/"
updated = False
for container in task.get("containerDefinitions", []):
    image = container.get("image", "")
    if image.startswith(prefix):
        repository = image[len(prefix):].split(":", 1)[0]
        container["image"] = f"{prefix}{repository}:{tag}"
        updated = True

if updated:
    with open(target, "w", encoding="utf-8") as stream:
        json.dump(task, stream)
    print("updated")
else:
    print("unchanged")
PY
)"

    if [[ "$UPDATE_STATUS" != "updated" ]]; then
      echo "Skipping $SERVICE_ARN: its task definition has no advanced-software ECR images."
      continue
    fi

    NEW_TASK_DEFINITION="$(
      aws ecs register-task-definition \
        --cli-input-json "file://$REGISTERED_TASK_DEFINITION" \
        --query 'taskDefinition.taskDefinitionArn' \
        --output text \
        --region "$REGION" \
        --profile "$PROFILE"
    )"

    aws ecs update-service \
      --cluster "$CLUSTER" \
      --service "$SERVICE_ARN" \
      --task-definition "$NEW_TASK_DEFINITION" \
      --force-new-deployment \
      --region "$REGION" \
      --profile "$PROFILE" >/dev/null
    echo "Waiting for $SERVICE_ARN to become stable."
    aws ecs wait services-stable \
      --cluster "$CLUSTER" \
      --services "$SERVICE_ARN" \
      --region "$REGION" \
      --profile "$PROFILE"
    UPDATED_SERVICE_COUNT=$((UPDATED_SERVICE_COUNT + 1))
  done
  echo "Updated $UPDATED_SERVICE_COUNT existing ECS service(s)."
fi

echo "Images are available in ECR with tag $IMAGE_TAG."
if [[ "$DEPLOY_STACK" != true && "$UPDATE_EXISTING" != true ]]; then
  echo "No ECS service was modified. Use --deploy-stack for the integrated stack or --update-existing for matching existing services."
fi