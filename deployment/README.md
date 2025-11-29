# Deployment

Complete deployment automation for ChooseYourHardware (Backend + Frontend).

## 🚀 Quick Start - Three Ways to Deploy

### **Option A: Deploy Everything (Recommended for First Time)** ⭐

This is the **easiest way** - one command deploys both backend and frontend:

```bash
cd deployment
./deploy_all.sh
```

**What it does:**
1. Asks for your GCP Project ID (one time)
2. Asks for your OpenAI API Key (one time)
3. Deploys backend to Cloud Run
4. **Automatically gets backend URL**
5. Deploys frontend to Firebase
6. **Automatically connects frontend to backend**
7. Creates `.env` file so future deployments are automatic

**When to use:** First deployment, or when updating both services.

---

### **Option B: Deploy Only Backend**

If you only changed backend code:

```bash
cd deployment/backend
./deploy_gcloud.sh
```

**What you need:**
- GCP Project ID
- OpenAI API Key

**Where to put them:**

1. **Using .env file** (recommended):
```bash
# In project root, create/edit .env
GCP_PROJECT_ID=your-project-id
OPENAI_API_KEY=sk-...your-key...
```

2. **Script will prompt** if .env doesn't exist

**After deployment:** Script shows you the backend URL like:
```
https://chooseyourhardware-xyz123.a.run.app
```

---

### **Option C: Deploy Only Frontend**

If you only changed frontend code:

```bash
cd deployment/frontend
./deploy_firebase.sh
```

**What you need:**
- GCP Project ID (same as backend)
- Backend URL (from backend deployment)
- Firebase Site ID (e.g., "chooseyourhardware")

**Where to put them:**

1. **Using .env file** (recommended):
```bash
# In project root, create/edit .env
GCP_PROJECT_ID=your-project-id
FIREBASE_BACKEND_URL=https://your-backend-xyz.a.run.app/api/v1
FIREBASE_SITE_ID=chooseyourhardware
```

2. **Script will prompt** if values are missing

**Important:** Make sure `FIREBASE_BACKEND_URL` ends with `/api/v1`!

---

## 📖 Step-by-Step First Time Setup

### 1. Get Your Credentials

**Google Cloud Project:**
- Go to: https://console.cloud.google.com
- Create a new project or use existing one
- Copy your **Project ID** (e.g., `easyware-479711`)

**OpenAI API Key:**
- Go to: https://platform.openai.com/api-keys
- Create new secret key
- Copy the key (starts with `sk-...`)

**Firebase (Optional - script will help):**
- Visit: https://console.firebase.google.com
- The deployment script will add your GCP project to Firebase automatically
- Just make sure you're logged in with the same Google account

### 2. Create .env File (Optional but Recommended)

In the **project root** (not in deployment folder):

```bash
# Copy the example
cp .env.example .env

# Edit with your values
nano .env
```

**Minimum required:**
```bash
GCP_PROJECT_ID=your-project-id
OPENAI_API_KEY=sk-your-openai-key
FIREBASE_SITE_ID=chooseyourhardware  # or any name you want
```

**Full configuration (optional):**
```bash
# Google Cloud Configuration (Backend)
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GCP_SERVICE_NAME=chooseyourhardware
GCP_MEMORY=1Gi
GCP_CPU=1
GCP_MIN_INSTANCES=0
GCP_MAX_INSTANCES=5
GCP_TIMEOUT=300

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-key
OPENAI_LLM_MODEL=gpt-4o-mini

# Firebase Configuration (Frontend)
FIREBASE_SITE_ID=chooseyourhardware
# FIREBASE_BACKEND_URL will be set automatically by deploy_all.sh

# API Configuration
ENV=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
LOG_FORMAT=text
```

### 3. Run Deployment

**First time? Use deploy_all.sh:**
```bash
cd deployment
./deploy_all.sh
```

The script will:
- ✅ Check if gcloud CLI is installed (shows install link if not)
- ✅ Check if Firebase CLI is installed (installs automatically)
- ✅ Authenticate you with Google (opens browser)
- ✅ Ask for any missing configuration
- ✅ Deploy backend first
- ✅ Get backend URL automatically
- ✅ Deploy frontend with correct backend URL
- ✅ Show you both URLs at the end

### 4. Save the URLs

After successful deployment, you'll see:

```
========================================
DEPLOYMENT COMPLETE! 🎉
========================================

Your Application URLs:
  Frontend:  https://chooseyourhardware.web.app
  Backend:   https://chooseyourhardware-xyz123.a.run.app
  API Docs:  https://chooseyourhardware-xyz123.a.run.app/docs
```

**Save these URLs!** You'll need them to:
- Share your app with users (Frontend URL)
- Test the API (Backend URL)
- Update individual services later

---

## 🔄 Updating Your Deployment

### After First Deployment

The `.env` file is created automatically, so future deployments are easier!

**Update everything:**
```bash
cd deployment && ./deploy_all.sh
```

**Update only backend:**
```bash
cd deployment/backend && ./deploy_gcloud.sh
```

**Update only frontend:**
```bash
# First, make sure FIREBASE_BACKEND_URL is in .env
# Then:
cd deployment/frontend && ./deploy_firebase.sh
```

---

## 🔗 How URLs Connect

```
User Browser
    ↓
https://chooseyourhardware.web.app (Frontend - Firebase)
    ↓
    | Makes API calls to:
    ↓
https://chooseyourhardware-xyz.a.run.app/api/v1 (Backend - Cloud Run)
    ↓
    | Uses OpenAI API
    ↓
OpenAI API (External)
```

**Important:**
- Frontend URL: Set by FIREBASE_SITE_ID (you choose)
- Backend URL: Auto-generated by Cloud Run (based on service name + random hash)
- Backend URL must be added to frontend's .env.production (deploy_all.sh does this automatically)

---

## 📝 Environment Variables Reference

### Where to Set Them

**Project Root `.env` file** (recommended):
```bash
/home/user/ChooseYourHardware/.env
```

**NOT** in deployment folders - they read from project root!

### Required vs Optional

| Variable | Required? | Used By | Description |
|----------|-----------|---------|-------------|
| `GCP_PROJECT_ID` | **YES** | Both | Your Google Cloud Project ID |
| `OPENAI_API_KEY` | **YES** | Backend | OpenAI API key for metadata extraction |
| `FIREBASE_SITE_ID` | Recommended | Frontend | Your site name (e.g., `chooseyourhardware`) |
| `FIREBASE_BACKEND_URL` | Auto-set | Frontend | Backend API URL (set by deploy_all.sh) |
| `GCP_REGION` | No | Backend | Default: `us-central1` |
| `GCP_SERVICE_NAME` | No | Backend | Default: `chooseyourhardware` |
| `GCP_MEMORY` | No | Backend | Default: `1Gi` |
| `GCP_CPU` | No | Backend | Default: `1` |

### If You Don't Use .env

No problem! Scripts will prompt you for:
1. **GCP Project ID** - Type it when asked
2. **OpenAI API Key** - Type it when asked (hidden input)
3. **Backend URL** (frontend only) - Copy from backend deployment output
4. **Site ID** (frontend only) - Press Enter to use project ID, or type custom name

---

## 🎯 Common Scenarios

### Scenario 1: First Time Deployment

```bash
# 1. Create .env with your credentials
cat > .env << EOF
GCP_PROJECT_ID=my-project-123
OPENAI_API_KEY=sk-my-key
FIREBASE_SITE_ID=chooseyourhardware
EOF

# 2. Deploy everything
cd deployment
./deploy_all.sh

# 3. Done! URLs are shown at the end
```

### Scenario 2: Updated Backend Code Only

```bash
# Just redeploy backend
cd deployment/backend
./deploy_gcloud.sh

# Frontend keeps using the same backend URL (unchanged)
```

### Scenario 3: Updated Frontend Code Only

```bash
# Make sure .env has FIREBASE_BACKEND_URL
# Then:
cd deployment/frontend
./deploy_firebase.sh
```

### Scenario 4: Changed Both Backend and Frontend

```bash
# Easiest: redeploy everything
cd deployment
./deploy_all.sh
```

### Scenario 5: Backend URL Changed (rare)

If you changed `GCP_SERVICE_NAME` or deployed to different region:

```bash
# 1. Deploy backend
cd deployment/backend
./deploy_gcloud.sh
# Note the new backend URL: https://new-service-xyz.a.run.app

# 2. Update .env
echo "FIREBASE_BACKEND_URL=https://new-service-xyz.a.run.app/api/v1" >> .env

# 3. Redeploy frontend
cd deployment/frontend
./deploy_firebase.sh
```

---

## 📁 Structure

```
deployment/
├── deploy_all.sh          # Master script - deploys everything
├── backend/
│   ├── deploy_gcloud.sh   # Backend → Google Cloud Run
│   ├── .gcloudignore
│   ├── DEPLOYMENT.md
│   └── README.md
└── frontend/
    ├── deploy_firebase.sh # Frontend → Firebase Hosting
    └── README.md
```

## 🔧 Prerequisites

### First Time Setup

1. **Google Cloud Account**
   - Create project at: https://console.cloud.google.com
   - Note your Project ID

2. **Firebase Account** (optional - script will help)
   - Visit: https://console.firebase.google.com
   - Script will automatically add your GCP project to Firebase

3. **Install CLIs** (script will check/help install)
   - Google Cloud SDK: https://cloud.google.com/sdk/docs/install
   - Firebase CLI: Installed automatically by script

4. **OpenAI API Key**
   - Get from: https://platform.openai.com/api-keys

## 📋 Configuration Options

### Option 1: Use .env file (Recommended)

```bash
# Copy example
cp .env.example .env

# Edit with your values
nano .env
```

Set these required values:
```bash
GCP_PROJECT_ID=your-project-id
OPENAI_API_KEY=your-openai-key
FIREBASE_SITE_ID=chooseyourhardware  # Your site name
```

### Option 2: Interactive Prompts

Just run `./deploy_all.sh` - it will ask for missing values!

## 🎯 Deploy Individual Services

### Backend Only

```bash
cd deployment/backend
./deploy_gcloud.sh
```

### Frontend Only

```bash
cd deployment/frontend
./deploy_firebase.sh
```

## 📊 What Gets Deployed

### Backend (Google Cloud Run)
- **URL**: `https://[service-name]-[hash].a.run.app`
- **Features**:
  - Auto-scaling (0 to 10 instances)
  - HTTPS automatic
  - Pay-per-request
  - Health checks
  - API documentation at `/docs`

### Frontend (Firebase Hosting)
- **URL**: `https://[site-id].web.app`
- **Features**:
  - Global CDN
  - Automatic HTTPS
  - Free tier (10GB + 360MB/day)
  - Instant deployments
  - Rollback support

## 🔄 Update Deployments

### Update Everything
```bash
cd deployment && ./deploy_all.sh
```

### Update Backend Only
```bash
cd deployment/backend && ./deploy_gcloud.sh
```

### Update Frontend Only
```bash
cd deployment/frontend && ./deploy_firebase.sh
```

## 📝 Environment Variables

All scripts read from `.env` in project root, with fallback to interactive prompts.

**Backend Variables:**
- `GCP_PROJECT_ID` - Required
- `OPENAI_API_KEY` - Required
- `GCP_REGION` - Optional (default: us-central1)
- `GCP_SERVICE_NAME` - Optional (default: chooseyourhardware)
- `GCP_MEMORY` - Optional (default: 1Gi)
- `GCP_CPU` - Optional (default: 1)
- `GCP_MIN_INSTANCES` - Optional (default: 0)
- `GCP_MAX_INSTANCES` - Optional (default: 5)

**Frontend Variables:**
- `FIREBASE_SITE_ID` - Optional (default: project-id)
- `FIREBASE_BACKEND_URL` - Auto-set by deploy_all.sh

## 🛠️ Troubleshooting

### "gcloud: command not found"
Install Google Cloud SDK: https://cloud.google.com/sdk/docs/install

### "firebase: command not found"
Script will install automatically (requires sudo)

### "Project not found in Firebase"
Script will automatically add your GCP project to Firebase

### "Site ID already exists"
Choose a different FIREBASE_SITE_ID or use the existing one

## 💰 Cost Estimates

**Backend (Cloud Run):**
- Free tier: 2M requests/month
- Light usage: ~$5-10/month
- With min_instances=1: ~$72/month

**Frontend (Firebase Hosting):**
- FREE for most use cases
- 10GB storage, 360MB/day transfer

## 📚 Additional Documentation

- [Backend Deployment Guide](./backend/DEPLOYMENT.md)
- [Frontend Deployment Guide](./frontend/README.md)
- [Main README](../README.md)

## 🔗 Useful Commands

```bash
# View backend logs
gcloud run logs read chooseyourhardware --region=us-central1

# View frontend deployments
firebase hosting:channel:list

# Test backend health
curl https://your-backend-url.a.run.app/health

# Open frontend
open https://your-site-id.web.app
```

## 🎉 Success!

After deployment, you'll see:
- ✅ Frontend URL (Firebase Hosting)
- ✅ Backend URL (Cloud Run)
- ✅ API Docs URL
- ✅ Health check status

Your app is live and ready to use! 🚀
