#!/usr/bin/env bash
set -euo pipefail

: "${AWS_REGION:?Set AWS_REGION}"
: "${VPC_ID:?Set VPC_ID}"
: "${PUBLIC_SUBNET_IDS:?Set two comma-separated public subnet IDs}"
: "${TASK_EXECUTION_ROLE_ARN:?Set TASK_EXECUTION_ROLE_ARN}"
: "${ALLOWED_CIDR:?Set the CIDR permitted to reach the demo ALB}"
: "${DEPLOY_SHA:?Set the validated commit SHA}"
: "${IMAGE_TAG:?Set IMAGE_TAG to the validated SHA and CI run ID}"
: "${ECR_REGISTRY:?Set ECR_REGISTRY}"

stack_name="${STACK_NAME:-advanced-software-transportation}"
backend_repo="advanced-software/transportation-backend"
frontend_repo="advanced-software/transportation-frontend"
mkdir -p reports/cloud
for repository in "$backend_repo" "$frontend_repo"; do
  # describe/create is deliberately explicit: permission failures must not be ignored.
  if ! aws ecr describe-repositories --repository-names "$repository" --region "$AWS_REGION" > reports/cloud/ecr-check.json 2> reports/cloud/ecr-check.err; then
    if grep -q RepositoryNotFoundException reports/cloud/ecr-check.err; then
      aws ecr create-repository --repository-name "$repository" --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true --region "$AWS_REGION"
    else
      cat reports/cloud/ecr-check.err >&2
      exit 1
    fi
  fi
done

# Always use the images built in the gated CI run, never rebuild different inputs.
for component in backend frontend; do
  repository="advanced-software/transportation-$component"
  if ! aws ecr describe-images --repository-name "$repository" --image-ids "imageTag=$IMAGE_TAG" --region "$AWS_REGION" > "reports/cloud/$component-image.json" 2> "reports/cloud/$component-image.err"; then
    if ! grep -q ImageNotFoundException "reports/cloud/$component-image.err"; then
      cat "reports/cloud/$component-image.err" >&2
      exit 1
    fi
    docker tag "transportation-$component:$DEPLOY_SHA" "$ECR_REGISTRY/$repository:$IMAGE_TAG"
    docker push "$ECR_REGISTRY/$repository:$IMAGE_TAG"
  fi
done

aws cloudformation validate-template --template-body file://scripts/deploy/transportation.yml --region "$AWS_REGION" > reports/cloud/template-validation.json
aws cloudformation deploy --template-file scripts/deploy/transportation.yml \
  --stack-name "$stack_name" --region "$AWS_REGION" --no-fail-on-empty-changeset \
  --parameter-overrides \
    "VpcId=$VPC_ID" "PublicSubnetIds=$PUBLIC_SUBNET_IDS" \
    "ExecutionRoleArn=$TASK_EXECUTION_ROLE_ARN" "AllowedCidr=$ALLOWED_CIDR" \
    "BackendImage=$ECR_REGISTRY/$backend_repo:$IMAGE_TAG" \
    "FrontendImage=$ECR_REGISTRY/$frontend_repo:$IMAGE_TAG" "ImageRevision=$DEPLOY_SHA"
aws cloudformation describe-stacks --stack-name "$stack_name" --region "$AWS_REGION" > reports/cloud/stack.json
cluster_name=$(jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "ClusterName") | .OutputValue' reports/cloud/stack.json)
service_name=$(jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "ServiceName") | .OutputValue' reports/cloud/stack.json)
aws ecs wait services-stable --cluster "$cluster_name" --services "$service_name" --region "$AWS_REGION"
aws ecs describe-services --cluster "$cluster_name" --services "$service_name" --region "$AWS_REGION" > reports/cloud/services.json
jq -e '.failures | length == 0' reports/cloud/services.json
jq -e '.services | length == 1 and all(.[]; .runningCount == .desiredCount and .runningCount > 0 and any(.deployments[]; .status == "PRIMARY" and .rolloutState == "COMPLETED"))' reports/cloud/services.json
jq -r '.Stacks[0].Outputs[] | select(.OutputKey == "ApplicationUrl") | .OutputValue' reports/cloud/stack.json
