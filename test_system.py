#!/usr/bin/env python3
"""Simple test script to verify the API works"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    try:
        from fastapi import FastAPI
        print("✅ FastAPI imported successfully")
        
        import psycopg2
        print("✅ psycopg2 imported successfully")
        
        from src.database_service import DatabaseService
        print("✅ DatabaseService imported successfully")
        
        from src.gcs_file_manager import GCSFileManager
        print("✅ GCSFileManager imported successfully")
        
        import config.config as config
        print("✅ Config imported successfully")
        
        # Test config values
        print(f"✅ Database host: {config.DATABASE_HOST}")
        print(f"✅ Database name: {config.DATABASE_NAME}")
        print(f"✅ GCS bucket: {config.GCS_BUCKET}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_database_connection():
    """Test database connection"""
    try:
        import psycopg2
        import config.config as config
        
        conn = psycopg2.connect(
            host=config.DATABASE_HOST,
            database=config.DATABASE_NAME,
            user=config.DATABASE_USER,
            password=config.DATABASE_PASSWORD,
            port=config.DATABASE_PORT
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if result and result[0] == 1:
            print("✅ Database connection successful")
            return True
        else:
            print("❌ Database connection test failed")
            return False
            
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False

def test_api_startup():
    """Test if the API can start up"""
    try:
        from api import app
        print("✅ API app created successfully")
        
        # Check if app has endpoints
        routes = [route.path for route in app.routes]
        print(f"✅ API has {len(routes)} routes defined")
        
        expected_routes = ["/api/documents", "/api/upload", "/api/stats"]
        found_routes = []
        
        for expected in expected_routes:
            for route in routes:
                if expected in route:
                    found_routes.append(expected)
                    break
        
        print(f"✅ Found expected routes: {found_routes}")
        return True
        
    except Exception as e:
        print(f"❌ API startup error: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting API and Database Tests...\n")
    
    all_passed = True
    
    print("1. Testing imports...")
    all_passed &= test_imports()
    print()
    
    print("2. Testing database connection...")
    all_passed &= test_database_connection()
    print()
    
    print("3. Testing API startup...")
    all_passed &= test_api_startup()
    print()
    
    if all_passed:
        print("🎉 All tests passed! The system is ready.")
        sys.exit(0)
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)
