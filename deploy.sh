#!/bin/bash
# Spectra — Automated deployment to Google Cloud Run
# Usage: ./deploy.sh <PROJECT_ID> <REGION>

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> <REGION>}"
REGION="${2:-europe-west1}"

echo "🔮 Deploying Spectra to Google Cloud..."
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"

# Set project
gcloud config set project "$PROJECT_ID"

# Enable APIs
echo "📦 Enabling APIs..."
gcloud services enable run.googleapis.com \
  firestore.googleapis.com \
  storage.googleapis.com \
  logging.googleapis.com \
  artifactregistry.googleapis.com

# Load backend env vars for Cloud Run
GOOGLE_API_KEY="${GOOGLE_API_KEY:-$(grep '^GOOGLE_API_KEY=' backend/.env 2>/dev/null | cut -d'=' -f2-)}"
if [[ -z "$GOOGLE_API_KEY" ]]; then
  echo "❌ GOOGLE_API_KEY not set. Export it or add it to backend/.env"
  exit 1
fi

FRONTEND_ORIGIN="https://spectra.aqta.ai"

# Deploy backend
echo "🚀 Deploying backend..."
gcloud run deploy spectra-backend \
  --source ./backend \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --timeout 3600 \
  --session-affinity \
  --set-env-vars "GOOGLE_API_KEY=${GOOGLE_API_KEY},ALLOWED_ORIGINS=${FRONTEND_ORIGIN},LOG_LEVEL=WARNING"

BACKEND_URL=$(gcloud run services describe spectra-backend \
  --region "$REGION" --format='value(status.url)')

echo "   Backend: $BACKEND_URL"

# Build and push frontend image
FRONTEND_IMAGE="europe-west1-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/spectra-frontend:latest"
echo "🔨 Building frontend..."
gcloud builds submit ./frontend \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --tag "$FRONTEND_IMAGE"

# Deploy frontend
echo "🚀 Deploying frontend..."
gcloud run deploy spectra-frontend \
  --image "$FRONTEND_IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars "NEXT_PUBLIC_WS_URL=wss://api.spectra.aqta.ai/ws,NEXT_PUBLIC_BRANDED=true"

FRONTEND_URL=$(gcloud run services describe spectra-frontend \
  --region "$REGION" --format='value(status.url)')

echo ""
echo "✅ Spectra deployed!"
echo "   Frontend: $FRONTEND_URL"
echo "   Backend:  $BACKEND_URL"
