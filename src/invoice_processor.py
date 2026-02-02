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
            'status': 'PROCESSING',
            'processing_id': None,
            'error_message': None,
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
                raise Exception("Document AI processing failed")
            
            logger.info("✅ Document AI processing completed")
            
            # Step 3: Extract entities
            logger.info("\nStep 3: Extracting entities with bounding boxes...")
            extraction_result = self.doc_ai.extract_entities(document)
            
            logger.info(f"✅ Extracted {extraction_result['total_entities']} entities")
            logger.info(f"   Unique entity types: {extraction_result['unique_entity_types']}")
            logger.info(f"   Average confidence: {extraction_result['avg_confidence']}")
            
            # Step 4: Validate extraction
            logger.info("\nStep 4: Validating extraction...")
            validation = extraction_result['validation']
            
            if validation['is_valid']:
                logger.info("✅ Validation passed - All required entities found")
                result['status'] = 'SUCCESS'
            else:
                logger.warning("⚠️  Validation issues found:")
                if validation['missing']:
                    logger.warning(f"   Missing entities: {validation['missing']}")
                if validation['low_confidence']:
                    logger.warning(f"   Low confidence entities: {[e['name'] for e in validation['low_confidence']]}")
                result['status'] = 'SUCCESS'  # Still success, but with warnings
            
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
                status=result['status'],
                entities=extraction_result['entities'],
                avg_confidence=extraction_result['avg_confidence']
            )
            
            logger.info(f"✅ Stored in database with processing_id: {processing_id}")
            
            # Step 6: Move file to processed folder
            logger.info("\nStep 6: Moving file to processed folder...")
            if self.gcs.move_to_processed(file_name):
                logger.info(f"✅ File moved to processed folder")
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
            
        except Exception as e:
            logger.error(f"❌ Processing failed: {str(e)}")
            result['status'] = 'FAILED'
            result['error_message'] = str(e)
            
            # Store failure in database
            try:
                processing_id = self.db.store_processing_record(
                    file_name=file_name,
                    gcs_path=self.gcs.get_gcs_uri(file_name),
                    status='FAILED',
                    error_message=str(e)
                )
                result['processing_id'] = processing_id
                
                # Move to failed folder (only if file exists)
                if self.gcs.file_exists(file_name):
                    self.gcs.move_to_failed(file_name)
                    logger.info(f"File moved to failed folder")
                
            except Exception as db_error:
                logger.error(f"Failed to store error in database: {str(db_error)}")
        
        finally:
            # Calculate processing time
            end_time = datetime.now()
            processing_time = (end_time - start_time).total_seconds()
            result['processing_time_seconds'] = round(processing_time, 2)
            
            logger.info(f"\n{'=' * 80}")
            logger.info(f"Processing completed: {file_name}")
            logger.info(f"Status: {result['status']}")
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
            
            if result['status'] == 'SUCCESS':
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
        Get detailed summary of a processed invoice
        
        Args:
            processing_id: Database processing ID
            
        Returns:
            Summary dictionary
        """
        try:
            # Get all entities
            entities = self.db.get_extracted_entities(processing_id)
            
            # Get statistics
            stats = self.db.get_entity_statistics(processing_id)
            
            # Get best values
            best_values = self.db.get_best_value_per_entity(processing_id)
            
            return {
                'processing_id': processing_id,
                'total_entities': len(entities),
                'statistics': stats,
                'best_values': best_values,
                'all_entities': entities
            }
            
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
        print(f"RESULT: {result['status']}")
        print(f"Processing ID: {result['processing_id']}")
        print(f"Total entities: {result['total_entities']}")
        if result['status'] == 'SUCCESS':
            print(f"Unique entity types: {result['unique_entity_types']}")
            print(f"Average confidence: {result['avg_confidence']}")
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
