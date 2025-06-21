#!/usr/bin/env python3
# create_tables.py - Run this to create the missing ProcessingStats table

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from database.models import Base, ProcessingStats, Document
from config.settings import Config

def create_tables():
    """Create all tables, including the new ProcessingStats table"""
    try:
        engine = create_engine(Config.DATABASE_URL)
        
        # Create all tables defined in Base.metadata
        Base.metadata.create_all(engine)
        
        print("✅ All tables created successfully!")
        print("📊 Tables created:")
        print("   - documents")
        print("   - processing_stats")
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = create_tables()
    if success:
        print("\n🚀 You can now run your application with ./scripts/run.sh")
    else:
        print("\n💥 Please check your database configuration and try again")
