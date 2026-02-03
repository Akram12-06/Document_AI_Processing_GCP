"""Main invoice processing pipeline"""
import logging
from typing import Dict, Optional
import os
import sys
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.document_ai_processor import DocumentAIProcessor
from src.database_service import DatabaseService
from src.gcs_file_manager import GCSFileManager
from config.config import (get_exception_details, EXCEPTION_CODES, calculate_min_confidence, 
                          determine_document_status, MIN_CONFIDENCE_THRESHOLD)

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class InvoiceProcessor:
    """Complete invoice processing pipeline"""
    
    def __init__(self):
        self.doc_ai = DocumentAIProcessor()
        self.db = DatabaseService()
        self.gcs = GCSFileManager()
        
        logger.info("Invoice Processor initialized successfully")
    
    def process_single_invoice(self, file_name: str) -> Dict:
        """
        Process a single invoice file
        
        Args:
            file_name: Name of the file in GCS input folder (just filename, not full path)
            
        Returns:
            Dictionary with processing results
        """
        # Clean the filename - remove any path components
        file_name = os.path.basename(file_name)
        
        start_time = datetime.now()
        logger.info(f"{'=' * 80}")
        logger.info(f"Starting processing: {file_name}")
        logger.info(f"{'=' * 80}")
        
        result = {
            'file_name': file_name,
            'processing_status': 'PROCESSING',  # Document AI processing status
            'document_status': 'PENDING',       # Document validation status
            'processing_id': None,
            'error_message': None,
            'min_confidence': None,
            'exception_reason_code': None,
            'exception_reason_description': None,
            'exception_entities': None,
            'total_entities': 0,
            'unique_entity_types': 0,
            'avg_confidence': 0,
            'validation': {},
            'statistics': {},
            'processing_time_seconds': 0
        }
        
        try:
            # Step 1: Verify file exists
            logger.info("Step 1: Verifying file exists...")
            if not self.gcs.file_exists(file_name):
                raise FileNotFoundError(f"File not found in gs://{self.gcs.bucket_name}/{self.gcs.input_folder}/ - Please check the filename")
            
            file_info = self.gcs.get_file_info(file_name)
            gcs_uri = file_info['gcs_uri']
            logger.info(f"✅ File found: {gcs_uri}")
            logger.info(f"   Size: {file_info['size']} bytes")
            
            # Step 2: Process with Document AI
            logger.info("\nStep 2: Processing with Document AI...")
            document = self.doc_ai.process_document_from_gcs(gcs_uri)
            
            if not document:
                # Document AI processing failed - set processing_status to FAILED
                raise Exception("Document AI processing failed - network or service error")
            
            logger.info("✅ Document AI processing completed successfully")
            result['processing_status'] = 'SUCCESS'  # Document AI processing succeeded
            
            # Step 3: Extract entities
            logger.info("\nStep 3: Extracting entities with bounding boxes...")
            extraction_result = self.doc_ai.extract_entities(document)
            
            logger.info(f"✅ Extracted {extraction_result['total_entities']} entities")
            logger.info(f"   Unique entity types: {extraction_result['unique_entity_types']}")
            logger.info(f"   Average confidence: {extraction_result['avg_confidence']}")
            
            # Step 4: Validate extraction and determine document status
            logger.info("\nStep 4: Validating extraction...")
            validation = extraction_result['validation']
            entities = extraction_result['entities']
            
            # Calculate minimum confidence
            min_confidence = calculate_min_confidence(entities)
            result['min_confidence'] = min_confidence
            
            logger.info(f"DEBUG - Validation result: is_valid={validation['is_valid']}")
            logger.info(f"DEBUG - Missing entities: {validation.get('missing', [])}")
            logger.info(f"DEBUG - Low confidence entities: {validation.get('low_confidence', [])}")
            logger.info(f"DEBUG - Minimum confidence: {min_confidence}")
            logger.info(f"DEBUG - Confidence threshold: {MIN_CONFIDENCE_THRESHOLD}")
            
            # Get missing entities (required entities not found)
            missing_entities = validation.get('missing', [])
            
            # Check ALL extracted entities for low confidence (not just required ones)
            all_low_confidence_entities = []
            for entity in entities:
                entity_confidence = entity.get('confidence', 0)
                if entity_confidence < MIN_CONFIDENCE_THRESHOLD:
                    all_low_confidence_entities.append({
                        'name': entity['name'],
                        'confidence': entity_confidence,
                        'value': entity.get('value', '')
                    })
            
            # Log all low confidence entities found
            if all_low_confidence_entities:
                logger.info(f"DEBUG - ALL low confidence entities found: {[e['name'] for e in all_low_confidence_entities]}")
            
            # Determine document status based on your requirements:
            # 1. If any required entities are missing -> FAILED
            # 2. If all entities present but ANY entity has low confidence -> PENDING_REVIEW
            # 3. If all entities present and all have good confidence -> SUCCESS
            if missing_entities:
                document_status = 'FAILED'
            elif all_low_confidence_entities:
                document_status = 'PENDING_REVIEW'
            else:
                document_status = 'SUCCESS'
            
            # Generate exception details with specific entity information
            if missing_entities or all_low_confidence_entities:
                exception_code, exception_desc, exception_entities = get_exception_details(
                    missing_entities, all_low_confidence_entities, min_confidence
                )
            else:
                exception_code, exception_desc, exception_entities = None, None, None
            
            # Log results with specific entity details
            if document_status == 'SUCCESS':
                logger.info("✅ Validation passed - All entities extracted with sufficient confidence")
            elif document_status == 'FAILED':
                logger.warning("❌ Document validation failed - Missing required entities")
                if missing_entities:
                    logger.warning(f"   Missing entities: {missing_entities}")
            elif document_status == 'PENDING_REVIEW':
                logger.warning("⚠️  Document needs review - Low confidence detected")
                if all_low_confidence_entities:
                    logger.warning("   Low confidence entities:")
                    for entity in all_low_confidence_entities:
                        logger.warning(f"     • {entity['name']}: {entity['confidence']:.2f} (threshold: {MIN_CONFIDENCE_THRESHOLD})")
                        logger.warning(f"       Value: '{entity['value']}'")
            
            # Update result with document validation info
            result['document_status'] = document_status
            result['exception_reason_code'] = exception_code
            result['exception_reason_description'] = exception_desc
            result['exception_entities'] = exception_entities
            
            # Log statistics
            if extraction_result['statistics'].get('entities_with_multiple_values'):
                logger.info("\n📊 Entities with multiple values:")
                for entity in extraction_result['statistics']['entities_with_multiple_values']:
                    logger.info(f"   • {entity['name']}: {entity['count']} values")
            
            # Step 5: Store in database
            logger.info("\nStep 5: Storing in database...")
            processing_id = self.db.store_processing_record(
                file_name=file_name,
                gcs_path=gcs_uri,
                processing_status=result['processing_status'],  # Document AI processing status
                document_status=result['document_status'],      # Document validation status
                min_confidence=result['min_confidence'],        # Minimum confidence
                exception_reason_code=result['exception_reason_code'],
                exception_reason_description=result['exception_reason_description'],
                exception_entities=result['exception_entities'], # Detailed entity exception info
                entities=extraction_result['entities'],
                raw_processor_output=extraction_result['raw_document_data']
            )
            
            logger.info(f"✅ Stored in database with processing_id: {processing_id}")
            
            # Step 6: Move file to processed folder and update GCS path
            logger.info("\nStep 6: Moving file to processed folder...")
            if self.gcs.move_to_processed(file_name):
                logger.info(f"✅ File moved to processed folder")
                # Update GCS path to processed folder
                processed_gcs_uri = f"gs://{self.gcs.bucket_name}/{self.gcs.processed_folder}/{file_name}"
                
                # Update the database record with new GCS path
                try:
                    conn = self.db.get_connection()
                    cursor = conn.cursor()
                    cursor.execute(
                        "UPDATE document_processing SET gcs_path = %s WHERE id = %s",
                        (processed_gcs_uri, processing_id)
                    )
                    conn.commit()
                    cursor.close()
                    conn.close()
                    logger.info(f"✅ Updated GCS path to: {processed_gcs_uri}")
                except Exception as update_error:
                    logger.warning(f"⚠️  Failed to update GCS path: {str(update_error)}")
                    
            else:
                logger.warning(f"⚠️  Failed to move file to processed folder")
            
            # Update result
            result.update({
                'processing_id': processing_id,
                'total_entities': extraction_result['total_entities'],
                'unique_entity_types': extraction_result['unique_entity_types'],
                'avg_confidence': extraction_result['avg_confidence'],
                'validation': validation,
                'statistics': extraction_result['statistics']
            })
            
        except FileNotFoundError as e:
            logger.error(f"❌ File error: {str(e)}")
            result['processing_status'] = 'FAILED'
            result['document_status'] = 'FAILED'
            result['error_message'] = str(e)
            result['exception_reason_code'] = EXCEPTION_CODES['FILE_NOT_FOUND']
            result['exception_reason_description'] = f"File not found in GCS: {file_name}"
            result['exception_entities'] = {"error_type": "file_not_found", "file_name": file_name}
            
            # Store failure in database
            try:
                processing_id = self.db.store_processing_record(
                    file_name=file_name,
                    gcs_path=self.gcs.get_gcs_uri(file_name),
                    processing_status='FAILED',
                    document_status='FAILED',
                    exception_reason_code=result['exception_reason_code'],
                    exception_reason_description=result['exception_reason_description'],
                    exception_entities=result['exception_entities'],
                    error_message=str(e)
                )
                result['processing_id'] = processing_id
            except Exception as db_error:
                logger.error(f"Failed to store error record: {str(db_error)}")
                
        except Exception as e:
            error_str = str(e)
            logger.error(f"❌ Processing failed: {error_str}")
            
            # Determine if this is a Document AI processing error or network error
            if "Document AI processing failed" in error_str or "network" in error_str.lower():
                result['processing_status'] = 'FAILED'  # Document AI failed
                result['document_status'] = 'PENDING'   # Cannot validate if processing failed
                result['exception_reason_code'] = EXCEPTION_CODES['DOCUMENT_AI_ERROR']
                result['exception_reason_description'] = f"Document AI processing failed: {error_str}"
                result['exception_entities'] = {"error_type": "document_ai_processing", "error_details": error_str}
            else:
                result['processing_status'] = 'FAILED'
                result['document_status'] = 'FAILED' 
                result['exception_reason_code'] = EXCEPTION_CODES['PROCESSING_ERROR']
                result['exception_reason_description'] = f"General processing error: {error_str}"
                result['exception_entities'] = {"error_type": "general_processing", "error_details": error_str}
                
            result['error_message'] = error_str
            
            # Store failure in database
            try:
                processing_id = self.db.store_processing_record(
                    file_name=file_name,
                    gcs_path=self.gcs.get_gcs_uri(file_name),
                    processing_status=result['processing_status'],
                    document_status=result['document_status'],
                    exception_reason_code=result['exception_reason_code'],
                    exception_reason_description=result['exception_reason_description'],
                    exception_entities=result['exception_entities'],
                    error_message=error_str
                )
                result['processing_id'] = processing_id
                
                # Move to failed folder (only if file exists)
                if self.gcs.file_exists(file_name):
                    self.gcs.move_to_failed(file_name)
                    logger.info(f"File moved to failed folder")
            except Exception as db_error:
                logger.error(f"Failed to store error record: {str(db_error)}")
        
        finally:
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            result['processing_time_seconds'] = round(processing_time, 2)
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing completed: {file_name}")
            logger.info(f"Processing Status: {result['processing_status']}")
            logger.info(f"Document Status: {result['document_status']}")
            if result.get('min_confidence'):
                logger.info(f"Min Confidence: {result['min_confidence']:.2f}")
            if result.get('exception_reason_code'):
                logger.info(f"Exception Code: {result['exception_reason_code']}")
            logger.info(f"Processing time: {processing_time:.2f} seconds")
            logger.info(f"{'=' * 80}\n")
        
        return result
    
    def process_all_invoices(self) -> Dict:
        """
        Process all invoices in the input folder
        
        Returns:
            Summary of processing results
        """
        logger.info("=" * 80)
        logger.info("BATCH PROCESSING: Processing all invoices in input folder")
        logger.info("=" * 80)
        
        # Get all PDF files
        files = self.gcs.list_input_files('.pdf')
        
        if not files:
            logger.info("No PDF files found in input folder")
            return {
                'total_files': 0,
                'successful': 0,
                'failed': 0,
                'results': []
            }
        
        logger.info(f"Found {len(files)} PDF files to process\n")
        
        results = []
        successful = 0
        failed = 0
        
        for i, file_name in enumerate(files, 1):
            logger.info(f"\n{'*' * 80}")
            logger.info(f"Processing file {i}/{len(files)}: {file_name}")
            logger.info(f"{'*' * 80}")
            
            result = self.process_single_invoice(file_name)
            results.append(result)
            
            if result['processing_status'] == 'SUCCESS' and result['document_status'] == 'SUCCESS':
                successful += 1
            else:
                failed += 1
        
        # Summary
        summary = {
            'total_files': len(files),
            'successful': successful,
            'failed': failed,
            'results': results
        }
        
        logger.info("\n" + "=" * 80)
        logger.info("BATCH PROCESSING COMPLETE")
        logger.info("=" * 80)
        logger.info(f"Total files: {summary['total_files']}")
        logger.info(f"Successful: {summary['successful']}")
        logger.info(f"Failed: {summary['failed']}")
        logger.info("=" * 80)
        
        return summary
    
    def get_processing_summary(self, processing_id: int) -> Dict:
        """
        Get detailed summary of a processed invoice with raw output
        
        Args:
            processing_id: Database processing ID
            
        Returns:
            Summary dictionary with raw processor output
        """
        try:
            # Use the new comprehensive summary method
            return self.db.get_processing_summary_with_raw(processing_id)
            
        except Exception as e:
            logger.error(f"Failed to get processing summary: {str(e)}")
            return {}
    
    def list_available_files(self):
        """List all files available for processing"""
        files = self.gcs.list_input_files('.pdf')
        
        if not files:
            print("\n❌ No PDF files found in input folder")
            print(f"   Bucket: gs://{self.gcs.bucket_name}/{self.gcs.input_folder}/")
            return
        
        print(f"\n📁 Available files in gs://{self.gcs.bucket_name}/{self.gcs.input_folder}/:")
        print(f"{'=' * 80}")
        for i, file_name in enumerate(files, 1):
            file_info = self.gcs.get_file_info(file_name)
            size_kb = file_info['size'] / 1024
            print(f"{i}. {file_name}")
            print(f"   Size: {size_kb:.2f} KB")
            print(f"   Created: {file_info['created']}")
        print(f"{'=' * 80}\n")


# CLI interface
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Invoice Processing Pipeline',
        epilog='Examples:\n'
               '  List files:        python src/invoice_processor.py --list\n'
               '  Process one file:  python src/invoice_processor.py --file T1.pdf\n'
               '  Process all files: python src/invoice_processor.py --all\n'
               '  Get summary:       python src/invoice_processor.py --summary 1\n',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--file',
        type=str,
        help='Process a single file by name (just filename, e.g., T1.pdf)'
    )
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all files in input folder'
    )
    parser.add_argument(
        '--summary',
        type=int,
        help='Get summary for a processing_id'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List all available files in input folder'
    )
    
    args = parser.parse_args()
    
    processor = InvoiceProcessor()
    
    if args.list:
        # List available files
        processor.list_available_files()
        
    elif args.file:
        # Process single file
        result = processor.process_single_invoice(args.file)
        print(f"\n{'=' * 80}")
        print(f"PROCESSING RESULT: {result['processing_status']}")
        print(f"DOCUMENT RESULT: {result['document_status']}")
        print(f"Processing ID: {result['processing_id']}")
        print(f"Total entities: {result['total_entities']}")
        if result['processing_status'] == 'SUCCESS':
            print(f"Unique entity types: {result['unique_entity_types']}")
            print(f"Average confidence: {result['avg_confidence']}")
            if result.get('min_confidence'):
                print(f"Minimum confidence: {result['min_confidence']:.2f}")
            if result.get('exception_reason_code'):
                print(f"Exception Code: {result['exception_reason_code']}")
                print(f"Exception Details: {result['exception_reason_description']}")
        else:
            print(f"Error: {result['error_message']}")
        print(f"Processing time: {result['processing_time_seconds']}s")
        print(f"{'=' * 80}")
        
    elif args.all:
        # Process all files
        summary = processor.process_all_invoices()
        
    elif args.summary:
        # Get summary
        summary = processor.get_processing_summary(args.summary)
        if summary:
            print(f"\n{'=' * 80}")
            print(f"Processing Summary - ID: {summary['processing_id']}")
            print(f"{'=' * 80}")
            print(f"Total entities extracted: {summary['total_entities']}")
            print(f"Unique entity types: {summary['statistics']['total_unique_entities']}")
            
            if summary['statistics']['entities_with_multiple_values']:
                print(f"\n📊 Entities with multiple values:")
                for entity in summary['statistics']['entities_with_multiple_values']:
                    print(f"  • {entity['name']}: {entity['count']} values")
                    print(f"    Values: {entity['values']}")
            
            print(f"\n✨ Best values (highest confidence):")
            for entity_name, value_info in summary['best_values'].items():
                print(f"  • {entity_name}: {value_info['entity_value']} (confidence: {value_info['confidence_score']})")
            print(f"{'=' * 80}\n")
        else:
            print(f"\n❌ No processing found with ID: {args.summary}\n")
        
    else:
        parser.print_help()
