#!/usr/bin/env bash
set -euo pipefail

#!/usr/bin/env bash
set -euo pipefail

# ==========================================
# AWS Configuration
# ==========================================

REGION="ap-southeast-2"
PROFILE="advanced-software"
ACCOUNT="364546113688"

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
PREFIX="advanced-software"

# ==========================================
# Verify AWS Authentication
# ==========================================

echo "Checking AWS authentication..."

aws sts get-caller-identity \
  --profile "$PROFILE" > /dev/null

echo "AWS authentication successful."

# ==========================================
# Login to Amazon ECR
# ==========================================

echo "Logging into Amazon ECR..."

aws ecr get-login-password \
  --region "$REGION" \
  --profile "$PROFILE" |
  docker login \
    --username AWS \
    --password-stdin "$REGISTRY"

# ==========================================
# Read Docker Compose Configuration
# ==========================================

echo "Reading Docker Compose configuration..."

COMPOSE_JSON=$(mktemp)
trap 'rm -f "$COMPOSE_JSON"' EXIT

docker compose config --format json > "$COMPOSE_JSON"

mapfile -t SERVICES < <(
  python3 - "$COMPOSE_JSON" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    config = json.load(f)

for name, service in config["services"].items():
    if service.get("build"):
        print(name)
PY
)

echo "Found ${#SERVICES[@]} services."

# ==========================================
# Build and Push All Images
# ==========================================

for SERVICE in "${SERVICES[@]}"; do

  REPO="${PREFIX}/${SERVICE}"
  LOCAL_IMAGE="warehouse-app-${SERVICE}:latest"
  REMOTE_IMAGE="${REGISTRY}/${REPO}:latest"

  echo ""
  echo "======================================"
  echo "Processing service: $SERVICE"
  echo "======================================"

  # --------------------------------------
  # Create ECR repository if missing
  # --------------------------------------

  if aws ecr describe-repositories \
    --repository-names "$REPO" \
    --region "$REGION" \
    --profile "$PROFILE" > /dev/null 2>&1; then

    echo "Repository already exists: $REPO"

  else

    echo "Creating ECR repository: $REPO"

    aws ecr create-repository \
      --repository-name "$REPO" \
      --region "$REGION" \
      --profile "$PROFILE" > /dev/null

  fi

  # --------------------------------------
  # Build Docker image
  # --------------------------------------

  echo "Building Docker image: $SERVICE"

  docker compose build "$SERVICE"

  # --------------------------------------
  # Verify local image
  # --------------------------------------

  echo "Verifying image: $LOCAL_IMAGE"

  docker image inspect "$LOCAL_IMAGE" > /dev/null

  # --------------------------------------
  # Tag image for ECR
  # --------------------------------------

  echo "Tagging image..."

  docker tag \
    "$LOCAL_IMAGE" \
    "$REMOTE_IMAGE"

  # --------------------------------------
  # Push image to ECR
  # --------------------------------------

  echo "Pushing image to ECR..."

  docker push "$REMOTE_IMAGE"

  echo "Successfully pushed: $REMOTE_IMAGE"

done

# ==========================================
# Completed
# ==========================================

echo ""
echo "======================================"
echo "All ${#SERVICES[@]} images uploaded!"
echo "======================================"

echo ""
echo "ECR Registry: $REGISTRY"
echo "AWS Region:   $REGION"
echo ""
echo "Next step: Deploy containers to ECS Fargate."

REGION="ap-southeast-2"
PROFILE="advanced-software"
ACCOUNT="364546113688"
REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
PREFIX="advanced-software"

echo "Checking AWS authentication..."
aws sts get-caller-identity --profile "$PROFILE" > /dev/null

echo "Logging into Amazon ECR..."
aws ecr get-login-password \
  --region "$REGION" \
  --profile "$PROFILE" |
  docker login --username AWS --password-stdin "$REGISTRY"

echo "Reading Docker Compose configuration..."
docker compose config --format json > /tmp/advanced-software-compose.json

mapfile -t SERVICES < <(
  python3 -c '
import json
with open("/tmp/advanced-software-compose.json") as f:
    config = json.load(f)
for name, service in config["services"].items():
    if service.get("build"):

#!/usr/bin/env bash
set -euo pipefail

# ==========================================
# AWS Configuration
# ==========================================

REGION="ap-southeast-2"
PROFILE="advanced-software"
ACCOUNT="364546113688"

REGISTRY="${ACCOUNT}.dkr.ecr.${REGION}.amazonaws.com"
PREFIX="advanced-software"

# ==========================================
# Verify AWS Authentication
# ==========================================

echo "Checking AWS authentication..."

aws sts get-caller-identity \
  --profile "$PROFILE" > /dev/null

echo "AWS authentication successful."

# ==========================================
# Login to Amazon ECR
# ==========================================

echo "Logging into Amazon ECR..."

aws ecr get-login-password \
  --region "$REGION" \
  --profile "$PROFILE" |
  docker login \
    --username AWS \
    --password-stdin "$REGISTRY"

# ==========================================
# Read Docker Compose Configuration
# ==========================================

echo "Reading Docker Compose configuration..."

COMPOSE_JSON=$(mktemp)
trap 'rm -f "$COMPOSE_JSON"' EXIT

docker compose config --format json > "$COMPOSE_JSON"

mapfile -t SERVICES < <(
  python3 - "$COMPOSE_JSON" <<'PY'
import json
import sys

with open(sys.argv[1]) as f:
    config = json.load(f)

for name, service in config["services"].items():
    if service.get("build"):
        print(name)
PY
)

echo "Found ${#SERVICES[@]} services."

# ==========================================
# Build and Push All Images
# ==========================================

for SERVICE in "${SERVICES[@]}"; do

  REPO="${PREFIX}/${SERVICE}"
  LOCAL_IMAGE="warehouse-app-${SERVICE}:latest"
  REMOTE_IMAGE="${REGISTRY}/${REPO}:latest"

  echo ""
  echo "======================================"
  echo "Processing service: $SERVICE"
  echo "======================================"

  # --------------------------------------
  # Create ECR repository if missing
  # --------------------------------------

  if aws ecr describe-repositories \
    --repository-names "$REPO" \
    --region "$REGION" \
    --profile "$PROFILE" > /dev/null 2>&1; then

    echo "Repository already exists: $REPO"

  else

    echo "Creating ECR repository: $REPO"

    aws ecr create-repository \
      --repository-name "$REPO" \
      --region "$REGION" \
      --profile "$PROFILE" > /dev/null

  fi

  # --------------------------------------
  # Build Docker image
  # --------------------------------------

  echo "Building Docker image: $SERVICE"

  docker compose build "$SERVICE"

  # --------------------------------------
  # Verify local image
  # --------------------------------------

  echo "Verifying image: $LOCAL_IMAGE"

  docker image inspect "$LOCAL_IMAGE" > /dev/null

  # --------------------------------------
  # Tag image for ECR
  # --------------------------------------

  echo "Tagging image..."

  docker tag \
    "$LOCAL_IMAGE" \
    "$REMOTE_IMAGE"

  # --------------------------------------
  # Push image to ECR
  # --------------------------------------

  echo "Pushing image to ECR..."

  docker push "$REMOTE_IMAGE"

  echo "Successfully pushed: $REMOTE_IMAGE"

done

# ==========================================
# Completed
# ==========================================

echo ""
echo "======================================"
echo "All ${#SERVICES[@]} images uploaded!"
echo "======================================"

echo ""
echo "ECR Registry: $REGISTRY"
echo "AWS Region:   $REGION"
echo ""
echo "Next step: Deploy containers to ECS Fargate."
        print(name)
'
)

for SERVICE in "${SERVICES[@]}"; do
  REPO="${PREFIX}/${SERVICE}"
  REMOTE_IMAGE="${REGISTRY}/${REPO}:latest"

  echo "======================================"
  echo "Pro
