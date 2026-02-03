#!/bin/bash

# Deploy FastAPI backend to Cloud Run
# This script builds and deploys the FastAPI backend service

set -e

# Configuration from config.py
PROJECT_ID="tss-gen-ai"
REGION="us-central1"
SERVICE_NAME="document-ai-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
SERVICE_ACCOUNT="642928170435-compute@developer.gserviceaccount.com"

# Configuration values from config.py
BUCKET_NAME="sample_invoice_bucket_coe"
INPUT_FOLDER="input"
PROCESSED_FOLDER="processed"
FAILED_FOLDER="failed"
DB_HOST="10.109.113.3"
DB_PORT="5432"
DB_NAME="invoice_poc_db"
DB_USER="postgres"
DB_PASSWORD="Nextgenai@123"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying DocumentAI FastAPI Backend to Cloud Run${NC}"
echo -e "${YELLOW}Project: ${PROJECT_ID}${NC}"
echo -e "${YELLOW}Bucket: ${BUCKET_NAME}${NC}"
echo -e "${YELLOW}Service Account: ${SERVICE_ACCOUNT}${NC}"

# Build and push using Cloud Build
echo -e "${YELLOW}Building and pushing Docker image with Cloud Build...${NC}"
# Copy Dockerfile.api to Dockerfile for Cloud Build
cp Dockerfile.api Dockerfile
gcloud builds submit \
    --tag $IMAGE_NAME \
    --project $PROJECT_ID
# Clean up
rm Dockerfile

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --service-account $SERVICE_ACCOUNT \
    --memory 2Gi \
    --cpu 1 \
    --concurrency 80 \
    --max-instances 10 \
    --timeout 300 \
    --project $PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)

echo -e "${GREEN}Deployment completed!${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"
echo -e "${YELLOW}API Documentation: ${SERVICE_URL}/docs${NC}"

# Test the deployment
echo -e "${YELLOW}Testing deployment...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/api/health" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}Check logs: gcloud logs read --service=${SERVICE_NAME} --project=${PROJECT_ID}${NC}"
fi

echo -e "${GREEN}Deployment script completed${NC}"
