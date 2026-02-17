#!/bin/bash

# Frontend Cloud Run Deployment Script
set -e

# Configuration
PROJECT_ID="tss-gen-ai"
SERVICE_NAME="document-ai-frontend"
REGION="us-central1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
PORT=80

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying DocumentAI React Frontend to Cloud Run${NC}"
echo -e "${YELLOW}Project: ${PROJECT_ID}${NC}"
echo -e "${YELLOW}Service: ${SERVICE_NAME}${NC}"

# Check if .env file exists and source it
if [ -f ".env" ]; then
    source .env
    echo -e "${YELLOW}API Base URL: ${VITE_API_BASE_URL}${NC}"
fi

# Build and push using Cloud Build
echo -e "${YELLOW}Building and pushing Docker image with Cloud Build...${NC}"
gcloud builds submit \
    --config cloudbuild.yaml \
    --project $PROJECT_ID \
    --substitutions="_VITE_API_BASE_URL=${VITE_API_BASE_URL},_IMAGE_NAME=${IMAGE_NAME}"

# Deploy to Cloud Run
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --max-instances 10 \
    --timeout 300 \
    --port 80 \
    --project $PROJECT_ID

# Get service URL
SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)

echo -e "${GREEN}Deployment completed!${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"

# Test the deployment
echo -e "${YELLOW}Testing deployment...${NC}"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}" || echo "000")

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "${GREEN}✓ Health check passed${NC}"
else
    echo -e "${RED}✗ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo -e "${YELLOW}Check logs: gcloud logs read --service=${SERVICE_NAME} --project=${PROJECT_ID}${NC}"
fi

echo -e "${GREEN}Frontend deployment script completed${NC}"