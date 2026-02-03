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

# Exception codes for document validation failures
EXCEPTION_CODES = {
    'MISSING_ENTITIES': 'MISS_ENT',
    'LOW_CONFIDENCE': 'LOW_CONF', 
    'NETWORK_ERROR': 'NET_ERR',
    'PROCESSING_ERROR': 'PROC_ERR',
    'FILE_NOT_FOUND': 'FILE_ERR',
    'DOCUMENT_AI_ERROR': 'DOC_AI_ERR',
    'INVALID_FORMAT': 'INV_FMT',
    'TIMEOUT_ERROR': 'TIMEOUT',
    'AUTH_ERROR': 'AUTH_ERR',
    'QUOTA_EXCEEDED': 'QUOTA_ERR',
    'MIXED_VALIDATION': 'MIX_VAL'  # Both missing entities and low confidence
}

# Exception descriptions mapping
EXCEPTION_DESCRIPTIONS = {
    'MISS_ENT': 'Required entities are missing from the document',
    'LOW_CONF': 'Extracted entities have confidence below threshold',
    'NET_ERR': 'Network connectivity issues during processing',
    'PROC_ERR': 'General processing error occurred',
    'FILE_ERR': 'File not found or inaccessible in GCS',
    'DOC_AI_ERR': 'Document AI service error',
    'INV_FMT': 'Invalid document format or corrupted file',
    'TIMEOUT': 'Processing timeout exceeded',
    'AUTH_ERR': 'Authentication or authorization error',
    'QUOTA_ERR': 'API quota or rate limit exceeded',
    'MIX_VAL': 'Multiple validation issues: missing entities and low confidence'
}

def get_exception_details(missing_entities=None, low_confidence_entities=None, min_confidence=None):
    """
    Generate exception code, description, and entity details based on validation results
    
    Args:
        missing_entities: List of missing required entities
        low_confidence_entities: List of entities with confidence below threshold
        min_confidence: Minimum confidence among all extracted entities
        
    Returns:
        Tuple of (exception_code, exception_description, exception_entities_json)
    """
    has_missing = missing_entities and len(missing_entities) > 0
    has_low_conf = low_confidence_entities and len(low_confidence_entities) > 0
    
    # Prepare exception entities JSON
    exception_entities = {
        "missing": missing_entities or [],
        "low_confidence": []
    }
    
    # Format low confidence entities with details
    if low_confidence_entities:
        for entity in low_confidence_entities:
            if isinstance(entity, dict):
                exception_entities["low_confidence"].append({
                    "name": entity.get("name"),
                    "confidence": entity.get("confidence"),
                    "threshold": MIN_CONFIDENCE_THRESHOLD
                })
            else:
                exception_entities["low_confidence"].append({
                    "name": str(entity),
                    "confidence": None,
                    "threshold": MIN_CONFIDENCE_THRESHOLD
                })
    
    # Add min_confidence info if provided
    if min_confidence is not None:
        exception_entities["min_confidence"] = min_confidence
        exception_entities["confidence_threshold"] = MIN_CONFIDENCE_THRESHOLD
    
    if has_missing and has_low_conf:
        code = EXCEPTION_CODES['MIXED_VALIDATION']
        desc = f"Missing entities: {missing_entities}; Low confidence entities: {[e['name'] if isinstance(e, dict) else e for e in low_confidence_entities]}"
    elif has_missing:
        code = EXCEPTION_CODES['MISSING_ENTITIES'] 
        desc = f"Missing required entities: {missing_entities}"
    elif has_low_conf:
        code = EXCEPTION_CODES['LOW_CONFIDENCE']
        low_conf_names = [e['name'] if isinstance(e, dict) else e for e in low_confidence_entities]
        desc = f"Low confidence entities (< {MIN_CONFIDENCE_THRESHOLD}): {low_conf_names}"
    elif min_confidence is not None and min_confidence < MIN_CONFIDENCE_THRESHOLD:
        code = EXCEPTION_CODES['LOW_CONFIDENCE']
        desc = f"Minimum confidence ({min_confidence:.2f}) below threshold ({MIN_CONFIDENCE_THRESHOLD})"
        exception_entities["reason"] = "min_confidence_below_threshold"
    else:
        return None, None, None
        
    return code, desc, exception_entities

def calculate_min_confidence(entities):
    """
    Calculate minimum confidence from list of extracted entities
    
    Args:
        entities: List of entity dictionaries with confidence scores
        
    Returns:
        Minimum confidence score (float) or None if no entities
    """
    if not entities:
        return None
    
    confidences = []
    for entity in entities:
        confidence = entity.get('confidence')
        if confidence is not None:
            confidences.append(confidence)
    
    return min(confidences) if confidences else None

def determine_document_status(missing_entities, low_confidence_entities, min_confidence):
    """
    Determine document status based on validation results
    
    Args:
        missing_entities: List of missing entities
        low_confidence_entities: List of low confidence entities  
        min_confidence: Minimum confidence score
        
    Returns:
        Document status: 'SUCCESS', 'FAILED', or 'PENDING_REVIEW'
    """
    has_missing = missing_entities and len(missing_entities) > 0
    has_low_conf = low_confidence_entities and len(low_confidence_entities) > 0
    
    if has_missing:
        return 'FAILED'  # Missing entities = hard failure
    elif has_low_conf:
        return 'PENDING_REVIEW'  # Low confidence = needs review
    elif min_confidence is not None and min_confidence < MIN_CONFIDENCE_THRESHOLD:
        return 'PENDING_REVIEW'  # Overall confidence too low = needs review
    else:
        return 'SUCCESS'  # All good

# Working directory
WORKING_DIR = "/home/si_akram/document_ai_poc"
