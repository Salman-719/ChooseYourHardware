#!/bin/bash
# Master deployment script - Deploys both backend and frontend
# Usage: cd deployment && ./deploy_all.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Script directory (deployment folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}ChooseYourHardware Full Deployment${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# Load environment variables from .env if exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}Loading configuration from .env file...${NC}"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${YELLOW}No .env file found. Will prompt for configuration.${NC}"
fi

# Get configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
OPENAI_KEY="${OPENAI_API_KEY:-}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${GCP_SERVICE_NAME:-chooseyourhardware}"
SITE_ID="${FIREBASE_SITE_ID:-}"

# Prompt for required values
while [ -z "$PROJECT_ID" ]; do
    echo -e "${YELLOW}Enter your GCP Project ID:${NC}"
    read -r PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Project ID cannot be empty. Please try again.${NC}"
    fi
done

while [ -z "$OPENAI_KEY" ]; do
    echo -e "${YELLOW}Enter your OpenAI API Key:${NC}"
    read -rs OPENAI_KEY
    echo ""
    if [ -z "$OPENAI_KEY" ]; then
        echo -e "${RED}OpenAI API Key cannot be empty. Please try again.${NC}"
    fi
done

if [ -z "$SITE_ID" ]; then
    echo -e "${YELLOW}Enter Firebase site ID (or press Enter to use '$PROJECT_ID'):${NC}"
    read -r SITE_ID
    if [ -z "$SITE_ID" ]; then
        SITE_ID="$PROJECT_ID"
    fi
fi

echo ""
echo -e "${BLUE}Full Deployment Configuration:${NC}"
echo -e "  Project ID:      ${GREEN}$PROJECT_ID${NC}"
echo -e "  Region:          ${GREEN}$REGION${NC}"
echo -e "  Backend Service: ${GREEN}$SERVICE_NAME${NC}"
echo -e "  Frontend Site:   ${GREEN}$SITE_ID.web.app${NC}"
echo -e "  OpenAI Key:      ${GREEN}Set${NC}"
echo ""

# Confirm deployment
echo -e "${YELLOW}This will deploy both backend and frontend. Proceed? (y/n)${NC}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

# Update .env if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo ""
    echo -e "${BLUE}Creating .env file for future deployments...${NC}"
    cat > "$PROJECT_ROOT/.env" << EOF
# Google Cloud Configuration
GCP_PROJECT_ID=$PROJECT_ID
GCP_REGION=$REGION
GCP_SERVICE_NAME=$SERVICE_NAME
GCP_MEMORY=1Gi
GCP_CPU=1
GCP_MIN_INSTANCES=0
GCP_MAX_INSTANCES=5
GCP_TIMEOUT=300

# OpenAI Configuration
OPENAI_API_KEY=$OPENAI_KEY
OPENAI_LLM_MODEL=gpt-4o-mini

# Firebase Configuration
FIREBASE_SITE_ID=$SITE_ID

# API Configuration
ENV=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
LOG_FORMAT=text
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
fi

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}STEP 1: Deploying Backend to Cloud Run${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# Deploy backend
cd "$SCRIPT_DIR/backend"
export GCP_PROJECT_ID="$PROJECT_ID"
export OPENAI_API_KEY="$OPENAI_KEY"
export GCP_REGION="$REGION"
export GCP_SERVICE_NAME="$SERVICE_NAME"

# Run backend deployment with auto-confirm
echo "y" | ./deploy_gcloud.sh

# Get backend URL
BACKEND_URL=$(gcloud run services describe "$SERVICE_NAME" \
    --region="$REGION" \
    --format="value(status.url)")

echo ""
echo -e "${GREEN}✓ Backend deployed successfully!${NC}"
echo -e "${GREEN}  Backend URL: $BACKEND_URL${NC}"

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}STEP 2: Deploying Frontend to Firebase${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

# Deploy frontend with backend URL
cd "$SCRIPT_DIR/frontend"
export FIREBASE_BACKEND_URL="$BACKEND_URL/api/v1"
export FIREBASE_SITE_ID="$SITE_ID"

# Run frontend deployment with auto-confirm
echo "y" | ./deploy_firebase.sh

FRONTEND_URL="https://${SITE_ID}.web.app"

echo ""
echo -e "${MAGENTA}========================================${NC}"
echo -e "${MAGENTA}DEPLOYMENT COMPLETE! 🎉${NC}"
echo -e "${MAGENTA}========================================${NC}"
echo ""

echo -e "${BLUE}Your Application URLs:${NC}"
echo -e "  ${GREEN}Frontend:${NC}  $FRONTEND_URL"
echo -e "  ${GREEN}Backend:${NC}   $BACKEND_URL"
echo -e "  ${GREEN}API Docs:${NC}  $BACKEND_URL/docs"
echo ""

echo -e "${BLUE}Test your deployment:${NC}"
echo -e "  ${YELLOW}curl $BACKEND_URL/health${NC}"
echo -e "  ${YELLOW}open $FRONTEND_URL${NC}"
echo ""

echo -e "${BLUE}View logs:${NC}"
echo -e "  Backend:  ${YELLOW}gcloud run logs read $SERVICE_NAME --region=$REGION${NC}"
echo -e "  Frontend: ${YELLOW}firebase hosting:channel:list --project=$PROJECT_ID${NC}"
echo ""

echo -e "${GREEN}All services deployed successfully! 🚀${NC}"
