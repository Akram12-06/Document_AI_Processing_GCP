#!/bin/bash

PROJECT_ID="tss-gen-ai"

echo "Enabling required APIs for project: ${PROJECT_ID}"
echo "========================================="

# Enable Cloud Run API
echo "Enabling Cloud Run API..."
gcloud services enable run.googleapis.com --project=${PROJECT_ID}

# Enable Cloud Scheduler API
echo "Enabling Cloud Scheduler API..."
gcloud services enable cloudscheduler.googleapis.com --project=${PROJECT_ID}

# Enable Cloud Build API
echo "Enabling Cloud Build API..."
gcloud services enable cloudbuild.googleapis.com --project=${PROJECT_ID}

# Enable Container Registry API
echo "Enabling Container Registry API..."
gcloud services enable containerregistry.googleapis.com --project=${PROJECT_ID}

# Enable Document AI API (should already be enabled)
echo "Enabling Document AI API..."
gcloud services enable documentai.googleapis.com --project=${PROJECT_ID}

# Enable Cloud SQL Admin API (should already be enabled)
echo "Enabling Cloud SQL Admin API..."
gcloud services enable sqladmin.googleapis.com --project=${PROJECT_ID}

echo ""
echo "✅ All APIs enabled successfully!"
echo ""
