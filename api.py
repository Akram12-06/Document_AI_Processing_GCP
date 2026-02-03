"""
FastAPI backend for DocumentAI Processing System UI
Provides REST API endpoints for the web interface
"""
from fastapi import FastAPI, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict, Any
import logging
import os
import sys
import io
from datetime import datetime, date
from pydantic import BaseModel
import asyncio
import psycopg2
from src.database_service import DatabaseService
from src.gcs_file_manager import GCSFileManager
import config.config as config
from concurrent.futures import ThreadPoolExecutor
from google.cloud import storage
import tempfile
import subprocess

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.database_service import DatabaseService
from src.gcs_file_manager import GCSFileManager
from src.invoice_processor import InvoiceProcessor
from config.config import BUCKET_NAME, INPUT_FOLDER, PROCESSED_FOLDER

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="DocumentAI Processing API",
    description="REST API for DocumentAI invoice processing system",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=config.DATABASE_HOST,
        database=config.DATABASE_NAME,
        user=config.DATABASE_USER,
        password=config.DATABASE_PASSWORD,
        port=config.DATABASE_PORT
    )

# Initialize services
db_service = DatabaseService()
gcs_manager = GCSFileManager()
invoice_processor = InvoiceProcessor()

# Thread pool for background tasks
executor = ThreadPoolExecutor(max_workers=4)

# Pydantic models for API responses
class DocumentTableRow(BaseModel):
    """Model for table display with required fields"""
    id: int
    file_name: str
    invoice_type: Optional[str] = None
    date_received: datetime  # When stored in GCS
    document_status: Optional[str] = None
    min_confidence: Optional[float] = None
    processing_status: str
    exception_reason_code: Optional[str] = None

class DocumentSummary(BaseModel):
    id: int
    file_name: str
    po_number: Optional[str] = None
    supplier_name: Optional[str] = None
    invoice_type: Optional[str] = None
    processing_status: str
    document_status: Optional[str] = None
    min_confidence: Optional[float] = None
    exception_reason_code: Optional[str] = None
    exception_reason_description: Optional[str] = None
    invoice_date: Optional[str] = None
    date_received: datetime
    created_at: datetime
    error_message: Optional[str] = None

class DocumentDetail(BaseModel):
    id: int
    file_name: str
    gcs_path: str
    processing_status: str
    document_status: Optional[str] = None
    min_confidence: Optional[float] = None
    exception_reason_code: Optional[str] = None
    exception_reason_description: Optional[str] = None
    exception_entities: Optional[List[Dict[str, Any]]] = None  # Changed to List
    invoice_type: Optional[str] = None
    date_received: datetime
    created_at: datetime
    updated_at: datetime
    error_message: Optional[str] = None
    entities: List[Dict[str, Any]]
    has_raw_output: Optional[bool] = False  # Made optional with default
    total_entities: Optional[int] = 0  # Made optional with default
    pdf_url: Optional[str] = None  # For PDF viewer

class EntityField(BaseModel):
    name: str
    value: str
    confidence: float
    page_number: Optional[int] = None
    bounding_box: Optional[Dict[str, Any]] = None

class ProcessingStats(BaseModel):
    total_documents: int
    successful: int
    failed: int
    processing_failed: int
    validation_failed: int
    pending_review: int
    recent_uploads: int
    avg_min_confidence: Optional[float] = None

class UploadResponse(BaseModel):
    success: bool
    message: str
    uploaded_files: List[Dict[str, Any]]  # Enhanced with file details
    failed_files: List[Dict[str, str]]

class ProcessingTriggerResponse(BaseModel):
    success: bool
    message: str
    triggered_files: List[str]
    job_id: Optional[str] = None


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "DocumentAI Processing API", 
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conn = db_service.get_connection()
        conn.close()
        
        # Test GCS connection
        gcs_manager.client.list_blobs(gcs_manager.bucket_name, max_results=1)
        
        return {
            "status": "healthy",
            "database": "connected",
            "gcs": "connected",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")


@app.get("/api/documents/table", response_model=List[DocumentTableRow])
async def get_documents_table(
    status: Optional[str] = Query(None, description="Filter by document status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get documents formatted for table display"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Query for table display with required fields
        query = """
        SELECT 
            dp.id,
            dp.file_name,
            dp.document_status,
            dp.min_confidence,
            dp.processing_status,
            dp.exception_reason_code,
            dp.created_at as date_received,
            invoice_type.entity_value as invoice_type
        FROM document_processing dp
        LEFT JOIN extracted_entities invoice_type 
            ON dp.id = invoice_type.processing_id 
            AND invoice_type.entity_name = 'invoice_type'
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if status:
            query += " AND dp.document_status = %s"
            params.append(status)
        
        query += " ORDER BY dp.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        documents = []
        for row in results:
            documents.append(DocumentTableRow(
                id=row[0],
                file_name=row[1],
                document_status=row[2],
                min_confidence=row[3],
                processing_status=row[4],
                exception_reason_code=row[5],
                date_received=row[6],
                invoice_type=row[7]
            ))
        
        cursor.close()
        conn.close()
        
        return documents
        
    except Exception as e:
        logger.error(f"Failed to get documents table: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@app.get("/api/documents/stats", response_model=ProcessingStats)
async def get_processing_stats():
    """Get enhanced dashboard statistics"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Enhanced statistics query
        cursor.execute("""
            SELECT 
                COUNT(*) as total_documents,
                COUNT(CASE WHEN processing_status = 'SUCCESS' AND document_status = 'SUCCESS' THEN 1 END) as successful,
                COUNT(CASE WHEN processing_status = 'FAILED' THEN 1 END) as processing_failed,
                COUNT(CASE WHEN document_status = 'FAILED' THEN 1 END) as validation_failed,
                COUNT(CASE WHEN document_status = 'PENDING_REVIEW' THEN 1 END) as pending_review,
                AVG(min_confidence) as avg_min_confidence
            FROM document_processing
            WHERE created_at >= NOW() - INTERVAL '30 days'
        """)
        
        stats = cursor.fetchone()
        
        # Recent uploads (last 7 days)
        cursor.execute("""
            SELECT COUNT(*) FROM document_processing 
            WHERE created_at >= NOW() - INTERVAL '7 days'
        """)
        recent_uploads = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return ProcessingStats(
            total_documents=stats[0] or 0,
            successful=stats[1] or 0,
            failed=stats[2] or 0,  # Only processing failures
            processing_failed=stats[2] or 0,
            validation_failed=stats[3] or 0,
            pending_review=stats[4] or 0,
            recent_uploads=recent_uploads,
            avg_min_confidence=float(stats[5]) if stats[5] else None
        )
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")


@app.get("/api/documents/{document_id}/pdf")
async def get_document_pdf(document_id: int):
    """Get PDF file for viewing"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Get document info
        cursor.execute("""
            SELECT gcs_path, file_name FROM document_processing WHERE id = %s
        """, (document_id,))
        
        result = cursor.fetchone()
        if not result:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        gcs_path, file_name = result
        cursor.close()
        conn.close()
        
        # Parse GCS path (format: gs://bucket/path/to/file)
        if gcs_path.startswith('gs://'):
            path_parts = gcs_path[5:].split('/', 1)  # Remove gs:// and split
            bucket_name = path_parts[0]
            blob_path = path_parts[1] if len(path_parts) > 1 else ''
        else:
            # If gcs_path is just the blob path, use the default bucket
            bucket_name = config.GCS_BUCKET
            blob_path = gcs_path
        
        # Create storage client and get blob
        from google.cloud import storage
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_path)
        
        if not blob.exists():
            raise HTTPException(status_code=404, detail="PDF file not found in storage")
        
        # Stream the PDF
        pdf_content = blob.download_as_bytes()
        
        return StreamingResponse(
            io.BytesIO(pdf_content),
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename={file_name}"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get PDF: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve PDF")


@app.get("/api/documents", response_model=List[DocumentSummary])
async def get_documents(
    file_name: Optional[str] = Query(None, description="Filter by file name"),
    po_number: Optional[str] = Query(None, description="Filter by PO number"),
    supplier_name: Optional[str] = Query(None, description="Filter by supplier name"),
    document_status: Optional[str] = Query(None, description="Filter by document status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get list of all processed documents with enhanced filters"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Enhanced query with all required fields
        query = """
        SELECT DISTINCT
            dp.id,
            dp.file_name,
            dp.processing_status,
            dp.document_status,
            dp.min_confidence,
            dp.exception_reason_code,
            dp.exception_reason_description,
            dp.created_at,
            dp.updated_at,
            dp.error_message,
            po.entity_value as po_number,
            supplier.entity_value as supplier_name,
            inv_date.entity_value as invoice_date,
            inv_type.entity_value as invoice_type
        FROM document_processing dp
        LEFT JOIN extracted_entities po ON dp.id = po.processing_id AND po.entity_name = 'po_number'
        LEFT JOIN extracted_entities supplier ON dp.id = supplier.processing_id AND supplier.entity_name = 'vendor_name'
        LEFT JOIN extracted_entities inv_date ON dp.id = inv_date.processing_id AND inv_date.entity_name = 'invoice_date'
        LEFT JOIN extracted_entities inv_type ON dp.id = inv_type.processing_id AND inv_type.entity_name = 'invoice_type'
        WHERE 1=1
        """
        
        params = []
        
        # Add filters
        if file_name:
            query += " AND dp.file_name ILIKE %s"
            params.append(f"%{file_name}%")
            
        if po_number:
            query += " AND po.entity_value ILIKE %s"
            params.append(f"%{po_number}%")
            
        if supplier_name:
            query += " AND supplier.entity_value ILIKE %s"
            params.append(f"%{supplier_name}%")
            
        if document_status:
            query += " AND dp.document_status = %s"
            params.append(document_status)
        
        # Add ordering and pagination
        query += " ORDER BY dp.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        results = cursor.fetchall()
        
        documents = []
        for row in results:
            documents.append(DocumentSummary(
                id=row[0],
                file_name=row[1],
                processing_status=row[2],
                document_status=row[3],
                min_confidence=row[4],
                exception_reason_code=row[5],
                exception_reason_description=row[6],
                created_at=row[7],
                date_received=row[7],  # Same as created_at for now
                updated_at=row[8],
                error_message=row[9],
                po_number=row[10],
                supplier_name=row[11],
                invoice_date=row[12],
                invoice_type=row[13]
            ))
        
        cursor.close()
        conn.close()
        
        return documents
        
    except Exception as e:
        logger.error(f"Failed to get documents: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve documents")


@app.get("/api/documents/{document_id}", response_model=DocumentDetail)
async def get_document_detail(document_id: int):
    """Get detailed information for a specific document"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Get document processing record
        cursor.execute("""
            SELECT id, file_name, gcs_path, processing_status, 
                   document_status, min_confidence, exception_reason_code, 
                   exception_reason_description, exception_entities, 
                   created_at, updated_at, error_message
            FROM document_processing 
            WHERE id = %s
        """, (document_id,))
        
        doc_result = cursor.fetchone()
        if not doc_result:
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Document not found")
        
        # Get extracted entities
        cursor.execute("""
            SELECT entity_name, entity_value, confidence_score, page_number
            FROM extracted_entities 
            WHERE processing_id = %s
            ORDER BY entity_name, confidence_score DESC
        """, (document_id,))
        
        entity_results = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        # Build entities list
        entities_list = []
        for row in entity_results:
            entities_list.append({
                'entity_name': row[0],
                'entity_value': row[1],
                'confidence': row[2],
                'page_number': row[3]
            })
        
        # Parse exception entities JSON if present
        exception_entities = []
        if doc_result[8]:  # exception_entities column (adjusted index)
            import json
            try:
                exception_entities = json.loads(doc_result[8])
            except:
                pass
        
        return DocumentDetail(
            id=doc_result[0],
            file_name=doc_result[1],
            gcs_path=doc_result[2],
            processing_status=doc_result[3],
            document_status=doc_result[4],
            min_confidence=doc_result[5],
            exception_reason_code=doc_result[6],
            exception_reason_description=doc_result[7],
            created_at=doc_result[9],
            updated_at=doc_result[10],
            error_message=doc_result[11],
            entities=entities_list,
            exception_entities=exception_entities,
            pdf_url=f"/api/documents/{document_id}/pdf",
            date_received=doc_result[9],  # Use created_at as date_received
            has_raw_output=len(entities_list) > 0,  # Set based on data availability
            total_entities=len(entities_list)  # Count of entities
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document detail: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document details")





@app.get("/api/documents/{document_id}/raw")
async def get_document_raw_output(document_id: int):
    """Get raw DocumentAI output for a specific document"""
    try:
        raw_data = db_service.get_raw_processor_output(document_id)
        
        if not raw_data:
            raise HTTPException(status_code=404, detail="Raw output not found")
        
        return raw_data['raw_processor_output']
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get raw output: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve raw output")


@app.post("/api/upload", response_model=UploadResponse)
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple PDF files to GCS input folder"""
    try:
        uploaded_files = []
        failed_files = []
        
        bucket = gcs_manager.client.bucket(gcs_manager.bucket_name)
        
        for file in files:
            try:
                # Validate file type
                if not file.filename.lower().endswith('.pdf'):
                    failed_files.append(f"{file.filename}: Not a PDF file")
                    continue
                
                # Read file content
                content = await file.read()
                
                # Upload to GCS input folder
                blob_name = f"{gcs_manager.input_folder}/{file.filename}"
                blob = bucket.blob(blob_name)
                
                blob.upload_from_string(content, content_type="application/pdf")
                uploaded_files.append(file.filename)
                
                logger.info(f"Uploaded file: {file.filename}")
                
            except Exception as e:
                failed_files.append(f"{file.filename}: {str(e)}")
                logger.error(f"Failed to upload {file.filename}: {str(e)}")
        
        return UploadResponse(
            success=len(uploaded_files) > 0,
            message=f"Uploaded {len(uploaded_files)} files, {len(failed_files)} failed",
            uploaded_files=uploaded_files,
            failed_files=failed_files
        )
        
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Upload failed")


@app.post("/api/trigger-processing", response_model=ProcessingTriggerResponse)
async def trigger_processing():
    """Trigger the Cloud Run job for processing uploaded files"""
    try:
        # You can implement this in several ways:
        # 1. Call the Cloud Run job URL directly
        # 2. Use Cloud Scheduler API to trigger the job
        # 3. Run the processing directly (for testing)
        
        # For now, let's run processing directly in background
        async def run_processing():
            try:
                summary = invoice_processor.process_all_invoices()
                logger.info(f"Processing completed: {summary}")
                return summary
            except Exception as e:
                logger.error(f"Processing failed: {str(e)}")
                raise
        
        # Run in background
        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(executor, lambda: invoice_processor.process_all_invoices())
        
        return ProcessingTriggerResponse(
            success=True,
            message="Processing job started",
            job_url=None  # Could include Cloud Run job URL
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger processing: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to trigger processing")


@app.get("/api/processing/status")
async def get_processing_status():
    """Get current processing status"""
    try:
        # Get recent processing activity
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                processing_status,
                COUNT(*) as count,
                MAX(created_at) as last_processed
            FROM document_processing 
            WHERE created_at >= NOW() - INTERVAL '1 hour'
            GROUP BY processing_status
        """)
        
        recent_activity = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return {
            "recent_activity": [
                {
                    "status": row[0],
                    "count": row[1],
                    "last_processed": row[2]
                }
                for row in recent_activity
            ]
        }
        
    except Exception as e:
        logger.error(f"Failed to get processing status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to get processing status")




@app.post("/api/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """Upload multiple files to GCS staging area"""
    uploaded_files = []
    
    try:
        for file in files:
            # Validate file type
            if not file.filename.lower().endswith('.pdf'):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Only PDF files are allowed. Invalid file: {file.filename}"
                )
            
            # Upload to GCS staging bucket
            staging_bucket = config.STAGING_BUCKET
            file_key = f"staging/{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
            
            gcs_manager = GCSFileManager()
            gcs_url = await gcs_manager.upload_file(
                file.file, 
                staging_bucket, 
                file_key
            )
            
            uploaded_files.append({
                "file_name": file.filename,
                "file_key": file_key,
                "gcs_url": gcs_url,
                "size": file.size,
                "upload_time": datetime.utcnow().isoformat()
            })
            
    except Exception as e:
        logger.error(f"Upload failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
    
    return {"uploaded_files": uploaded_files}

@app.post("/api/trigger-processing")
async def trigger_processing(file_keys: List[str]):
    """Trigger document processing for uploaded files"""
    try:
        processing_results = []
        
        for file_key in file_keys:
            # Move file from staging to processing bucket
            gcs_manager = GCSFileManager()
            final_key = file_key.replace("staging/", "")
            
            # Move file
            success = await gcs_manager.move_file(
                config.STAGING_BUCKET, file_key,
                config.GCS_BUCKET, final_key
            )
            
            if success:
                # Trigger processing
                from src.invoice_processor import InvoiceProcessor
                processor = InvoiceProcessor()
                
                result = await processor.process_document(
                    bucket_name=config.GCS_BUCKET,
                    file_name=final_key
                )
                
                processing_results.append({
                    "file_key": file_key,
                    "processing_id": result.get("processing_id"),
                    "status": "processing_started"
                })
            else:
                processing_results.append({
                    "file_key": file_key,
                    "status": "failed_to_move",
                    "error": "Could not move file to processing bucket"
                })
        
        return {"processing_results": processing_results}
        
    except Exception as e:
        logger.error(f"Processing trigger failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to trigger processing: {str(e)}")

@app.get("/api/stats")
async def get_dashboard_stats():
    """Get dashboard statistics"""
    try:
        conn = db_service.get_connection()
        cursor = conn.cursor()
        
        # Get document counts by status
        cursor.execute("""
            SELECT document_status, COUNT(*) 
            FROM document_processing 
            GROUP BY document_status
        """)
        status_counts = dict(cursor.fetchall())
        
        # Get average confidence
        cursor.execute("""
            SELECT AVG(min_confidence) 
            FROM document_processing 
            WHERE min_confidence IS NOT NULL
        """)
        avg_confidence = cursor.fetchone()[0] or 0
        
        # Get recent activity (last 24 hours)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM document_processing 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
        """)
        recent_activity = cursor.fetchone()[0] or 0
        
        # Get total processed documents
        cursor.execute("SELECT COUNT(*) FROM document_processing")
        total_documents = cursor.fetchone()[0] or 0
        
        cursor.close()
        conn.close()
        
        return {
            "total_documents": total_documents,
            "status_breakdown": status_counts,
            "average_confidence": round(float(avg_confidence), 2) if avg_confidence else 0,
            "recent_activity": recent_activity,
            "success_rate": round(
                (status_counts.get("SUCCESS", 0) / max(total_documents, 1)) * 100, 2
            )
        }
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve statistics")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
