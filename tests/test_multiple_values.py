"""Test script to demonstrate handling of multiple entity values"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.database_service import DatabaseService
import json

def test_multiple_values_storage():
    """Test storing and retrieving multiple values for same entity"""
    
    print("=" * 80)
    print("Testing Multiple Entity Values Handling")
    print("=" * 80)
    
    db = DatabaseService()
    
    # Simulate Document AI extracting multiple values for same entity
    test_entities = [
        # Invoice has 3 different HSN codes (line items)
        {'name': 'hsn_number', 'value': '8471', 'confidence': 0.95, 'page_number': 0, 'bounding_box': {'vertices': [{'x': 100, 'y': 200}]}},
        {'name': 'hsn_number', 'value': '8473', 'confidence': 0.92, 'page_number': 0, 'bounding_box': {'vertices': [{'x': 100, 'y': 250}]}},
        {'name': 'hsn_number', 'value': '8517', 'confidence': 0.88, 'page_number': 0, 'bounding_box': {'vertices': [{'x': 100, 'y': 300}]}},
        
        # Single invoice number
        {'name': 'invoice_number', 'value': 'INV-2024-001', 'confidence': 0.98, 'page_number': 0, 'bounding_box': {'vertices': [{'x': 50, 'y': 50}]}},
        
        # Multiple vendor names (edge case - might be error in extraction)
        {'name': 'vendor_name', 'value': 'ABC Corp', 'confidence': 0.85, 'page_number': 0, 'bounding_box': None},
        {'name': 'vendor_name', 'value': 'ABC Corporation Ltd', 'confidence': 0.78, 'page_number': 0, 'bounding_box': None},
    ]
    
    # Store in database
    print("\n📝 Storing test data...")
    processing_id = db.store_processing_record(
        file_name='test_multiple_values.pdf',
        gcs_path='gs://test/test_multiple_values.pdf',
        status='SUCCESS',
        entities=test_entities,
        avg_confidence=0.89
    )
    
    print(f"✅ Stored with processing_id: {processing_id}")
    
    # Test 1: Get all entities (should have 6 rows)
    print("\n" + "=" * 80)
    print("Test 1: Get ALL Entities (including duplicates)")
    print("=" * 80)
    all_entities = db.get_extracted_entities(processing_id)
    print(f"Total rows: {len(all_entities)}")
    for entity in all_entities:
        print(f"  • {entity['entity_name']}: {entity['entity_value']} (confidence: {entity['confidence_score']})")
    
    # Test 2: Get entities grouped by name
    print("\n" + "=" * 80)
    print("Test 2: Get Entities GROUPED by Name")
    print("=" * 80)
    grouped = db.get_entities_grouped_by_name(processing_id)
    for entity_name, values in grouped.items():
        print(f"\n{entity_name}:")
        for val in values:
            print(f"  • {val['entity_value']} (confidence: {val['confidence_score']})")
    
    # Test 3: Get statistics
    print("\n" + "=" * 80)
    print("Test 3: Get Statistics")
    print("=" * 80)
    stats = db.get_entity_statistics(processing_id)
    print(f"Total unique entities: {stats['total_unique_entities']}")
    print(f"\nEntities with MULTIPLE values:")
    for entity in stats['entities_with_multiple_values']:
        print(f"  • {entity['name']}: {entity['count']} values → {entity['values']}")
    print(f"\nEntities with SINGLE value:")
    for entity_name in stats['entities_with_single_value']:
        print(f"  • {entity_name}")
    
    # Test 4: Get best value per entity
    print("\n" + "=" * 80)
    print("Test 4: Get BEST (Highest Confidence) Value per Entity")
    print("=" * 80)
    best_values = db.get_best_value_per_entity(processing_id)
    for entity_name, value_info in best_values.items():
        print(f"  • {entity_name}: {value_info['entity_value']} (confidence: {value_info['confidence_score']})")
    
    print("\n" + "=" * 80)
    print("✅ All tests completed successfully!")
    print("=" * 80)


if __name__ == "__main__":
    test_multiple_values_storage()
