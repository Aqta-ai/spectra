#!/bin/bash
# Spectra — Automated deployment to Google Cloud Run
# Usage: ./deploy.sh <PROJECT_ID> [REGION]
# Example: ./deploy.sh analog-sum-485815-j3 europe-west1
#
# Prerequisites:
#   gcloud auth login
#   export GOOGLE_API_KEY=<your-gemini-api-key>

set -euo pipefail

PROJECT_ID="${1:?Usage: ./deploy.sh <PROJECT_ID> [REGION]}"
REGION="${2:-europe-west1}"

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
  echo "❌  GOOGLE_API_KEY not set. Run: export GOOGLE_API_KEY=<your-key>"
  exit 1
fi

echo "🔮 Deploying Spectra to Google Cloud..."
echo "   Project: $PROJECT_ID"
echo "   Region:  $REGION"

gcloud config set project "$PROJECT_ID"

# ── Enable required APIs ───────────────────────────────────────────────────────
echo "📦 Enabling APIs..."
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  --project "$PROJECT_ID"

# ── Store API key in Secret Manager (idempotent) ───────────────────────────────
echo "🔑 Storing API key in Secret Manager..."
if ! gcloud secrets describe spectra-gemini-key --project "$PROJECT_ID" &>/dev/null; then
  echo -n "$GOOGLE_API_KEY" | gcloud secrets create spectra-gemini-key \
    --data-file=- \
    --project "$PROJECT_ID"
  echo "   Created secret: spectra-gemini-key"
else
  echo -n "$GOOGLE_API_KEY" | gcloud secrets versions add spectra-gemini-key \
    --data-file=- \
    --project "$PROJECT_ID"
  echo "   Updated secret: spectra-gemini-key"
fi

# ── Service account for backend ───────────────────────────────────────────────
SA_NAME="spectra-backend"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🔑 Setting up service account..."
if ! gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" &>/dev/null; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name "Spectra Backend" \
    --project "$PROJECT_ID"
fi

# Grant logging
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/logging.logWriter" \
  --condition=None --quiet

# Grant access to the API key secret
gcloud secrets add-iam-policy-binding spectra-gemini-key \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/secretmanager.secretAccessor" \
  --project "$PROJECT_ID" --quiet

# ── Deploy backend ────────────────────────────────────────────────────────────
echo "🚀 Deploying backend..."
gcloud run deploy spectra-backend \
  --source ./backend \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --service-account "$SA_EMAIL" \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 2 \
  --timeout 3600 \
  --session-affinity \
  --concurrency 20 \
  --min-instances 1 \
  --max-instances 10 \
  --set-secrets "GOOGLE_API_KEY=spectra-gemini-key:latest" \
  --set-env-vars "ALLOWED_ORIGINS=*,LOG_LEVEL=WARNING"

BACKEND_URL=$(gcloud run services describe spectra-backend \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)')

echo "   Backend: $BACKEND_URL"

WS_URL="${BACKEND_URL/https:\/\//wss://}/ws"
echo "   WS URL:  $WS_URL"

# ── Build & deploy frontend (WS URL baked in at build time) ───────────────────
FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/spectra-frontend:latest"
echo "🔨 Building frontend (WS_URL=${WS_URL})..."
gcloud builds submit ./frontend \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --config frontend/cloudbuild.yaml \
  --substitutions "_NEXT_PUBLIC_WS_URL=${WS_URL},_IMAGE=${FRONTEND_IMAGE}"

echo "🚀 Deploying frontend..."
gcloud run deploy spectra-frontend \
  --image "$FRONTEND_IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10

FRONTEND_URL=$(gcloud run services describe spectra-frontend \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)')

echo "   Frontend: $FRONTEND_URL"

# ── Patch backend CORS to real frontend URL ───────────────────────────────────
echo "🔧 Patching backend CORS → $FRONTEND_URL..."
gcloud run services update spectra-backend \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --update-env-vars "ALLOWED_ORIGINS=${FRONTEND_URL}"

echo ""
echo "✅ Spectra deployed!"
echo "   Frontend: $FRONTEND_URL"
echo "   Backend:  $BACKEND_URL"
echo "   WS:       $WS_URL"
