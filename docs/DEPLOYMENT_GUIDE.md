# Spectra Deployment Guide

## Overview

This guide covers deployment procedures for Spectra's accessibility-enhanced components, including the vision system, location context handler, voice command processor, and performance monitoring system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Environment Configuration](#environment-configuration)
3. [Component Deployment](#component-deployment)
4. [Deployment Procedures](#deployment-procedures)
5. [Verification and Testing](#verification-and-testing)
6. [Rollback Procedures](#rollback-procedures)
7. [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Backend**: Python 3.11+, 1GB RAM minimum, 2GB recommended
- **Frontend**: Node.js 20+, 512MB RAM minimum
- **Cloud Platform**: Google Cloud Platform account with billing enabled
- **API Access**: Gemini API key with vision capabilities enabled

### Required Services

- Google Cloud Run (for hosting)
- Google Gemini API (for AI capabilities)
- Cloud Build (for container builds)
- Artifact Registry (for container storage)

### Access Requirements

- GCP project with Owner or Editor role
- Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
- gcloud CLI installed and authenticated

## Environment Configuration

### Backend Environment Variables

Create or update `backend/.env`:

```bash
# Required
GOOGLE_API_KEY=your_gemini_api_key_here
GCP_PROJECT_ID=your_gcp_project_id

# Optional - Performance Tuning
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
VISION_TIMEOUT=10                 # Vision API timeout in seconds
CACHE_TTL=5                       # Cache time-to-live in seconds
MAX_CACHE_SIZE=100                # Maximum cache entries
SLOW_RESPONSE_THRESHOLD=3.0       # Threshold for slow response alerts (seconds)

# Optional - Rate Limiting
MAX_RETRIES=3                     # Maximum retry attempts for failed API calls
RETRY_BASE_DELAY=0.5              # Base delay for exponential backoff (seconds)

# Optional - Monitoring
ENABLE_PERFORMANCE_MONITORING=true
ENABLE_ERROR_TRACKING=true
```

### Frontend Environment Variables

Create or update `frontend/.env.local`:

```bash
# Required
NEXT_PUBLIC_WS_URL=wss://your-backend-url.run.app/ws

# Optional - Development
NEXT_PUBLIC_DEBUG_MODE=false
NEXT_PUBLIC_LOG_LEVEL=info
```

### Production Environment Variables

For Cloud Run deployment, set environment variables using:

```bash
gcloud run services update spectra-backend \
  --region=us-central1 \
  --set-env-vars="GOOGLE_API_KEY=${GOOGLE_API_KEY},GCP_PROJECT_ID=${GCP_PROJECT_ID},LOG_LEVEL=INFO"
```

## Component Deployment

### 1. Enhanced Vision System

The enhanced vision system includes error handling, retry logic, and performance monitoring.

**Key Files:**
- `backend/app/error_handler.py` - Error handling and logging
- `backend/app/performance_monitor.py` - Performance tracking
- `backend/app/streaming/session.py` - Vision system integration

**Deployment Steps:**

1. Ensure all dependencies are installed:
```bash
cd backend
pip install -r requirements.txt
```

2. Verify error handler configuration:
```python
# In your session initialization
from app.error_handler import error_handler
from app.performance_monitor import get_performance_monitor

# Error handler is automatically initialized
# Performance monitor is available globally
```

3. Test vision system locally:
```bash
python -m pytest backend/tests/test_error_handler.py
python -m pytest backend/tests/test_performance_monitor.py
```

### 2. Location Context Handler

Handles "where am I?" queries for accessibility users.

**Key Files:**
- `backend/app/location_context_handler.py`
- `backend/tests/test_location_context_handler.py`

**Deployment Steps:**

1. Verify location handler integration in session:
```python
from app.location_context_handler import LocationContextHandler

# Handler is initialized in session
location_handler = LocationContextHandler()
```

2. Test location detection:
```bash
python -m pytest backend/tests/test_location_context_handler.py -v
```

3. Verify website indicators are up to date:
   - Review `website_indicators` dictionary in `location_context_handler.py`
   - Add new websites as needed for your user base

### 3. Voice Command Processor

Processes natural language voice commands with context awareness.

**Key Files:**
- `backend/app/voice_command_processor.py` (if implemented)
- `backend/tests/test_voice_command_processor.py`

**Deployment Steps:**

1. Verify command patterns are configured
2. Test command parsing:
```bash
python -m pytest backend/tests/test_voice_command_processor.py -v
```

### 4. Performance Monitoring System

Tracks vision API response times, cache hit rates, and action success rates.

**Key Files:**
- `backend/app/performance_monitor.py`
- `backend/tests/test_performance_monitor.py`

**Deployment Steps:**

1. Configure monitoring thresholds in environment variables
2. Verify metrics collection:
```bash
# Test performance monitoring
python -m pytest backend/tests/test_performance_monitor.py -v
```

3. Access performance metrics via health endpoint:
```bash
curl https://your-backend-url.run.app/health
```

## Deployment Procedures

### Local Development Deployment

1. **Start Backend:**
```bash
cd backend
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
uvicorn app.main:app --reload --port 8080
```

2. **Start Frontend:**
```bash
cd frontend
npm run dev
```

3. **Verify Services:**
- Backend: http://localhost:8080/health
- Frontend: http://localhost:3000

### Docker Deployment

1. **Build and Run with Docker Compose:**
```bash
docker-compose up --build
```

2. **Verify Containers:**
```bash
docker-compose ps
docker-compose logs backend
docker-compose logs frontend
```

### Google Cloud Run Deployment

#### Automated Deployment (Recommended)

Use the provided deployment script:

```bash
# Set environment variables
export GCP_PROJECT_ID=your-project-id
export GCP_REGION=us-central1
export GOOGLE_API_KEY=your-api-key

# Deploy both services
./infra/deploy.sh

# Deploy backend only
./infra/deploy.sh --backend-only

# Deploy frontend only
./infra/deploy.sh --frontend-only
```

#### Manual Deployment

**Backend Deployment:**

```bash
# Build container
cd backend
gcloud builds submit --tag=gcr.io/${GCP_PROJECT_ID}/spectra-backend

# Deploy to Cloud Run
gcloud run deploy spectra-backend \
  --image=gcr.io/${GCP_PROJECT_ID}/spectra-backend \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=1Gi \
  --cpu=2 \
  --timeout=300 \
  --concurrency=80 \
  --min-instances=0 \
  --max-instances=10 \
  --set-env-vars="GOOGLE_API_KEY=${GOOGLE_API_KEY},GCP_PROJECT_ID=${GCP_PROJECT_ID},LOG_LEVEL=INFO"
```

**Frontend Deployment:**

```bash
# Get backend URL
BACKEND_URL=$(gcloud run services describe spectra-backend \
  --region=us-central1 \
  --format="value(status.url)")

# Build container
cd frontend
gcloud builds submit --tag=gcr.io/${GCP_PROJECT_ID}/spectra-frontend

# Deploy to Cloud Run
gcloud run deploy spectra-frontend \
  --image=gcr.io/${GCP_PROJECT_ID}/spectra-frontend \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=512Mi \
  --cpu=1 \
  --timeout=60 \
  --set-env-vars="NEXT_PUBLIC_WS_URL=${BACKEND_URL/https/wss}/ws"
```

### Terraform Deployment

For infrastructure-as-code deployment:

```bash
cd infra

# Initialize Terraform
terraform init

# Plan deployment
terraform plan \
  -var="project_id=${GCP_PROJECT_ID}" \
  -var="region=us-central1" \
  -var="google_api_key=${GOOGLE_API_KEY}"

# Apply deployment
terraform apply \
  -var="project_id=${GCP_PROJECT_ID}" \
  -var="region=us-central1" \
  -var="google_api_key=${GOOGLE_API_KEY}"
```

## Verification and Testing

### Post-Deployment Verification

1. **Backend Health Check:**
```bash
curl https://your-backend-url.run.app/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "performance": {
    "vision_metrics": {
      "avg_response_time": 1.2,
      "success_rate": 98.5
    },
    "cache_metrics": {
      "hit_rate": 75.0
    }
  }
}
```

2. **Frontend Accessibility:**
```bash
# Visit frontend URL
open https://your-frontend-url.run.app

# Check for:
# - Page loads successfully
# - Microphone permission prompt appears
# - Screen sharing permission prompt appears
# - Voice activation works
```

3. **WebSocket Connection:**
```bash
# Test WebSocket connectivity
wscat -c wss://your-backend-url.run.app/ws
```

### Functional Testing

1. **Vision System Test:**
   - Share screen with test content
   - Ask "What's on screen?"
   - Verify accurate description

2. **Location Context Test:**
   - Navigate to Google.com
   - Ask "Where am I?"
   - Verify response: "You're on Google - search engine"

3. **Voice Command Test:**
   - Say "Click the search button"
   - Verify command is parsed and executed

4. **Performance Test:**
   - Check `/health` endpoint for performance metrics
   - Verify response times < 2 seconds
   - Verify cache hit rate > 70%

### Accessibility Testing

1. **Screen Reader Compatibility:**
   - Test with NVDA (Windows)
   - Test with JAWS (Windows)
   - Test with VoiceOver (macOS)

2. **Keyboard Navigation:**
   - Tab through all interactive elements
   - Verify Q/W/Escape shortcuts work
   - Verify focus indicators are visible

3. **Voice Activation:**
   - Test "Hey Spectra" wake word
   - Test continuous listening mode
   - Test barge-in functionality

## Rollback Procedures

### Cloud Run Rollback

If issues are detected after deployment:

```bash
# List revisions
gcloud run revisions list \
  --service=spectra-backend \
  --region=us-central1

# Rollback to previous revision
gcloud run services update-traffic spectra-backend \
  --region=us-central1 \
  --to-revisions=spectra-backend-00001-abc=100
```

### Docker Rollback

```bash
# Stop current containers
docker-compose down

# Checkout previous version
git checkout <previous-commit>

# Rebuild and restart
docker-compose up --build
```

### Database/State Rollback

Spectra is stateless - no database rollback needed. All state is in-memory and cleared on restart.

## Troubleshooting

### Common Deployment Issues

#### 1. API Key Issues

**Symptom:** "Invalid API key" errors in logs

**Solution:**
```bash
# Verify API key is set
echo $GOOGLE_API_KEY

# Update Cloud Run service
gcloud run services update spectra-backend \
  --region=us-central1 \
  --set-env-vars="GOOGLE_API_KEY=${GOOGLE_API_KEY}"

# Verify API key has Gemini access
# Visit https://aistudio.google.com/app/apikey
```

#### 2. WebSocket Connection Failures

**Symptom:** Frontend cannot connect to backend

**Solution:**
```bash
# Verify backend URL is correct
gcloud run services describe spectra-backend \
  --region=us-central1 \
  --format="value(status.url)"

# Update frontend environment variable
gcloud run services update spectra-frontend \
  --region=us-central1 \
  --set-env-vars="NEXT_PUBLIC_WS_URL=wss://your-backend-url.run.app/ws"
```

#### 3. Memory Issues

**Symptom:** Container crashes with OOM errors

**Solution:**
```bash
# Increase memory allocation
gcloud run services update spectra-backend \
  --region=us-central1 \
  --memory=2Gi

# Monitor memory usage
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=spectra-backend" \
  --limit=50 \
  --format=json
```

#### 4. Slow Response Times

**Symptom:** Vision API calls taking > 3 seconds

**Solution:**
1. Check performance metrics: `curl https://your-backend-url.run.app/health`
2. Review cache hit rate (should be > 70%)
3. Check Gemini API status: https://status.cloud.google.com/
4. Consider increasing CPU allocation:
```bash
gcloud run services update spectra-backend \
  --region=us-central1 \
  --cpu=4
```

#### 5. Rate Limiting

**Symptom:** "Rate limit exceeded" errors

**Solution:**
1. Check Gemini API quota: https://console.cloud.google.com/apis/api/generativelanguage.googleapis.com/quotas
2. Implement request throttling
3. Increase cache TTL to reduce API calls:
```bash
gcloud run services update spectra-backend \
  --region=us-central1 \
  --set-env-vars="CACHE_TTL=10"
```

### Deployment Logs

**View Cloud Run Logs:**
```bash
# Backend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=spectra-backend" \
  --limit=100 \
  --format=json

# Frontend logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=spectra-frontend" \
  --limit=100 \
  --format=json
```

**View Build Logs:**
```bash
gcloud builds list --limit=10
gcloud builds log <BUILD_ID>
```

## Deployment Automation Scripts

### Available Scripts

The following scripts are available in the `infra/` directory:

#### deploy.sh
Main deployment script for Cloud Run deployment.
```bash
./infra/deploy.sh [--backend-only | --frontend-only]
```

#### setup-monitoring.sh
Configures monitoring, alerting, and log-based metrics.
```bash
export ALERT_EMAIL=alerts@example.com
./infra/setup-monitoring.sh
```

#### create-dashboard.sh
Creates a comprehensive performance dashboard in Cloud Monitoring.
```bash
./infra/create-dashboard.sh
```

#### verify-deployment.sh
Verifies deployment health and performance metrics.
```bash
./infra/verify-deployment.sh
```

#### rollback.sh
Automated rollback to previous revision.
```bash
./infra/rollback.sh --backend --frontend --revision=previous
```

### Deployment Workflow

**Standard Deployment:**
```bash
# 1. Deploy services
./infra/deploy.sh

# 2. Setup monitoring (first time only)
export ALERT_EMAIL=your-email@example.com
./infra/setup-monitoring.sh

# 3. Create dashboard (first time only)
./infra/create-dashboard.sh

# 4. Verify deployment
./infra/verify-deployment.sh
```

**Rollback Workflow:**
```bash
# 1. Execute rollback
./infra/rollback.sh --backend --frontend --revision=previous

# 2. Verify rollback
./infra/verify-deployment.sh

# 3. Monitor post-rollback
watch -n 5 'curl -s ${BACKEND_URL}/health | jq .performance'
```

## Deployment Checklist

Before deploying to production, review the comprehensive deployment checklist:

**Location:** `infra/DEPLOYMENT_CHECKLIST.md`

**Key sections:**
- Pre-deployment verification
- Deployment execution steps
- Post-deployment validation
- Rollback procedures
- Emergency procedures

## Rollback Procedures

Detailed rollback procedures are documented in:

**Location:** `infra/ROLLBACK_PROCEDURES.md`

**Includes:**
- Quick rollback commands
- Rollback decision matrix
- Component-specific rollback procedures
- Verification procedures
- Post-rollback actions

## Monitoring Configuration

Monitoring and alerting configuration is defined in:

**Location:** `infra/monitoring-config.yaml`

**Includes:**
- Alert policies for critical metrics
- Custom metrics definitions
- Log-based metrics
- Dashboard configuration
- Performance targets

## Next Steps

After successful deployment:

1. Review [Monitoring and Alerting Guide](MONITORING_GUIDE.md)
2. Complete [Deployment Checklist](../infra/DEPLOYMENT_CHECKLIST.md)
3. Review [Rollback Procedures](../infra/ROLLBACK_PROCEDURES.md)
4. Set up [Maintenance Procedures](MAINTENANCE_GUIDE.md)
5. Configure [Performance Tuning](PERFORMANCE_TUNING_GUIDE.md)

## Support

For deployment issues:
- Check [Troubleshooting Guide](TROUBLESHOOTING.md)
- Review [Rollback Procedures](../infra/ROLLBACK_PROCEDURES.md)
- Review [Developer Guide](DEVELOPER_GUIDE.md)
- Contact: support@aqta.ai
