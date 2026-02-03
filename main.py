"""Cloud Run Job for Invoice Processing - Runs every 30 minutes"""
import logging
import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

from src.invoice_processor import InvoiceProcessor

# Configure logging for Cloud Run
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)


def main():
    """Main function for Cloud Run Job"""
    try:
        logger.info("=" * 80)
        logger.info("🚀 Starting Invoice Processing Cloud Run Job")
        logger.info(f"⏰ Execution time: {datetime.now().isoformat()}")
        logger.info("=" * 80)
        
        # Initialize processor
        processor = InvoiceProcessor()
        
        # Process all invoices in the input folder
        summary = processor.process_all_invoices()
        
        # Log results
        logger.info("\n" + "=" * 80)
        logger.info("📊 JOB EXECUTION SUMMARY")
        logger.info("=" * 80)
        logger.info(f"Total files processed: {summary['total_files']}")
        logger.info(f"✅ Successful: {summary['successful']}")
        logger.info(f"❌ Failed: {summary['failed']}")
        logger.info("=" * 80)
        
        # Exit with appropriate code
        if summary['failed'] > 0 and summary['successful'] == 0:
            logger.error("All files failed to process")
            sys.exit(1)
        elif summary['total_files'] == 0:
            logger.info("No files to process - this is normal")
            sys.exit(0)
        else:
            logger.info("✅ Job completed successfully")
            sys.exit(0)
            
    except Exception as e:
        logger.error(f"❌ Job failed with error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
