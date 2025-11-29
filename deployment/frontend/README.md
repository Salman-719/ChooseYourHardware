# Frontend Deployment to Firebase Hosting

Quick reference for deploying the ChooseYourHardware frontend to Firebase Hosting.

## 🚀 Quick Deploy

```bash
cd deployment/frontend
./deploy_firebase.sh
```

The script will:
1. ✅ Install Firebase CLI (if needed)
2. ✅ Authenticate with Google
3. ✅ Set up Firebase project
4. ✅ Configure environment variables
5. ✅ Install npm dependencies
6. ✅ Build production bundle
7. ✅ Deploy to Firebase Hosting

## 📋 What You Need

- **GCP Project ID** (same as backend: `easyware-479711`)
- **Google Account** with access to the project

## 🌐 After Deployment

Your frontend will be available at:
```
https://easyware-479711.web.app
```

Connected to backend:
```
https://chooseyourhardware-rhen2vww6a-uc.a.run.app/api/v1
```

## 💰 Cost

**FREE** - Firebase Hosting free tier includes:
- 10 GB storage
- 360 MB/day transfer
- Free SSL certificate
- Global CDN

## 🔧 Manual Steps (if needed)

```bash
# Install Firebase CLI
npm install -g firebase-tools

# Login
firebase login

# Build frontend
cd Frontend/northlane-partner-hub
npm install
npm run build

# Deploy
firebase deploy --only hosting
```

## 📝 Files Created

- `Frontend/northlane-partner-hub/firebase.json` - Firebase configuration
- `Frontend/northlane-partner-hub/.firebaserc` - Project settings
- `Frontend/northlane-partner-hub/.env.production` - Production environment variables

## 🛠️ Useful Commands

```bash
# View deployments
firebase hosting:channel:list

# Roll back
firebase hosting:channel:deploy previous

# Delete hosting
firebase hosting:disable
```
