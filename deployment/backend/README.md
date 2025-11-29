# Backend Deployment

This directory contains backend deployment configurations and scripts for Google Cloud Run.

## 📁 Structure

```
deployment/backend/
├── README.md              # This file
├── DEPLOYMENT.md          # Detailed deployment guide
├── deploy_gcloud.sh       # Automated GCP deployment script
└── .gcloudignore         # Files to exclude from GCP upload
```

Note: Dockerfile is in the project root (required by Cloud Build).

## 🚀 Quick Deploy to Google Cloud Run

```bash
# 1. Configure environment (in project root)
cp .env.example .env
# Edit .env with your GCP_PROJECT_ID and OPENAI_API_KEY

# 2. Deploy
cd deployment/backend
./deploy_gcloud.sh
```

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

## 📋 Other Deployment Options

### Local Docker

```bash
# Build (from project root)
docker build -t chooseyourhardware .

# Run
docker run -p 8080:8080 \
  -e OPENAI_API_KEY=your-key \
  -e PYTHONPATH=/app/src \
  chooseyourhardware
```

### Kubernetes (Future)

```bash
# Coming soon: k8s manifests
```

### AWS ECS (Future)

```bash
# Coming soon: terraform configs
```

## 📝 Files

### deploy_gcloud.sh
Automated deployment script that:
- Authenticates with GCP
- Enables required APIs
- Builds and deploys container
- Tests deployment
- Shows service URL

### Dockerfile
Production-optimized container:
- Python 3.11 slim
- Non-root user
- Health checks
- Minimal attack surface

### .gcloudignore
Excludes from deployment:
- Tests
- Documentation
- Local files
- Development dependencies

## 🔧 Configuration

All configuration via `.env` in project root:

```bash
# GCP
GCP_PROJECT_ID=your-project
GCP_REGION=us-central1
GCP_SERVICE_NAME=chooseyourhardware-api

# Resources
GCP_MEMORY=2Gi
GCP_CPU=1
GCP_MIN_INSTANCES=0
GCP_MAX_INSTANCES=10

# App
OPENAI_API_KEY=sk-xxx
ENV=production
```

## 📊 Monitoring

After deployment:

```bash
# View logs
gcloud run logs read chooseyourhardware-api --region=us-central1

# Stream logs
gcloud run logs tail chooseyourhardware-api --region=us-central1

# Metrics
gcloud run services describe chooseyourhardware-api --region=us-central1
```

## 🔄 Updates

To redeploy after changes:

```bash
cd deployment
./deploy_gcloud.sh
```

Cloud Run automatically handles:
- Zero-downtime deployment
- Traffic migration
- Rollback on failure

## 🗑️ Cleanup

```bash
gcloud run services delete chooseyourhardware-api --region=us-central1
```
