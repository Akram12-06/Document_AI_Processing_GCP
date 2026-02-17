#!/bin/bash

# Configuration
PROJECT_ID="tss-gen-ai"
REGION="us-central1"
JOB_NAME="invoice-processor-job"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${JOB_NAME}"
SERVICE_ACCOUNT="642928170435-compute@developer.gserviceaccount.com"

echo "========================================="
echo "Deploying Invoice Processor Cloud Run Job"
echo "========================================="
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Job Name: ${JOB_NAME}"
echo "Service Account: ${SERVICE_ACCOUNT}"
echo "========================================="

# Step 1: Build and push Docker image
echo ""
echo "📦 Step 1: Building Docker image..."
gcloud builds submit --tag ${IMAGE_NAME} --project=${PROJECT_ID}

if [ $? -ne 0 ]; then
    echo "❌ Docker build failed!"
    exit 1
fi

echo "✅ Docker image built successfully"

# Step 2: Create/Update Cloud Run Job
echo ""
echo "🚀 Step 2: Deploying Cloud Run Job..."
gcloud run jobs deploy ${JOB_NAME} \
    --image ${IMAGE_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --service-account ${SERVICE_ACCOUNT} \
    --max-retries 2 \
    --task-timeout 30m \
    --memory 4Gi \
    --cpu 1

if [ $? -ne 0 ]; then
    echo "❌ Cloud Run Job deployment failed!"
    exit 1
fi

echo "✅ Cloud Run Job deployed successfully"

# Step 3: Execute job once to test
echo ""
echo "🧪 Step 3: Testing job execution..."
gcloud run jobs execute ${JOB_NAME} \
    --region ${REGION} \
    --project ${PROJECT_ID} \
    --wait

if [ $? -ne 0 ]; then
    echo "⚠️  Test execution failed - check logs"
else
    echo "✅ Test execution successful"
fi

# Step 4: Create Cloud Scheduler job (runs every 30 minutes)
echo ""
echo "⏰ Step 4: Setting up Cloud Scheduler..."

# Check if scheduler job exists
SCHEDULER_EXISTS=$(gcloud scheduler jobs list --project=${PROJECT_ID} --location=${REGION} --format="value(name)" 2>/dev/null | grep "invoice-processor-scheduler")

if [ -z "$SCHEDULER_EXISTS" ]; then
    echo "Creating new scheduler job..."
    gcloud scheduler jobs create http invoice-processor-scheduler \
        --location ${REGION} \
        --schedule "*/50 * * * *" \
        --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method POST \
        --oauth-service-account-email ${SERVICE_ACCOUNT} \
        --project ${PROJECT_ID}
else
    echo "Updating existing scheduler job..."
    gcloud scheduler jobs update http invoice-processor-scheduler \
        --location ${REGION} \
        --schedule "*/50 * * * *" \
        --uri "https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run" \
        --http-method POST \
        --oauth-service-account-email ${SERVICE_ACCOUNT} \
        --project ${PROJECT_ID}
fi

if [ $? -ne 0 ]; then
    echo "❌ Cloud Scheduler creation failed!"
    echo "   Note: You may need to enable Cloud Scheduler API"
    echo "   Run: gcloud services enable cloudscheduler.googleapis.com --project=${PROJECT_ID}"
    exit 1
fi

echo "✅ Cloud Scheduler created/updated successfully"

echo ""
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "📋 Job Details:"
echo "   Job Name: ${JOB_NAME}"
echo "   Schedule: Every 30 minutes (*/30 * * * *)"
echo "   Region: ${REGION}"
echo "   Service Account: ${SERVICE_ACCOUNT}"
echo ""
echo "🔧 Next Steps:"
echo "   1. Upload PDFs to: gs://${PROJECT_ID}/input/"
echo "   2. Monitor logs: ./manage_job.sh logs"
echo "   3. Check database for results"
echo ""
echo "📖 Useful Commands:"
echo "   View job details:    gcloud run jobs describe ${JOB_NAME} --region ${REGION}"
echo "   Execute job now:     gcloud run jobs execute ${JOB_NAME} --region ${REGION}"
echo "   View job logs:       ./manage_job.sh logs"
echo "   Pause scheduler:     ./manage_job.sh pause"
echo "   Resume scheduler:    ./manage_job.sh resume"
echo ""
echo "========================================="


