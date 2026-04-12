#!/bin/bash
# Spectra Production Deployment Script
# Deploys backend and frontend to Google Cloud Run with full configuration

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-analog-sum-485815-j3}"
REGION="${GCP_REGION:-europe-west1}"
BACKEND_SERVICE="spectra-backend"
FRONTEND_SERVICE="spectra-frontend"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Spectra Production Deployment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Project:${NC} $PROJECT_ID"
echo -e "${GREEN}Region:${NC}  $REGION"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}❌ gcloud CLI not found. Please install it first.${NC}"
    exit 1
fi

if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
    echo -e "${RED}❌ GOOGLE_API_KEY not set${NC}"
    echo -e "${YELLOW}Please run: export GOOGLE_API_KEY=your_key${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Prerequisites OK${NC}"
echo ""

# Set project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project "$PROJECT_ID"
echo -e "${GREEN}✓ Project set${NC}"
echo ""

# Enable APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com \
  --project "$PROJECT_ID" \
  --quiet

echo -e "${GREEN}✓ APIs enabled${NC}"
echo ""

# Store API key in Secret Manager
echo -e "${YELLOW}Storing API key in Secret Manager...${NC}"
if ! gcloud secrets describe spectra-gemini-key --project "$PROJECT_ID" &>/dev/null; then
  echo -n "$GOOGLE_API_KEY" | gcloud secrets create spectra-gemini-key \
    --data-file=- \
    --project "$PROJECT_ID"
  echo -e "${GREEN}✓ Secret created${NC}"
else
  echo -n "$GOOGLE_API_KEY" | gcloud secrets versions add spectra-gemini-key \
    --data-file=- \
    --project "$PROJECT_ID"
  echo -e "${GREEN}✓ Secret updated${NC}"
fi
echo ""

# Create service account
echo -e "${YELLOW}Setting up service account...${NC}"
SA_NAME="spectra-backend"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe "$SA_EMAIL" --project "$PROJECT_ID" &>/dev/null; then
  gcloud iam service-accounts create "$SA_NAME" \
    --display-name "Spectra Backend" \
    --project "$PROJECT_ID"
  echo -e "${GREEN}✓ Service account created${NC}"
else
  echo -e "${GREEN}✓ Service account exists${NC}"
fi

# Grant permissions
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/logging.logWriter" \
  --condition=None --quiet

gcloud secrets add-iam-policy-binding spectra-gemini-key \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/secretmanager.secretAccessor" \
  --project "$PROJECT_ID" --quiet

echo -e "${GREEN}✓ Permissions granted${NC}"
echo ""

# Deploy backend
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Deploying Backend${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

gcloud run deploy "$BACKEND_SERVICE" \
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
  --set-env-vars "ALLOWED_ORIGINS=*,LOG_LEVEL=INFO,ENABLE_GEMINI_LIVE=true"

BACKEND_URL=$(gcloud run services describe "$BACKEND_SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)')

WS_URL="${BACKEND_URL/https:\/\//wss://}/ws"

echo ""
echo -e "${GREEN}✓ Backend deployed${NC}"
echo -e "${GREEN}  URL: $BACKEND_URL${NC}"
echo -e "${GREEN}  WS:  $WS_URL${NC}"
echo ""

# Build frontend
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Building Frontend${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

FRONTEND_IMAGE="${REGION}-docker.pkg.dev/${PROJECT_ID}/cloud-run-source-deploy/${FRONTEND_SERVICE}:latest"

gcloud builds submit ./frontend \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --config frontend/cloudbuild.yaml \
  --substitutions "_NEXT_PUBLIC_WS_URL=${WS_URL},_IMAGE=${FRONTEND_IMAGE}"

echo -e "${GREEN}✓ Frontend built${NC}"
echo ""

# Deploy frontend
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Deploying Frontend${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

gcloud run deploy "$FRONTEND_SERVICE" \
  --image "$FRONTEND_IMAGE" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --allow-unauthenticated \
  --memory 512Mi \
  --cpu 1 \
  --concurrency 80 \
  --min-instances 0 \
  --max-instances 10

FRONTEND_URL=$(gcloud run services describe "$FRONTEND_SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --format='value(status.url)')

echo ""
echo -e "${GREEN}✓ Frontend deployed${NC}"
echo -e "${GREEN}  URL: $FRONTEND_URL${NC}"
echo ""

# Update backend CORS
echo -e "${YELLOW}Configuring CORS...${NC}"
CORS_ORIGINS="${FRONTEND_URL},https://spectra.aqta.ai"

gcloud run services update "$BACKEND_SERVICE" \
  --region "$REGION" \
  --project "$PROJECT_ID" \
  --update-env-vars "ALLOWED_ORIGINS=${CORS_ORIGINS}"

echo -e "${GREEN}✓ CORS configured${NC}"
echo ""

# Health check
echo -e "${YELLOW}Running health checks...${NC}"
sleep 5

BACKEND_HEALTH=$(curl -s "${BACKEND_URL}/health" | grep -o '"status":"[^"]*"' || echo "failed")
if [[ "$BACKEND_HEALTH" == *"ok"* ]] || [[ "$BACKEND_HEALTH" == *"healthy"* ]]; then
  echo -e "${GREEN}✓ Backend health check passed${NC}"
else
  echo -e "${YELLOW}⚠ Backend health check inconclusive${NC}"
fi

FRONTEND_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$FRONTEND_URL")
if [[ "$FRONTEND_STATUS" == "200" ]]; then
  echo -e "${GREEN}✓ Frontend health check passed${NC}"
else
  echo -e "${YELLOW}⚠ Frontend returned status: $FRONTEND_STATUS${NC}"
fi
echo ""

# Summary
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}   Deployment Complete!${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}Frontend:${NC} $FRONTEND_URL"
echo -e "${GREEN}Backend:${NC}  $BACKEND_URL"
echo -e "${GREEN}WebSocket:${NC} $WS_URL"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Visit $FRONTEND_URL"
echo "2. Install Chrome extension from Chrome Web Store"
echo "3. Press Q to connect"
echo "4. Press W to share screen"
echo "5. Say 'Hey Spectra' to start"
echo ""
echo -e "${GREEN}✨ Spectra is live!${NC}"
