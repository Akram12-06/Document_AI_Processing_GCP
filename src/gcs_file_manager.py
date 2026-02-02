"""GCS file management for invoice processing"""
from google.cloud import storage
import logging
from typing import List, Optional
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.config import BUCKET_NAME, INPUT_FOLDER, PROCESSED_FOLDER, FAILED_FOLDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class GCSFileManager:
    """Handle GCS file operations"""
    
    def __init__(self):
        self.bucket_name = BUCKET_NAME
        self.input_folder = INPUT_FOLDER
        self.processed_folder = PROCESSED_FOLDER
        self.failed_folder = FAILED_FOLDER
        
        # Initialize GCS client
        self.client = storage.Client()
        self.bucket = self.client.bucket(self.bucket_name)
        
        logger.info(f"Initialized GCS File Manager for bucket: {self.bucket_name}")
    
    def list_input_files(self, file_extension: str = '.pdf') -> List[str]:
        """
        List all files in the input folder
        
        Args:
            file_extension: Filter by file extension (default: .pdf)
            
        Returns:
            List of file names (without folder prefix)
        """
        try:
            blobs = self.bucket.list_blobs(prefix=f"{self.input_folder}/")
            
            files = []
            for blob in blobs:
                # Skip the folder itself
                if blob.name == f"{self.input_folder}/":
                    continue
                
                # Filter by extension
                if file_extension and not blob.name.lower().endswith(file_extension.lower()):
                    continue
                
                # Extract just the filename
                file_name = blob.name.split('/')[-1]
                files.append(file_name)
            
            logger.info(f"Found {len(files)} {file_extension} files in {self.input_folder}/")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list input files: {str(e)}")
            return []
    
    def get_gcs_uri(self, file_name: str, folder: Optional[str] = None) -> str:
        """
        Get full GCS URI for a file
        
        Args:
            file_name: Name of the file
            folder: Folder name (default: input_folder)
            
        Returns:
            Full GCS URI (gs://bucket/folder/file)
        """
        folder = folder or self.input_folder
        return f"gs://{self.bucket_name}/{folder}/{file_name}"
    
    def move_file(self, file_name: str, from_folder: str, to_folder: str) -> bool:
        """
        Move file from one folder to another
        
        Args:
            file_name: Name of the file
            from_folder: Source folder
            to_folder: Destination folder
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_blob_name = f"{from_folder}/{file_name}"
            dest_blob_name = f"{to_folder}/{file_name}"
            
            source_blob = self.bucket.blob(source_blob_name)
            
            # Check if source exists
            if not source_blob.exists():
                logger.error(f"Source file not found: {source_blob_name}")
                return False
            
            # Copy to destination
            self.bucket.copy_blob(source_blob, self.bucket, dest_blob_name)
            
            # Delete source
            source_blob.delete()
            
            logger.info(f"Moved file: {source_blob_name} → {dest_blob_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to move file {file_name}: {str(e)}")
            return False
    
    def move_to_processed(self, file_name: str) -> bool:
        """Move file from input to processed folder"""
        return self.move_file(file_name, self.input_folder, self.processed_folder)
    
    def move_to_failed(self, file_name: str) -> bool:
        """Move file from input to failed folder"""
        return self.move_file(file_name, self.input_folder, self.failed_folder)
    
    def file_exists(self, file_name: str, folder: Optional[str] = None) -> bool:
        """
        Check if file exists in a folder
        
        Args:
            file_name: Name of the file
            folder: Folder to check (default: input_folder)
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            folder = folder or self.input_folder
            blob_name = f"{folder}/{file_name}"
            blob = self.bucket.blob(blob_name)
            return blob.exists()
            
        except Exception as e:
            logger.error(f"Error checking file existence: {str(e)}")
            return False
    
    def get_file_info(self, file_name: str, folder: Optional[str] = None) -> Optional[dict]:
        """
        Get file metadata
        
        Args:
            file_name: Name of the file
            folder: Folder (default: input_folder)
            
        Returns:
            Dictionary with file info or None
        """
        try:
            folder = folder or self.input_folder
            blob_name = f"{folder}/{file_name}"
            blob = self.bucket.blob(blob_name)
            
            if not blob.exists():
                return None
            
            blob.reload()
            
            return {
                'name': file_name,
                'size': blob.size,
                'created': blob.time_created,
                'updated': blob.updated,
                'content_type': blob.content_type,
                'gcs_uri': self.get_gcs_uri(file_name, folder)
            }
            
        except Exception as e:
            logger.error(f"Failed to get file info: {str(e)}")
            return None


# Test function
def test_gcs_manager():
    """Test GCS file manager"""
    try:
        gcs = GCSFileManager()
        print(f"✅ GCS File Manager initialized successfully!")
        print(f"Bucket: {gcs.bucket_name}")
        
        # List input files
        print(f"\n📁 Files in {gcs.input_folder}/:")
        files = gcs.list_input_files()
        for file_name in files:
            print(f"  • {file_name}")
            info = gcs.get_file_info(file_name)
            if info:
                print(f"    Size: {info['size']} bytes")
                print(f"    GCS URI: {info['gcs_uri']}")
        
        if not files:
            print("  (No files found)")
        
        return True
        
    except Exception as e:
        print(f"❌ GCS File Manager test failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_gcs_manager()
