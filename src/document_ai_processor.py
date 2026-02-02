"""Document AI processor for entity extraction with bounding boxes"""
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
import logging
from typing import Dict, List, Optional
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.config import PROJECT_ID, PROCESSOR_ID, LOCATION, REQUIRED_ENTITIES, MIN_CONFIDENCE_THRESHOLD

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DocumentAIProcessor:
    """Handle Document AI operations"""
    
    def __init__(self):
        self.project_id = PROJECT_ID
        self.location = LOCATION
        self.processor_id = PROCESSOR_ID
        self.processor_name = f"projects/{PROJECT_ID}/locations/us/processors/{PROCESSOR_ID}"
        
        # Initialize Document AI client
        self.client = documentai.DocumentProcessorServiceClient()
        logger.info(f"Initialized Document AI processor: {self.processor_name}")
    
    def process_document_from_gcs(self, gcs_uri: str) -> Optional[documentai.Document]:
        """
        Process document from GCS using Document AI
        
        Args:
            gcs_uri: GCS URI of the document (gs://bucket/path/file.pdf)
            
        Returns:
            Document object with extracted entities or None if failed
        """
        try:
            logger.info(f"Processing document: {gcs_uri}")
            
            # Create GCS document object
            gcs_document = documentai.GcsDocument(
                gcs_uri=gcs_uri,
                mime_type="application/pdf"
            )
            
            # Configure the process request
            request = documentai.ProcessRequest(
                name=self.processor_name,
                gcs_document=gcs_document
            )
            
            # Process the document
            result = self.client.process_document(request=request)
            document = result.document
            
            logger.info(f"✅ Document processed successfully: {gcs_uri}")
            logger.info(f"Found {len(document.entities)} entities")
            
            return document
            
        except Exception as e:
            logger.error(f"❌ Document AI processing failed: {str(e)}")
            return None
    
    def _extract_bounding_box(self, entity) -> Optional[Dict]:
        """
        Extract bounding box information from entity
        
        Args:
            entity: Document AI entity object
            
        Returns:
            Dictionary containing vertices and normalized vertices
        """
        try:
            if not entity.page_anchor or not entity.page_anchor.page_refs:
                return None
            
            page_ref = entity.page_anchor.page_refs[0]
            
            if not page_ref.bounding_poly:
                return None
            
            bounding_poly = page_ref.bounding_poly
            
            # Extract vertices (absolute coordinates)
            vertices = []
            if bounding_poly.vertices:
                for vertex in bounding_poly.vertices:
                    vertices.append({
                        'x': float(vertex.x) if hasattr(vertex, 'x') else 0.0,
                        'y': float(vertex.y) if hasattr(vertex, 'y') else 0.0
                    })
            
            # Extract normalized vertices (0-1 scale)
            normalized_vertices = []
            if bounding_poly.normalized_vertices:
                for vertex in bounding_poly.normalized_vertices:
                    normalized_vertices.append({
                        'x': float(vertex.x) if hasattr(vertex, 'x') else 0.0,
                        'y': float(vertex.y) if hasattr(vertex, 'y') else 0.0
                    })
            
            return {
                'vertices': vertices,
                'normalized_vertices': normalized_vertices
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract bounding box: {str(e)}")
            return None
    
    def _get_page_number(self, entity) -> Optional[int]:
        """
        Extract page number from entity
        
        Args:
            entity: Document AI entity object
            
        Returns:
            Page number (0-indexed) or None
        """
        try:
            if entity.page_anchor and entity.page_anchor.page_refs:
                return entity.page_anchor.page_refs[0].page
            return None
        except Exception as e:
            logger.warning(f"Failed to extract page number: {str(e)}")
            return None
    
    def extract_entities(self, document: documentai.Document) -> Dict:
        """
        Extract and structure entities from Document AI response with bounding boxes
        
        Args:
            document: Processed Document AI document object
            
        Returns:
            Dictionary containing entities, validation results, and metadata
        """
        try:
            entities_list = []
            entity_dict = {}
            total_confidence = 0
            
            # Extract entities with bounding boxes
            for entity in document.entities:
                entity_name = entity.type_
                entity_value = entity.mention_text
                confidence = entity.confidence
                
                # Extract bounding box and page number
                bounding_box = self._extract_bounding_box(entity)
                page_number = self._get_page_number(entity)
                
                entity_data = {
                    'name': entity_name,
                    'value': entity_value,
                    'confidence': round(confidence, 2),
                    'page_number': page_number,
                    'bounding_box': bounding_box
                }
                
                entities_list.append(entity_data)
                
                entity_dict[entity_name] = {
                    'value': entity_value,
                    'confidence': round(confidence, 2),
                    'page_number': page_number,
                    'bounding_box': bounding_box
                }
                
                total_confidence += confidence
                
                # Log with bounding box info
                bbox_info = f"(page: {page_number}, bbox: {'✓' if bounding_box else '✗'})"
                logger.info(f"  • {entity_name}: {entity_value} (confidence: {confidence:.2f}) {bbox_info}")
            
            # Calculate average confidence
            avg_confidence = round(total_confidence / len(entities_list), 2) if entities_list else 0
            
            # Calculate unique entity types
            unique_entity_types = len(set(entity['name'] for entity in entities_list))
            
            # Calculate statistics for entities with multiple values
            entity_value_counts = {}
            for entity in entities_list:
                entity_name = entity['name']
                if entity_name not in entity_value_counts:
                    entity_value_counts[entity_name] = {
                        'count': 0,
                        'values': []
                    }
                entity_value_counts[entity_name]['count'] += 1
                entity_value_counts[entity_name]['values'].append(entity['value'])
            
            entities_with_multiple_values = [
                {
                    'name': entity_name,
                    'count': info['count'],
                    'values': info['values']
                }
                for entity_name, info in entity_value_counts.items()
                if info['count'] > 1
            ]
            
            # Validate entities
            validation_result = self._validate_entities(entity_dict)
            
            return {
                'entities': entities_list,
                'entity_dict': entity_dict,
                'avg_confidence': avg_confidence,
                'total_entities': len(entities_list),
                'unique_entity_types': unique_entity_types,
                'validation': validation_result,
                'statistics': {
                    'entities_with_multiple_values': entities_with_multiple_values,
                    'total_unique_entities': unique_entity_types
                }
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return {
                'entities': [],
                'entity_dict': {},
                'avg_confidence': 0,
                'total_entities': 0,
                'validation': {'is_valid': False, 'missing': [], 'low_confidence': []}
            }
    
    def _validate_entities(self, entity_dict: Dict) -> Dict:
        """
        Validate extracted entities
        
        Args:
            entity_dict: Dictionary of extracted entities
            
        Returns:
            Validation results with missing and low confidence entities
        """
        missing_entities = []
        low_confidence_entities = []
        
        # Check for missing required entities
        for required_entity in REQUIRED_ENTITIES:
            if required_entity not in entity_dict:
                missing_entities.append(required_entity)
            elif entity_dict[required_entity]['confidence'] < MIN_CONFIDENCE_THRESHOLD:
                low_confidence_entities.append({
                    'name': required_entity,
                    'confidence': entity_dict[required_entity]['confidence']
                })
        
        is_valid = len(missing_entities) == 0 and len(low_confidence_entities) == 0
        
        if not is_valid:
            logger.warning(f"⚠️  Validation issues found:")
            if missing_entities:
                logger.warning(f"   Missing entities: {missing_entities}")
            if low_confidence_entities:
                logger.warning(f"   Low confidence entities: {low_confidence_entities}")
        else:
            logger.info("✅ All validations passed!")
        
        return {
            'is_valid': is_valid,
            'missing': missing_entities,
            'low_confidence': low_confidence_entities
        }


# Test function
def test_document_ai():
    """Test Document AI processor"""
    try:
        processor = DocumentAIProcessor()
        print(f"✅ Document AI client initialized successfully!")
        print(f"Processor: {processor.processor_name}")
        return True
    except Exception as e:
        print(f"❌ Document AI initialization failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_document_ai()
