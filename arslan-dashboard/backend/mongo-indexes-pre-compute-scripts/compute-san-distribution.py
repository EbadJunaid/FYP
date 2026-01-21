#!/usr/bin/env python3
"""
Pre-compute SAN Distribution - stores histogram buckets
This script should be run periodically (e.g., every 6-12 hours via cron job)
"""

import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_progress(message, color=BLUE):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}{BOLD}[{timestamp}]{RESET} {color}{message}{RESET}")

def print_success(message):
    print_progress(f"✓ {message}", GREEN)

def print_error(message):
    print_progress(f"✗ {message}", RED)

def print_info(message):
    print_progress(f"ℹ {message}", YELLOW)

def main():
    print_progress("=" * 70, BOLD)
    print_progress("SAN DISTRIBUTION MATERIALIZED VIEW GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Connect to MongoDB
    print_progress("Step 1/4: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    print_progress("Step 2/4: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    print_progress("Step 3/4: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['san-distribution']
    print_success("Target database and collection ready")
    
    print_progress("Step 4/4: Computing SAN distribution...")
    start_time = datetime.now()
    
    pipeline = [
        {'$project': {
            'sanCount': {'$size': {'$ifNull': ['$parsed.names', []]}}
        }},
        {'$bucket': {
            'groupBy': '$sanCount',
            'boundaries': [0, 1, 2, 4, 6, 11, 21, 51],
            'default': '50+',
            'output': {'count': {'$sum': 1}}
        }}
    ]
    
    try:
        results = list(source_collection.aggregate(pipeline, allowDiskUse=True))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        
        # Map bucket IDs to readable labels
        bucket_labels = {
            0: '0',
            1: '1',
            2: '2-3',
            4: '4-5',
            6: '6-10',
            11: '11-20',
            21: '21-50',
            '50+': '50+'
        }
        
        distribution_docs = []
        for i, r in enumerate(results):
            bucket_id = r['_id']
            label = bucket_labels.get(bucket_id, str(bucket_id))
            distribution_docs.append({
                'bucket_id': i,
                'bucket': label,
                'count': r['count'],
                'computed_at': datetime.now(timezone.utc)
            })
        
        print()
        print_info("Distribution Buckets:")
        for doc in distribution_docs:
            print(f"  {doc['bucket']:<10} = {doc['count']:>7,} certificates")
        print()
        
        # Store in target collection
        print_progress("Storing results in database...")
        
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        if distribution_docs:
            target_collection.insert_many(distribution_docs)
            print_success(f"Inserted {len(distribution_docs)} bucket records")
        
        # Store metadata
        metadata = {
            '_id': 'metadata',
            'last_computed': datetime.now(timezone.utc),
            'computation_duration_seconds': duration,
            'total_buckets': len(distribution_docs)
        }
        target_collection.replace_one(
            {'_id': 'metadata'},
            metadata,
            upsert=True
        )
        print_success("Stored metadata")
        
    except Exception as e:
        print_error(f"Computation failed: {str(e)}")
        sys.exit(1)
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("SAN DISTRIBUTION COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Stored in: {BOLD}tranco-latest-8-lakh-results.san-distribution{RESET}")
    print_info(f"Computation Time: {BOLD}{duration:.2f}s{RESET}")
    print()
    
    client.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_error("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
