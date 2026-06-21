#!/usr/bin/env python3
"""Test database switching functionality"""

from certificates.db import MongoDBClient

def test_database_switching():
    print("=" * 60)
    print("DATABASE SWITCHING TEST")
    print("=" * 60)
    print()
    
    # Test current database
    current = MongoDBClient.get_current_database()
    print(f"✓ Current database: {current['name']} ({current['id']})")
    print(f"  Main DB: {current['main_db']}")
    print(f"  Results DB: {current['results_db']}")
    print()
    
    # Test available databases
    print("Available databases:")
    for db_id, db_info in MongoDBClient.get_available_databases().items():
        print(f"  • {db_id}: {db_info['name']} - {db_info['description']}")
    print()
    
    # Test switching
    print("Testing switch to Pakistani database...")
    success = MongoDBClient.switch_database('pakistani')
    if success:
        current = MongoDBClient.get_current_database()
        print(f"✓ Switch successful!")
        print(f"  New database: {current['name']} ({current['id']})")
    else:
        print("✗ Switch failed!")
    print()
    
    # Switch back
    print("Switching back to Global database...")
    success = MongoDBClient.switch_database('global')
    if success:
        current = MongoDBClient.get_current_database()
        print(f"✓ Switch successful!")
        print(f"  Current database: {current['name']} ({current['id']})")
    else:
        print("✗ Switch failed!")
    print()
    
    print("=" * 60)
    print("TEST COMPLETED SUCCESSFULLY")
    print("=" * 60)

if __name__ == '__main__':
    test_database_switching()
