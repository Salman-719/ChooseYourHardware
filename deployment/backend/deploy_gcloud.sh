#!/bin/bash
# Google Cloud Run deployment script for ChooseYourHardware API
# Usage: cd deployment && ./deploy_gcloud.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (deployment/backend folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root (two levels up: deployment/backend -> deployment -> root)
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}Google Cloud Run Deployment${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

# Load environment variables from .env if exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}Loading configuration from .env file...${NC}"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${YELLOW}No .env file found in project root. Using defaults and prompts.${NC}"
fi

# Configuration with defaults
PROJECT_ID="${GCP_PROJECT_ID:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${GCP_SERVICE_NAME:-chooseyourhardware-api}"
MEMORY="${GCP_MEMORY:-2Gi}"
CPU="${GCP_CPU:-1}"
MIN_INSTANCES="${GCP_MIN_INSTANCES:-0}"
MAX_INSTANCES="${GCP_MAX_INSTANCES:-10}"
TIMEOUT="${GCP_TIMEOUT:-300}"
OPENAI_KEY="${OPENAI_API_KEY:-}"

# Prompt for required values if not set
while [ -z "$PROJECT_ID" ]; do
    echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
    read -r PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Project ID cannot be empty. Please try again.${NC}"
    fi
done

while [ -z "$OPENAI_KEY" ]; do
    echo -e "${YELLOW}Enter your OpenAI API Key (required):${NC}"
    read -rs OPENAI_KEY
    echo ""
    if [ -z "$OPENAI_KEY" ]; then
        echo -e "${RED}OpenAI API Key cannot be empty. Please try again.${NC}"
    fi
done

echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo -e "  Project ID:      ${GREEN}$PROJECT_ID${NC}"
echo -e "  Region:          ${GREEN}$REGION${NC}"
echo -e "  Service Name:    ${GREEN}$SERVICE_NAME${NC}"
echo -e "  Memory:          ${GREEN}$MEMORY${NC}"
echo -e "  CPU:             ${GREEN}$CPU${NC}"
echo -e "  Min Instances:   ${GREEN}$MIN_INSTANCES${NC}"
echo -e "  Max Instances:   ${GREEN}$MAX_INSTANCES${NC}"
echo -e "  Timeout:         ${GREEN}${TIMEOUT}s${NC}"
echo -e "  OpenAI Key:      ${GREEN}$([ -n "$OPENAI_KEY" ] && echo "Set" || echo "Not set")${NC}"
echo ""

# Confirm deployment
echo -e "${YELLOW}Proceed with deployment? (y/n)${NC}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Checking Google Cloud CLI installation...${NC}"
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Google Cloud CLI not found.${NC}"
    echo -e "${YELLOW}Please install it from: https://cloud.google.com/sdk/docs/install${NC}"
    echo -e "${YELLOW}Or run: curl https://sdk.cloud.google.com | bash${NC}"
    exit 1
else
    echo -e "${GREEN}✓ Google Cloud CLI installed${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Checking gcloud authentication...${NC}"
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo -e "${YELLOW}Not authenticated. Running gcloud auth login...${NC}"
    gcloud auth login
else
    ACTIVE_ACCOUNT=$(gcloud auth list --filter=status:ACTIVE --format="value(account)" | head -n 1)
    echo -e "${GREEN}✓ Already authenticated as: $ACTIVE_ACCOUNT${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✓ Project set to: $PROJECT_ID${NC}"

echo ""
echo -e "${BLUE}Step 4: Enabling required APIs...${NC}"
echo -e "${YELLOW}Enabling Cloud Run API...${NC}"
gcloud services enable run.googleapis.com --project="$PROJECT_ID"
echo -e "${YELLOW}Enabling Cloud Build API...${NC}"
gcloud services enable cloudbuild.googleapis.com --project="$PROJECT_ID"
echo -e "${YELLOW}Enabling Artifact Registry API...${NC}"
gcloud services enable artifactregistry.googleapis.com --project="$PROJECT_ID"
echo -e "${GREEN}✓ APIs enabled${NC}"

echo ""
echo -e "${BLUE}Step 5: Building and deploying to Cloud Run...${NC}"

# Change to project root for deployment
cd "$PROJECT_ROOT"

# Build deployment command - use Dockerfile from deployment folder
DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory $MEMORY \
    --cpu $CPU \
    --min-instances $MIN_INSTANCES \
    --max-instances $MAX_INSTANCES \
    --timeout ${TIMEOUT}s \
    --port 8000 \
    --clear-base-image \
    --set-env-vars PYTHONPATH=/app/src,ENV=production,OPENAI_API_KEY=$OPENAI_KEY"

# Execute deployment
echo -e "${YELLOW}Running deployment command...${NC}"
eval "$DEPLOY_CMD"

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}==================================${NC}"

# Get service URL
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(status.url)")

echo ""
echo -e "${BLUE}Service Information:${NC}"
echo -e "  Service URL:     ${GREEN}$SERVICE_URL${NC}"
echo -e "  Health Check:    ${GREEN}${SERVICE_URL}/health${NC}"
echo -e "  API Docs:        ${GREEN}${SERVICE_URL}/docs${NC}"
echo ""

# Test health endpoint
echo -e "${BLUE}Testing health endpoint...${NC}"
if curl -sf "$SERVICE_URL/health" > /dev/null; then
    echo -e "${GREEN}✓ Health check passed!${NC}"
    echo -e "${GREEN}Response:${NC}"
    curl -s "$SERVICE_URL/health" | python3 -m json.tool || echo ""
else
    echo -e "${RED}✗ Health check failed${NC}"
    echo -e "${YELLOW}Check logs with: gcloud run logs read $SERVICE_NAME --region=$REGION${NC}"
fi

echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View logs:       ${YELLOW}gcloud run logs read $SERVICE_NAME --region=$REGION${NC}"
echo -e "  Stream logs:     ${YELLOW}gcloud run logs tail $SERVICE_NAME --region=$REGION${NC}"
echo -e "  Update service:  ${YELLOW}cd deployment/backend && ./deploy_gcloud.sh${NC}"
echo -e "  Delete service:  ${YELLOW}gcloud run services delete $SERVICE_NAME --region=$REGION${NC}"
echo ""
echo -e "${GREEN}Deployment successful! 🚀${NC}"
