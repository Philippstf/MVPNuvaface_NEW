#!/bin/bash
# Medical AI Assistant Direct Deployment Script

echo "🏥 Deploying Medical AI Assistant Backend..."

# Navigate to backend directory
cd "$(dirname "$0")"

# Deploy using gcloud (make sure we're in backend/ directory)
gcloud run deploy nuvaface-medical-assistant \
  --source=. \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --timeout=600 \
  --max-instances=10 \
  --min-instances=0 \
  --concurrency=80 \
  --set-env-vars=PYTHONPATH=/app

echo "✅ Medical AI Assistant Backend deployed!"