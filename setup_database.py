# setup_database.py
import psycopg2
import sys
import os

# Add config to path
sys.path.insert(0, os.path.dirname(__file__))
from config.config import DB_CONFIG

def create_tables():
    """Create database tables and indexes with bounding box support and raw processor output"""
    
    # SQL for creating tables
    create_tables_sql = """
    -- Create document processing table with raw processor output
    CREATE TABLE IF NOT EXISTS document_processing (
        id SERIAL PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL,
        gcs_path VARCHAR(500) NOT NULL,
        processing_status VARCHAR(50) NOT NULL CHECK (processing_status IN ('SUCCESS', 'FAILED', 'PROCESSING')),
        document_status VARCHAR(50) CHECK (document_status IN ('SUCCESS', 'FAILED', 'PENDING', 'PENDING_REVIEW')),
        min_confidence DECIMAL(3,2),
        exception_reason_code VARCHAR(20),
        exception_reason_description TEXT,
        exception_entities JSONB,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT,
        raw_processor_output JSONB
    );

    -- Create entities table with bounding box support
    CREATE TABLE IF NOT EXISTS extracted_entities (
        id SERIAL PRIMARY KEY,
        processing_id INTEGER REFERENCES document_processing(id) ON DELETE CASCADE,
        entity_name VARCHAR(50) NOT NULL,
        entity_value TEXT,
        confidence_score DECIMAL(3,2),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        page_number INTEGER,
        bounding_box JSONB
    );

    COMMENT ON COLUMN document_processing.processing_status IS 
    'Document AI processing status: SUCCESS (AI processed successfully), FAILED (AI processing failed due to network/service issues), PROCESSING (currently being processed)';
    
    COMMENT ON COLUMN document_processing.document_status IS 
    'Document extraction validation status: SUCCESS (all entities extracted with confidence above threshold), FAILED (missing entities), PENDING (not yet validated), PENDING_REVIEW (all entities present but min confidence below threshold)';
    
    COMMENT ON COLUMN document_processing.min_confidence IS 
    'Minimum confidence score among all extracted entities (0.00-1.00). Used to determine if document needs review.';
    
    COMMENT ON COLUMN document_processing.exception_reason_code IS 
    'Exception code for validation failures: MISSING_ENTITIES, LOW_CONFIDENCE, PROCESSING_ERROR, etc.';
    
    COMMENT ON COLUMN document_processing.exception_reason_description IS 
    'Detailed description of validation failures including specific missing entities or low confidence fields';
    
    COMMENT ON COLUMN document_processing.exception_entities IS 
    'JSON object containing details of entities that caused exceptions: {"missing": [], "low_confidence": [{"name": "...", "confidence": 0.xx}]}';
    
    COMMENT ON COLUMN extracted_entities.bounding_box IS 
    'Bounding box coordinates in format: {"vertices": [{"x": float, "y": float}, ...], "normalized_vertices": [{"x": float, "y": float}, ...]}';
    
    COMMENT ON COLUMN document_processing.raw_processor_output IS 
    'Complete raw output from Document AI processor in JSON format for future analysis and reprocessing';

    -- Create indexes for performance
    CREATE INDEX IF NOT EXISTS idx_document_processing_status ON document_processing(processing_status);
    CREATE INDEX IF NOT EXISTS idx_document_processing_document_status ON document_processing(document_status);
    CREATE INDEX IF NOT EXISTS idx_document_processing_exception_code ON document_processing(exception_reason_code);
    CREATE INDEX IF NOT EXISTS idx_document_processing_min_confidence ON document_processing(min_confidence);
    CREATE INDEX IF NOT EXISTS idx_extracted_entities_processing_id ON extracted_entities(processing_id);
    CREATE INDEX IF NOT EXISTS idx_extracted_entities_name ON extracted_entities(entity_name);
    CREATE INDEX IF NOT EXISTS idx_extracted_entities_page_number ON extracted_entities(page_number);
    
    -- Performance indexes for new schema
    CREATE INDEX IF NOT EXISTS idx_document_processing_file_name ON document_processing(file_name);
    CREATE INDEX IF NOT EXISTS idx_document_processing_status_created ON document_processing(processing_status, created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_document_processing_gcs_path ON document_processing USING hash(gcs_path);
    
    -- GIN index for JSONB columns for efficient searching
    CREATE INDEX IF NOT EXISTS idx_extracted_entities_bounding_box_gin ON extracted_entities USING gin(bounding_box);
    CREATE INDEX IF NOT EXISTS idx_document_processing_raw_output_gin ON document_processing USING gin(raw_processor_output);
    CREATE INDEX IF NOT EXISTS idx_document_processing_exception_entities_gin ON document_processing USING gin(exception_entities);
    """
    
    # SQL for test data
    test_data_sql = """
    -- Insert test record with sample raw processor output (only if table is empty)
    INSERT INTO document_processing (file_name, gcs_path, processing_status, document_status, min_confidence, raw_processor_output)
    SELECT 
        'test_invoice.pdf', 
        'gs://sample_invoice_bucket_coe/input/test_invoice.pdf', 
        'SUCCESS',
        'PENDING',
        0.85,
        '{"test_data": true, "entities_count": 0, "mock_document": {"text": "Sample invoice document", "pages": [{"page_number": 0}]}}'::jsonb
    WHERE NOT EXISTS (SELECT 1 FROM document_processing WHERE file_name = 'test_invoice.pdf');
    """
    
    try:
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔗 Connected to database successfully!")
        
        # Create tables
        print("📋 Creating tables...")
        cursor.execute(create_tables_sql)
        
        # Insert test data
        print("📝 Inserting test data...")
        cursor.execute(test_data_sql)
        
        # Commit changes
        conn.commit()
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
        """)
        tables = cursor.fetchall()
        print(f"✅ Tables created: {[table[0] for table in tables]}")
        
        # Display document_processing schema
        print("\n📋 document_processing table schema (Updated v1.1.0):")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'document_processing'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            marker = "🆕" if col[0] == 'raw_processor_output' else "  "
            print(f"   {marker} {col[0]}: {col[1]} (nullable: {col[2]})")

        # Display extracted_entities schema
        print("\n📋 extracted_entities table schema:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'extracted_entities'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"   • {col[0]}: {col[1]} (nullable: {col[2]})")
        
        # Check record count
        cursor.execute("SELECT COUNT(*) FROM document_processing;")
        count = cursor.fetchone()[0]
        print(f"\n✅ Document processing records: {count}")
        
        cursor.execute("SELECT COUNT(*) FROM extracted_entities;")
        count = cursor.fetchone()[0]
        print(f"✅ Extracted entities records: {count}")
        
        # Display column comments  
        print("\n📝 Column comments:")
        cursor.execute("""
            SELECT 
                t.table_name,
                cols.column_name,
                pg_catalog.col_description(c.oid, cols.ordinal_position::int)
            FROM information_schema.columns cols
            JOIN pg_catalog.pg_class c ON c.relname = cols.table_name
            JOIN information_schema.tables t ON t.table_name = cols.table_name
            WHERE t.table_name IN ('document_processing', 'extracted_entities')
            AND pg_catalog.col_description(c.oid, cols.ordinal_position::int) IS NOT NULL
            ORDER BY t.table_name, cols.ordinal_position
        """)
        comments = cursor.fetchall()
        for comment in comments:
            print(f"   • {comment[0]}.{comment[1]}: {comment[2]}")
        
        # Display performance indexes
        print("\n🚀 Performance indexes created:")
        cursor.execute("""
            SELECT indexname, tablename 
            FROM pg_indexes 
            WHERE tablename IN ('document_processing', 'extracted_entities')
            AND indexname LIKE 'idx_%'
            ORDER BY tablename, indexname
        """)
        indexes = cursor.fetchall()
        for idx in indexes:
            marker = "🆕" if 'gin' in idx[0] or 'file_name' in idx[0] or 'status_created' in idx[0] or 'gcs_path' in idx[0] else "  "
            print(f"   {marker} {idx[1]}: {idx[0]}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database setup completed successfully!")
        print("✅ New Features:")
        print("   🆕 Raw processor output storage (JSONB)")
        print("   🚀 Performance indexes for faster queries")
        print("   🔍 JSONB search capabilities") 
        print("   📦 Bounding box support")
        print("   🆕 Document status validation (separate from processing status)")
        print("   🆕 Exception reason codes and descriptions")
        print("   🆕 Exception entities tracking (which specific entities failed)")
        print("   🆕 Minimum confidence tracking for review workflow")
        print("   🆕 PENDING_REVIEW status for low confidence documents")
        print("   ❌ Removed: extraction_confidence (use entity-level confidence instead)")
        return True
        
    except Exception as e:
        print(f"❌ Database setup failed: {e}")
        return False

def migrate_existing_table():
    """Add bounding box columns to existing extracted_entities table"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("🔧 Migrating existing table to add bounding box support...")
        
        # Add new columns if they don't exist
        cursor.execute("""
            ALTER TABLE extracted_entities 
            ADD COLUMN IF NOT EXISTS page_number INTEGER,
            ADD COLUMN IF NOT EXISTS bounding_box JSONB;
        """)
        
        # Add column comment
        cursor.execute("""
            COMMENT ON COLUMN extracted_entities.bounding_box IS 
            'Bounding box coordinates in format: {"vertices": [{"x": float, "y": float}, ...], "normalized_vertices": [{"x": float, "y": float}, ...]}';
        """)
        
        # Add index for page_number
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_extracted_entities_page_number 
            ON extracted_entities(page_number);
        """)
        
        conn.commit()
        
        print("✅ Migration completed successfully!")
        
        # Display updated schema
        print("\n📋 Updated schema:")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'extracted_entities'
            ORDER BY ordinal_position
        """)
        columns = cursor.fetchall()
        for col in columns:
            print(f"   • {col[0]}: {col[1]} (nullable: {col[2]})")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def test_connection():
    """Test database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"✅ Database connection successful!")
        print(f"PostgreSQL version: {version[0][:50]}...")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def check_table_exists():
    """Check if tables already exist"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'extracted_entities'
            );
        """)
        exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        return exists
        
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting database setup...")
    print("=" * 80)
    
    # Test connection first
    if not test_connection():
        sys.exit(1)
    
    print("\n" + "=" * 80)
    
    # Check if table already exists
    table_exists = check_table_exists()
    
    if table_exists:
        print("📋 Table 'extracted_entities' already exists")
        response = input("\nDo you want to migrate existing table to add bounding box support? (yes/no): ")
        
        if response.lower() == 'yes':
            if migrate_existing_table():
                print("\n✅ Migration complete! Table updated with bounding box support")
            else:
                sys.exit(1)
        else:
            print("Skipping migration. Using existing table structure.")
    else:
        print("📋 Creating new tables with bounding box support...")
        if create_tables():
            print("\n✅ Database setup complete! Ready for Step 2")
        else:
            sys.exit(1)
    
    print("\n" + "=" * 80)
    print("🎉 Setup completed successfully!")
