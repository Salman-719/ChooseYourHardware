#!/bin/bash
# Firebase Hosting deployment script for ChooseYourHardware Frontend
# Usage: cd deployment/frontend && ./deploy_firebase.sh

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (deployment/frontend folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Project root (two levels up)
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
# Frontend directory
FRONTEND_DIR="$PROJECT_ROOT/Frontend/northlane-partner-hub"

echo -e "${BLUE}==================================${NC}"
echo -e "${BLUE}Firebase Hosting Deployment${NC}"
echo -e "${BLUE}==================================${NC}"
echo ""

echo -e "${YELLOW}Prerequisites:${NC}"
echo -e "  1. Google account with Firebase access"
echo -e "  2. Firebase project created (or we'll help you set it up)"
echo -e ""
echo -e "${YELLOW}If you haven't set up Firebase yet:${NC}"
echo -e "  Visit: ${BLUE}https://console.firebase.google.com${NC}"
echo -e "  Note: We'll add your GCP project to Firebase automatically"
echo ""

# Load environment variables from .env if exists
if [ -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}Loading configuration from .env file...${NC}"
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
else
    echo -e "${YELLOW}No .env file found in project root.${NC}"
fi

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-}"
BACKEND_URL="${FIREBASE_BACKEND_URL:-}"
SITE_ID="${FIREBASE_SITE_ID:-}"

# Prompt for project ID if not set
while [ -z "$PROJECT_ID" ]; do
    echo -e "${YELLOW}Enter your GCP Project ID (same as backend):${NC}"
    read -r PROJECT_ID
    if [ -z "$PROJECT_ID" ]; then
        echo -e "${RED}Project ID cannot be empty. Please try again.${NC}"
    fi
done

# Prompt for backend URL if not set
while [ -z "$BACKEND_URL" ]; do
    echo -e "${YELLOW}Enter your backend API URL (e.g., https://your-service.a.run.app/api/v1):${NC}"
    read -r BACKEND_URL
    if [ -z "$BACKEND_URL" ]; then
        echo -e "${RED}Backend URL cannot be empty. Please try again.${NC}"
    fi
done

# Prompt for site ID if not set (optional, will use default if skipped)
if [ -z "$SITE_ID" ]; then
    echo -e "${YELLOW}Enter Firebase site ID (or press Enter to use '$PROJECT_ID'):${NC}"
    read -r SITE_ID
    if [ -z "$SITE_ID" ]; then
        SITE_ID="$PROJECT_ID"
    fi
fi

echo ""
echo -e "${BLUE}Deployment Configuration:${NC}"
echo -e "  Project ID:      ${GREEN}$PROJECT_ID${NC}"
echo -e "  Backend API URL: ${GREEN}$BACKEND_URL${NC}"
echo -e "  Firebase Site:   ${GREEN}$SITE_ID.web.app${NC}"
echo -e "  Frontend Dir:    ${GREEN}$FRONTEND_DIR${NC}"
echo ""

# Confirm deployment
echo -e "${YELLOW}Proceed with deployment? (y/n)${NC}"
read -r CONFIRM
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo -e "${RED}Deployment cancelled${NC}"
    exit 0
fi

echo ""
echo -e "${BLUE}Step 1: Checking Firebase CLI installation...${NC}"
if ! command -v firebase &> /dev/null; then
    echo -e "${YELLOW}Firebase CLI not found. Installing...${NC}"
    sudo npm install -g firebase-tools
    echo -e "${GREEN}✓ Firebase CLI installed${NC}"
else
    echo -e "${GREEN}✓ Firebase CLI already installed${NC}"
fi

echo ""
echo -e "${BLUE}Step 2: Checking authentication...${NC}"
if ! firebase projects:list &> /dev/null; then
    echo -e "${YELLOW}Not authenticated. Running firebase login...${NC}"
    firebase login
else
    echo -e "${GREEN}✓ Already authenticated${NC}"
fi

echo ""
echo -e "${BLUE}Step 3: Adding GCP project to Firebase...${NC}"
# Check if project exists in Firebase
if firebase projects:list 2>/dev/null | grep -q "$PROJECT_ID"; then
    echo -e "${GREEN}✓ Project already added to Firebase${NC}"
else
    echo -e "${YELLOW}Adding GCP project to Firebase...${NC}"
    firebase projects:addfirebase "$PROJECT_ID" || {
        echo -e "${RED}Failed to add project to Firebase.${NC}"
        echo -e "${YELLOW}Please add it manually at: https://console.firebase.google.com${NC}"
        echo -e "${YELLOW}Then run this script again.${NC}"
        exit 1
    }
    echo -e "${GREEN}✓ Project added to Firebase${NC}"
fi

echo ""
echo -e "${BLUE}Step 4: Setting up Firebase project...${NC}"
cd "$FRONTEND_DIR"

# Check if Firebase is already initialized
if [ ! -f ".firebaserc" ] || [ ! -f "firebase.json" ]; then
    echo -e "${YELLOW}Initializing Firebase Hosting...${NC}"
    
    # Create firebase.json
    cat > firebase.json << EOF
{
  "hosting": {
    "site": "$SITE_ID",
    "public": "dist",
    "ignore": [
      "firebase.json",
      "**/.*",
      "**/node_modules/**"
    ],
    "rewrites": [
      {
        "source": "**",
        "destination": "/index.html"
      }
    ],
    "headers": [
      {
        "source": "**/*.@(jpg|jpeg|gif|png|svg|webp|js|css|woff|woff2|ttf|eot)",
        "headers": [
          {
            "key": "Cache-Control",
            "value": "max-age=31536000"
          }
        ]
      }
    ]
  }
}
EOF
    
    # Create .firebaserc
    cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF
    
    echo -e "${GREEN}✓ Firebase initialized${NC}"
else
    echo -e "${YELLOW}Updating Firebase configuration...${NC}"
    
    # Update .firebaserc with current project
    cat > .firebaserc << EOF
{
  "projects": {
    "default": "$PROJECT_ID"
  }
}
EOF
    echo -e "${GREEN}✓ Firebase configuration updated${NC}"
fi

echo ""
echo -e "${BLUE}Step 5: Creating production .env file...${NC}"
cat > .env.production << EOF
VITE_API_BASE_URL=$BACKEND_URL
EOF
echo -e "${GREEN}✓ Created .env.production${NC}"

echo ""
echo -e "${BLUE}Step 6: Installing dependencies...${NC}"
if [ ! -d "node_modules" ]; then
    npm install
    echo -e "${GREEN}✓ Dependencies installed${NC}"
else
    echo -e "${GREEN}✓ Dependencies already installed${NC}"
fi

echo ""
echo -e "${BLUE}Step 7: Building frontend for production...${NC}"
npm run build
echo -e "${GREEN}✓ Build complete${NC}"

echo ""
echo -e "${BLUE}Step 8: Creating Firebase Hosting site...${NC}"
# Try to create the site, ignore if already exists
firebase hosting:sites:create "$SITE_ID" --project "$PROJECT_ID" 2>/dev/null && {
    echo -e "${GREEN}✓ Hosting site created: $SITE_ID${NC}"
} || {
    echo -e "${YELLOW}Site already exists or using default site${NC}"
}

echo ""
echo -e "${BLUE}Step 9: Deploying to Firebase Hosting...${NC}"
firebase deploy --only hosting --project "$PROJECT_ID"

echo ""
echo -e "${GREEN}==================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}==================================${NC}"

# Get hosting URL
HOSTING_URL="https://${SITE_ID}.web.app"

echo ""
echo -e "${BLUE}Frontend Information:${NC}"
echo -e "  Frontend URL:    ${GREEN}$HOSTING_URL${NC}"
echo -e "  Backend API:     ${GREEN}$BACKEND_URL${NC}"
echo ""

echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View hosting:    ${YELLOW}firebase hosting:channel:list --project=$PROJECT_ID${NC}"
echo -e "  Update frontend: ${YELLOW}cd deployment/frontend && ./deploy_firebase.sh${NC}"
echo -e "  Delete hosting:  ${YELLOW}firebase hosting:disable --project=$PROJECT_ID${NC}"
echo ""
echo -e "${GREEN}Frontend deployed successfully! 🚀${NC}"
echo -e "${GREEN}Visit: $HOSTING_URL${NC}"
