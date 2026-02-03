#!/usr/bin/env python3
"""
Quick verification script to test the updated schema and functionality
(FIXED VERSION – structural + indentation errors removed)
"""
import sys
import os

# Add current directory to path  
sys.path.insert(0, os.path.dirname(__file__))


def test_database_setup():
    """Test the database setup with new schema"""
    print("🧪 Testing Database Setup with New Schema")
    print("=" * 50)

    try:
        from src.database_service import DatabaseService
        db = DatabaseService()
        conn = db.get_connection()

        if conn:
            print("✅ Database connection successful")
            conn.close()
        else:
            print("❌ Database connection failed")
            return False

    except Exception as e:
        print(f"❌ Database connection error: {str(e)}")
        return False

    return True



def test_new_schema():
    """Test the new schema features including document_status and exception codes"""
    print("\n🔍 Testing New Schema Features")
    print("=" * 50)

    try:
        from src.database_service import DatabaseService
        from config.config import EXCEPTION_CODES, get_exception_details

        db = DatabaseService()

        test_raw_output = {
            "test": True,
            "entities": [
                {"type": "invoice_number", "value": "INV-001", "confidence": 0.95}
            ],
            "metadata": {"test_run": True}
        }

        # ------------------- Test 1 -------------------
        print("Test 1: Success case...")
        processing_id_1 = db.store_processing_record(
            file_name="test_success.pdf",
            gcs_path="gs://test-bucket/test_success.pdf",
            processing_status="SUCCESS",
            document_status="SUCCESS",
            min_confidence=0.95,
            entities=[],
            raw_processor_output=test_raw_output
        )
        print(f"✅ Stored successful record with ID: {processing_id_1}")

        # ------------------- Test 2 -------------------
        print("Test 2: Missing entities validation failure...")
        missing_entities = ['invoice_number', 'vendor_name']

        exception_code, exception_desc, exception_entities = get_exception_details(
            missing_entities, None, 0.75
        )

        processing_id_2 = db.store_processing_record(
            file_name="test_missing_entities.pdf",
            gcs_path="gs://test-bucket/test_missing_entities.pdf",
            processing_status="SUCCESS",
            document_status="FAILED",
            min_confidence=0.75,
            exception_reason_code=exception_code,
            exception_reason_description=exception_desc,
            exception_entities=exception_entities,
            entities=[],
            raw_processor_output=test_raw_output
        )

        print(f"✅ Stored missing entities failure record with ID: {processing_id_2}")

        # ------------------- Test 3 -------------------
        print("Test 3: Low confidence - needs review...")
        low_confidence = [
            {'name': 'invoice_date', 'confidence': 0.45},
            {'name': 'total_amount', 'confidence': 0.55}
        ]

        exception_code, exception_desc, exception_entities = get_exception_details(
            None, low_confidence, 0.45
        )

        processing_id_3 = db.store_processing_record(
            file_name="test_low_confidence.pdf",
            gcs_path="gs://test-bucket/test_low_confidence.pdf",
            processing_status="SUCCESS",
            document_status="PENDING_REVIEW",
            min_confidence=0.45,
            exception_reason_code=exception_code,
            exception_reason_description=exception_desc,
            exception_entities=exception_entities,
            entities=[],
            raw_processor_output=test_raw_output
        )

        print(f"✅ Stored low confidence review record with ID: {processing_id_3}")

        # ------------------- Test 4 -------------------
        print("Test 4: Document AI processing failure...")
        processing_id_4 = db.store_processing_record(
            file_name="test_processing_fail.pdf",
            gcs_path="gs://test-bucket/test_processing_fail.pdf",
            processing_status="FAILED",
            document_status="PENDING",
            exception_reason_code=EXCEPTION_CODES['DOCUMENT_AI_ERROR'],
            exception_reason_description="Document AI service timeout error",
            exception_entities={"error_type": "document_ai_timeout", "service": "Document AI"},
            error_message="Network timeout during Document AI processing"
        )

        print(f"✅ Stored processing failure record with ID: {processing_id_4}")

        # ------------------- Test 5 -------------------
        print("Test 5: Testing document status update...")
        update_success = db.update_document_status(
            processing_id_4,
            document_status="FAILED",
            exception_reason_code=EXCEPTION_CODES['NETWORK_ERROR'],
            exception_reason_description="Updated after retry - network error persisted",
            exception_entities={"error_type": "persistent_network_error", "retry_count": 3}
        )

        print(f"✅ Document status update: {'Success' if update_success else 'Failed'}")

        # ------------------- Verification -------------------
        print("\n📊 Verifying stored records...")
        for pid in [processing_id_1, processing_id_2, processing_id_3, processing_id_4]:
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT file_name, processing_status, document_status, min_confidence,
                       exception_reason_code, exception_entities
                FROM document_processing WHERE id = %s
            """, (pid,))
            record = cursor.fetchone()

            if record:
                print(f"   ID {pid}: {record[0]} | Processing: {record[1]} | Document: {record[2]} | Min Conf: {record[3]} | Exception: {record[4]}")
                if record[5]:
                    print(f"      Exception Entities: {record[5]}")

            cursor.close()
            conn.close()

        return True

    except Exception as e:
        print(f"❌ Schema test error: {str(e)}")
        return False



def test_invoice_processor():
    """Test the invoice processor with new schema"""
    print("\n🏭 Testing Invoice Processor Integration")
    print("=" * 50)

    try:
        from src.invoice_processor import InvoiceProcessor
        from src.document_ai_processor import DocumentAIProcessor
        from src.gcs_file_manager import GCSFileManager

        print("🔧 Initializing components...")

        doc_ai = DocumentAIProcessor()
        print("✅ DocumentAI processor initialized")

        gcs = GCSFileManager()
        print("✅ GCS file manager initialized")

        processor = InvoiceProcessor()
        print("✅ Invoice processor initialized")

        print("\n📁 Checking for available files...")
        processor.list_available_files()

        return True

    except Exception as e:
        print(f"❌ Invoice processor test error: {str(e)}")
        return False



def main():
    """Main test function"""
    print("🚀 Schema Verification Script")
    print("Testing updated DocumentAI processing system with new schema")
    print("=" * 70)

    tests = [
        ("Database Setup", test_database_setup),
        ("New Schema Features", test_new_schema),
        ("Invoice Processor", test_invoice_processor)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            if test_func():
                print(f"✅ {test_name}: PASSED")
                passed += 1
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")

    print("\n" + "=" * 70)
    print("📊 TEST RESULTS")
    print("=" * 70)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("✨ Your updated schema is working correctly!")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
