"""Document AI processor for entity extraction with bounding boxes"""
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
import logging
from typing import Dict, List, Optional
import os
import sys
from datetime import datetime

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
            Dictionary containing entities, validation results, metadata, and raw document data
        """
        try:
            entities_list = []
            entity_dict = {}
            total_confidence = 0
            
            # Convert document to serializable format for storage
            raw_document_data = self._convert_document_to_dict(document)
            
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
                },
                'raw_document_data': raw_document_data
            }
            
        except Exception as e:
            logger.error(f"Entity extraction failed: {str(e)}")
            return {
                'entities': [],
                'entity_dict': {},
                'avg_confidence': 0,
                'total_entities': 0,
                'validation': {'is_valid': False, 'missing': [], 'low_confidence': []},
                'raw_document_data': None
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
    
    def _convert_document_to_dict(self, document: documentai.Document) -> Dict:
        """
        Convert Document AI document object to serializable dictionary
        
        Args:
            document: Document AI document object
            
        Returns:
            Serializable dictionary containing document data
        """
        try:
            # Basic document info
            doc_dict = {
                'mime_type': document.mime_type,
                'text': document.text,
                'uri': document.uri if hasattr(document, 'uri') else None,
                'error': None,
                'pages': [],
                'entities': [],
                'document_style': None,
                'revisions': [],
                'text_styles': []
            }
            
            # Handle document error if present
            if hasattr(document, 'error') and document.error:
                doc_dict['error'] = {
                    'code': document.error.code,
                    'message': document.error.message
                }
            
            # Process pages
            for page in document.pages:
                page_dict = {
                    'page_number': page.page_number if hasattr(page, 'page_number') else None,
                    'dimension': {
                        'width': float(page.dimension.width) if page.dimension else None,
                        'height': float(page.dimension.height) if page.dimension else None,
                        'unit': page.dimension.unit if page.dimension else None
                    },
                    'layout': None,
                    'detected_languages': [],
                    'blocks': len(page.blocks) if hasattr(page, 'blocks') else 0,
                    'paragraphs': len(page.paragraphs) if hasattr(page, 'paragraphs') else 0,
                    'lines': len(page.lines) if hasattr(page, 'lines') else 0,
                    'tokens': len(page.tokens) if hasattr(page, 'tokens') else 0
                }
                
                # Process detected languages
                if hasattr(page, 'detected_languages'):
                    for lang in page.detected_languages:
                        page_dict['detected_languages'].append({
                            'language_code': lang.language_code,
                            'confidence': float(lang.confidence) if hasattr(lang, 'confidence') else None
                        })
                
                doc_dict['pages'].append(page_dict)
            
            # Process entities
            for entity in document.entities:
                entity_dict = {
                    'type': entity.type_,
                    'mention_text': entity.mention_text,
                    'confidence': float(entity.confidence),
                    'page_anchor': None,
                    'text_anchor': None,
                    'id': entity.id if hasattr(entity, 'id') else None,
                    'normalized_value': None,
                    'properties': []
                }
                
                # Process page anchor (bounding boxes)
                if entity.page_anchor and entity.page_anchor.page_refs:
                    page_refs = []
                    for page_ref in entity.page_anchor.page_refs:
                        page_ref_dict = {
                            'page': page_ref.page if hasattr(page_ref, 'page') else None,
                            'layout_type': page_ref.layout_type if hasattr(page_ref, 'layout_type') else None,
                            'layout_id': page_ref.layout_id if hasattr(page_ref, 'layout_id') else None,
                            'bounding_poly': None
                        }
                        
                        # Extract bounding polygon
                        if page_ref.bounding_poly:
                            poly_dict = {
                                'vertices': [],
                                'normalized_vertices': []
                            }
                            
                            if page_ref.bounding_poly.vertices:
                                for vertex in page_ref.bounding_poly.vertices:
                                    poly_dict['vertices'].append({
                                        'x': float(vertex.x) if hasattr(vertex, 'x') else 0.0,
                                        'y': float(vertex.y) if hasattr(vertex, 'y') else 0.0
                                    })
                            
                            if page_ref.bounding_poly.normalized_vertices:
                                for vertex in page_ref.bounding_poly.normalized_vertices:
                                    poly_dict['normalized_vertices'].append({
                                        'x': float(vertex.x) if hasattr(vertex, 'x') else 0.0,
                                        'y': float(vertex.y) if hasattr(vertex, 'y') else 0.0
                                    })
                            
                            page_ref_dict['bounding_poly'] = poly_dict
                        
                        page_refs.append(page_ref_dict)
                    
                    entity_dict['page_anchor'] = {'page_refs': page_refs}
                
                # Process text anchor
                if entity.text_anchor and entity.text_anchor.text_segments:
                    text_segments = []
                    for segment in entity.text_anchor.text_segments:
                        text_segments.append({
                            'start_index': int(segment.start_index) if hasattr(segment, 'start_index') else None,
                            'end_index': int(segment.end_index) if hasattr(segment, 'end_index') else None
                        })
                    entity_dict['text_anchor'] = {'text_segments': text_segments}
                
                # Process normalized value
                if hasattr(entity, 'normalized_value') and entity.normalized_value:
                    try:
                        # Convert normalized value based on type
                        if hasattr(entity.normalized_value, 'text'):
                            entity_dict['normalized_value'] = {
                                'text': entity.normalized_value.text
                            }
                        elif hasattr(entity.normalized_value, 'money_value'):
                            money = entity.normalized_value.money_value
                            entity_dict['normalized_value'] = {
                                'money_value': {
                                    'currency_code': money.currency_code if hasattr(money, 'currency_code') else None,
                                    'units': int(money.units) if hasattr(money, 'units') else None,
                                    'nanos': int(money.nanos) if hasattr(money, 'nanos') else None
                                }
                            }
                        elif hasattr(entity.normalized_value, 'date_value'):
                            date = entity.normalized_value.date_value
                            entity_dict['normalized_value'] = {
                                'date_value': {
                                    'year': int(date.year) if hasattr(date, 'year') else None,
                                    'month': int(date.month) if hasattr(date, 'month') else None,
                                    'day': int(date.day) if hasattr(date, 'day') else None
                                }
                            }
                    except Exception as norm_error:
                        logger.warning(f"Failed to process normalized value: {norm_error}")
                        entity_dict['normalized_value'] = None
                
                # Process entity properties/relationships
                if hasattr(entity, 'properties'):
                    for prop in entity.properties:
                        prop_dict = {
                            'type': prop.type_ if hasattr(prop, 'type_') else None,
                            'mention_text': prop.mention_text if hasattr(prop, 'mention_text') else None,
                            'confidence': float(prop.confidence) if hasattr(prop, 'confidence') else None
                        }
                        entity_dict['properties'].append(prop_dict)
                
                doc_dict['entities'].append(entity_dict)
            
            # Add metadata
            doc_dict['metadata'] = {
                'total_pages': len(doc_dict['pages']),
                'total_entities': len(doc_dict['entities']),
                'processing_timestamp': datetime.now().isoformat(),
                'processor_version': 'document-ai-v1'  # Could be made configurable
            }
            
            logger.info(f"✅ Converted document to dict: {doc_dict['metadata']['total_pages']} pages, {doc_dict['metadata']['total_entities']} entities")
            return doc_dict
            
        except Exception as e:
            logger.error(f"Failed to convert document to dict: {str(e)}")
            # Return minimal document structure with error info
            return {
                'mime_type': getattr(document, 'mime_type', None),
                'text': getattr(document, 'text', None),
                'error': {
                    'conversion_error': str(e)
                },
                'metadata': {
                    'processing_timestamp': datetime.now().isoformat(),
                    'conversion_failed': True
                }
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
