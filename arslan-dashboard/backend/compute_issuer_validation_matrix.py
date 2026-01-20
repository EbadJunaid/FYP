#!/usr/bin/env python3
"""
Pre-compute Issuer Validation Matrix - stores top issuers × validation levels
This script should be run periodically (e.g., every 6-12 hours via cron job)
"""

import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Color codes for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_progress(message, color=BLUE):
    """Print colored progress message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}{BOLD}[{timestamp}]{RESET} {color}{message}{RESET}")

def print_success(message):
    """Print success message"""
    print_progress(f"✓ {message}", GREEN)

def print_error(message):
    """Print error message"""
    print_progress(f"✗ {message}", RED)

def print_info(message):
    """Print info message"""
    print_progress(f"ℹ {message}", YELLOW)

def main():
    """Main execution function"""
    
    print_progress("=" * 70, BOLD)
    print_progress("ISSUER VALIDATION MATRIX GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Step 1: Connect to MongoDB
    print_progress("Step 1/5: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    # Step 2: Access source database and collection
    print_progress("Step 2/5: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    # Step 3: Access target database
    print_progress("Step 3/5: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['issuer-validation-matrix']
    print_success("Target database and collection ready")
    
    # Step 4: Run aggregation to get issuer × validation level combinations
    print_progress("Step 4/5: Computing issuer × validation level matrix...")
    print_info("This will take 1-2 minutes to scan all documents...")
    print()
    
    start_time = datetime.now()
    
    pipeline = [
        # Stage 1: Project needed fields only
        {'$project': {
            'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
            'validationLevel': {'$ifNull': ['$parsed.validation_level', 'Unknown']}
        }},
        # Stage 2: Filter out null issuers
        {'$match': {'issuer': {'$exists': True, '$ne': None}}},
        # Stage 3: Group by issuer + validationLevel
        {'$group': {
            '_id': {
                'issuer': '$issuer',
                'validationLevel': '$validationLevel'
            },
            'count': {'$sum': 1}
        }},
        # Stage 4: Sort by count
        {'$sort': {'count': -1}}
    ]
    
    try:
        print_info(f"Aggregation started at: {start_time.strftime('%H:%M:%S')}")
        
        results = list(source_collection.aggregate(
            pipeline,
            hint='idx_issuer_org',
            allowDiskUse=True
        ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        print_success(f"Found {len(results)} issuer × validation combinations")
        print()
        
    except Exception as e:
        print_error(f"Aggregation failed: {str(e)}")
        sys.exit(1)
    
    # Step 5: Process results and store ALL combinations
    print_progress("Step 5/5: Processing and storing results...")
    
    if not results:
        print_error("No results to store")
        sys.exit(1)
    
    # Calculate issuer totals to determine top issuers
    issuer_totals = {}
    for r in results:
        issuer = r['_id']['issuer']
        issuer_totals[issuer] = issuer_totals.get(issuer, 0) + r['count']
    
    # Get top 50 issuers (will be filtered by API with limit parameter)
    top_issuers = sorted(issuer_totals.items(), key=lambda x: x[1], reverse=True)[:50]
    top_issuer_names = {issuer for issuer, _ in top_issuers}
    
    # Prepare matrix records for top issuers only
    matrix_records = []
    for i, r in enumerate(results):
        issuer = r['_id']['issuer']
        if issuer in top_issuer_names:
            record = {
                'record_id': f'matrix-{i}',
                'issuer': issuer,
                'validationLevel': r['_id']['validationLevel'],
                'count': r['count'],
                'issuer_total': issuer_totals[issuer],
                'computed_at': datetime.now(timezone.utc)
            }
            matrix_records.append(record)
    
    print_success(f"Prepared {len(matrix_records)} matrix records for top 50 issuers")
    
    # Display top 10 issuer × validation combinations
    print()
    print_info("Top 10 Issuer × Validation Level Combinations:")
    print()
    for i, record in enumerate(matrix_records[:10], 1):
        print(f"  {i:2}. {record['issuer'][:35]:<35} × {record['validationLevel']:<8} = {record['count']:>7,} certs")
    print()
    
    # Store in target collection
    print_progress("Storing results in database...")
    
    try:
        # Clear existing data
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        # Insert new data
        if matrix_records:
            result = target_collection.insert_many(matrix_records)
            print_success(f"Inserted {len(result.inserted_ids)} records")
        
        # Create indexes
        target_collection.create_index('issuer')
        target_collection.create_index('issuer_total')
        target_collection.create_index('computed_at')
        target_collection.create_index([('issuer_total', -1), ('count', -1)])
        print_success("Created indexes on target collection")
        
        # Store metadata
        metadata = {
            '_id': 'metadata',
            'last_computed': datetime.now(timezone.utc),
            'computation_duration_seconds': duration,
            'total_combinations': len(matrix_records),
            'total_issuers': len(top_issuer_names),
            'source_database': 'tranco-latest-8-lakh',
            'source_collection': 'certificates'
        }
        target_collection.replace_one(
            {'_id': 'metadata'},
            metadata,
            upsert=True
        )
        print_success("Stored computation metadata")
        
    except Exception as e:
        print_error(f"Failed to store results: {str(e)}")
        sys.exit(1)
    
    # Final summary
    print()
    print_progress("=" * 70, BOLD)
    print_success("ISSUER VALIDATION MATRIX COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Database: {BOLD}tranco-latest-8-lakh-results{RESET}")
    print_info(f"Collection: {BOLD}issuer-validation-matrix{RESET}")
    print_info(f"Total Records: {BOLD}{len(matrix_records):,}{RESET}")
    print_info(f"Computation Time: {BOLD}{duration:.1f}s{RESET}")
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
