"""Configuration settings for Document AI Invoice Processor"""

# GCP Configuration
PROJECT_ID = "tss-gen-ai"
PROCESSOR_ID = "af805e1b229eafbf"
LOCATION = "us-central1"

# GCS Configuration
BUCKET_NAME = "sample_invoice_bucket_coe"
INPUT_FOLDER = "input"
PROCESSED_FOLDER = "processed"
FAILED_FOLDER = "failed"

# Database Configuration
DB_CONFIG = {
    'host': '10.109.113.3',
    'port': 5432,
    'database': 'invoice_poc_db',
    'user': 'postgres',
    'password': 'Nextgenai@123'
}

# Required entities for validation
REQUIRED_ENTITIES = [
    'country',
    'customer_gst_number',
    'po_number',
    'customer_name',
    'invoice_number',
    'hsn_number',
    'invoice_currency',
    'invoice_date',
    'invoice_net_amount',
    'invoice_total_amount',
    'invoice_type',
    'payment_term',
    'vendor_name'
]

# Processing configuration
MIN_CONFIDENCE_THRESHOLD = 0.70  # 70% confidence threshold

# Working directory
WORKING_DIR = "/home/si_akram/document_ai_poc"
