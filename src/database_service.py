"""Database service for storing processing results with bounding boxes - Handles Multiple Values"""
import psycopg2
from psycopg2.extras import RealDictCursor, Json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from config.config import DB_CONFIG

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabaseService:
    """Handle all database operations - Optimized for multiple entity values"""
    
    def __init__(self):
        self.db_config = DB_CONFIG
    
    def get_connection(self):
        """Create database connection"""
        try:
            conn = psycopg2.connect(**self.db_config)
            return conn
        except Exception as e:
            logger.error(f"Database connection failed: {str(e)}")
            raise
    
    def store_processing_record(
        self,
        file_name: str,
        gcs_path: str,
        status: str,
        entities: Optional[List[Dict]] = None,
        error_message: Optional[str] = None,
        avg_confidence: Optional[float] = None
    ) -> int:
        """
        Store processing record and extracted entities with bounding boxes
        Each entity value is stored as a SEPARATE ROW (handles multiple values naturally)
        
        Args:
            file_name: Name of the processed file
            gcs_path: GCS path of the file
            status: Processing status (SUCCESS, FAILED, PROCESSING)
            entities: List of extracted entities (can have multiple entries for same entity_name)
            error_message: Error message if processing failed
            avg_confidence: Average confidence score of extracted entities
            
        Returns:
            processing_id: ID of the created processing record
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert processing record
            insert_query = """
                INSERT INTO document_processing 
                (file_name, gcs_path, processing_status, error_message, extraction_confidence, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id
            """
            
            cursor.execute(
                insert_query,
                (file_name, gcs_path, status, error_message, avg_confidence, datetime.now())
            )
            
            processing_id = cursor.fetchone()[0]
            logger.info(f"Created processing record with ID: {processing_id}")
            
            # Insert entities if provided (each value = separate row)
            if entities and status == 'SUCCESS':
                inserted_count = self._store_entities(cursor, processing_id, entities)
                logger.info(f"Stored {inserted_count} entity records (including duplicates)")
            
            conn.commit()
            logger.info(f"Successfully stored processing record for {file_name}")
            return processing_id
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Failed to store processing record: {str(e)}")
            raise
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def _store_entities(self, cursor, processing_id: int, entities: List[Dict]) -> int:
        """
        Store extracted entities with bounding boxes
        Each entity value is stored as a SEPARATE ROW
        
        Args:
            cursor: Database cursor
            processing_id: ID of the processing record
            entities: List of entity dictionaries
            
        Returns:
            Number of rows inserted
        """
        insert_query = """
            INSERT INTO extracted_entities 
            (processing_id, entity_name, entity_value, confidence_score, page_number, bounding_box)
            VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        inserted_count = 0
        
        for entity in entities:
            try:
                # Validate entity has required fields
                if 'name' not in entity or 'value' not in entity:
                    logger.warning(f"Skipping invalid entity: {entity}")
                    continue
                
                # Skip empty values
                if not entity['value'] or str(entity['value']).strip() == '':
                    logger.warning(f"Skipping empty value for entity: {entity.get('name')}")
                    continue
                
                # Convert bounding_box dict to JSON for PostgreSQL
                bounding_box_json = Json(entity.get('bounding_box')) if entity.get('bounding_box') else None
                
                cursor.execute(
                    insert_query,
                    (
                        processing_id,
                        entity['name'],
                        str(entity['value']).strip(),
                        entity.get('confidence'),
                        entity.get('page_number'),
                        bounding_box_json
                    )
                )
                inserted_count += 1
                
            except Exception as e:
                logger.error(f"Failed to insert entity {entity.get('name')}: {str(e)}")
                # Continue with other entities
                continue
        
        logger.info(f"Stored {inserted_count} entities with bounding boxes for processing_id {processing_id}")
        return inserted_count
    
    def get_processing_status(self, file_name: str) -> Optional[Dict]:
        """Get processing status for a file"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT * FROM document_processing
                WHERE file_name = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            
            cursor.execute(query, (file_name,))
            result = cursor.fetchone()
            
            return dict(result) if result else None
            
        except Exception as e:
            logger.error(f"Failed to get processing status: {str(e)}")
            return None
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_extracted_entities(self, processing_id: int) -> List[Dict]:
        """
        Get extracted entities with bounding boxes for a processing record
        Returns ALL rows (including multiple values for same entity)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    id,
                    entity_name, 
                    entity_value, 
                    confidence_score, 
                    page_number, 
                    bounding_box,
                    created_at
                FROM extracted_entities
                WHERE processing_id = %s
                ORDER BY entity_name, confidence_score DESC
            """
            
            cursor.execute(query, (processing_id,))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get extracted entities: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_entities_grouped_by_name(self, processing_id: int) -> Dict[str, List[Dict]]:
        """
        Get entities grouped by entity_name
        Useful for handling multiple values per entity
        
        Returns:
            Dictionary with entity_name as key and list of values as value
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    entity_name, 
                    entity_value, 
                    confidence_score, 
                    page_number, 
                    bounding_box
                FROM extracted_entities
                WHERE processing_id = %s
                ORDER BY entity_name, confidence_score DESC
            """
            
            cursor.execute(query, (processing_id,))
            results = cursor.fetchall()
            
            # Group by entity_name
            grouped = {}
            for row in results:
                entity_name = row['entity_name']
                if entity_name not in grouped:
                    grouped[entity_name] = []
                grouped[entity_name].append(dict(row))
            
            return grouped
            
        except Exception as e:
            logger.error(f"Failed to get grouped entities: {str(e)}")
            return {}
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_entity_statistics(self, processing_id: int) -> Dict:
        """
        Get statistics about extracted entities
        Shows which entities have multiple values
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    entity_name,
                    COUNT(*) as value_count,
                    AVG(confidence_score) as avg_confidence,
                    MAX(confidence_score) as max_confidence,
                    MIN(confidence_score) as min_confidence,
                    ARRAY_AGG(entity_value ORDER BY confidence_score DESC) as all_values
                FROM extracted_entities
                WHERE processing_id = %s
                GROUP BY entity_name
                ORDER BY entity_name
            """
            
            cursor.execute(query, (processing_id,))
            results = cursor.fetchall()
            
            stats = {
                'total_unique_entities': len(results),
                'entities_with_multiple_values': [],
                'entities_with_single_value': [],
                'entity_details': []
            }
            
            for row in results:
                entity_info = dict(row)
                stats['entity_details'].append(entity_info)
                
                if row['value_count'] > 1:
                    stats['entities_with_multiple_values'].append({
                        'name': row['entity_name'],
                        'count': row['value_count'],
                        'values': row['all_values']
                    })
                else:
                    stats['entities_with_single_value'].append(row['entity_name'])
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get entity statistics: {str(e)}")
            return {}
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_best_value_per_entity(self, processing_id: int) -> Dict[str, Dict]:
        """
        Get the BEST (highest confidence) value for each entity
        Useful when you need single value per entity
        
        Returns:
            Dictionary with entity_name as key and best value info as value
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT DISTINCT ON (entity_name)
                    entity_name,
                    entity_value,
                    confidence_score,
                    page_number,
                    bounding_box
                FROM extracted_entities
                WHERE processing_id = %s
                ORDER BY entity_name, confidence_score DESC
            """
            
            cursor.execute(query, (processing_id,))
            results = cursor.fetchall()
            
            best_values = {}
            for row in results:
                best_values[row['entity_name']] = dict(row)
            
            return best_values
            
        except Exception as e:
            logger.error(f"Failed to get best values: {str(e)}")
            return {}
        finally:
            if conn:
                cursor.close()
                conn.close()
    
    def get_entities_with_locations(self, processing_id: int) -> List[Dict]:
        """Get entities with their bounding box locations formatted for visualization"""
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            query = """
                SELECT 
                    entity_name,
                    entity_value,
                    confidence_score,
                    page_number,
                    bounding_box->>'vertices' as vertices,
                    bounding_box->>'normalized_vertices' as normalized_vertices
                FROM extracted_entities
                WHERE processing_id = %s
                ORDER BY page_number, entity_name
            """
            
            cursor.execute(query, (processing_id,))
            results = cursor.fetchall()
            
            return [dict(row) for row in results]
            
        except Exception as e:
            logger.error(f"Failed to get entities with locations: {str(e)}")
            return []
        finally:
            if conn:
                cursor.close()
                conn.close()


# Test function
def test_database_connection():
    """Test database connection and schema"""
    try:
        db = DatabaseService()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Database connection successful!")
        print(f"PostgreSQL version: {version[0]}")
        
        # Test tables exist
        cursor.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public'
        """)
        tables = cursor.fetchall()
        print(f"\n✅ Tables found: {[t[0] for t in tables]}")
        
        # Check extracted_entities columns
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'extracted_entities'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        print(f"\n✅ extracted_entities columns:")
        for col in columns:
            print(f"   • {col[0]}: {col[1]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        return False


if __name__ == "__main__":
    test_database_connection()
