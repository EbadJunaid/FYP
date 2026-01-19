#!/usr/bin/env python3
"""
Pre-compute CA Analytics and store in materialized view collection
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
    print_progress("CA ANALYTICS MATERIALIZED VIEW GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Step 1: Connect to MongoDB
    print_progress("Step 1/6: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    # Step 2: Access source database and collection
    print_progress("Step 2/6: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    # Get total document count
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    # Step 3: Create/access target database and collection
    print_progress("Step 3/6: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['ca-analytics']
    print_success("Target database and collection ready")
    
    # Step 4: Run aggregation pipeline
    print_progress("Step 4/6: Computing CA distribution...")
    print_info("This will take 2-3 minutes to scan all documents...")
    print()
    
    pipeline = [
        # Project only the issuer organization field
        {'$project': {
            'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
        }},
        # Filter out null/missing issuers
        {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
        # Group by issuer and count
        {'$group': {
            '_id': '$issuer_org',
            'count': {'$sum': 1}
        }},
        # Sort by count descending
        {'$sort': {'count': -1}}
    ]
    
    try:
        # Run aggregation with progress tracking
        start_time = datetime.now()
        print_info(f"Aggregation started at: {start_time.strftime('%H:%M:%S')}")
        
        results = list(source_collection.aggregate(
            pipeline,
            hint='idx_issuer_org',
            allowDiskUse=True
        ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        print_success(f"Found {len(results)} unique Certificate Authorities")
        print()
        
    except Exception as e:
        print_error(f"Aggregation failed: {str(e)}")
        sys.exit(1)
    
    # Step 5: Prepare data for storage
    print_progress("Step 5/6: Preparing data for storage...")
    
    if not results:
        print_error("No results to store")
        sys.exit(1)
    
    # Calculate total certificates with valid issuer
    total_with_issuer = sum(r['count'] for r in results)
    max_count = results[0]['count'] if results else 1
    
    # Color palette for visualization
    colors = [
        '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444',
        '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
        '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#d946ef',
        '#eab308', '#6b7280'
    ]
    
    # Transform results into API-ready format
    ca_records = []
    for i, result in enumerate(results):
        ca_record = {
            'ca_id': f'ca-{i}',
            'name': result['_id'],
            'count': result['count'],
            'max_count': max_count,
            'percentage': round((result['count'] / total_with_issuer) * 100, 1),
            'color': colors[i % len(colors)],
            'rank': i + 1,
            'computed_at': datetime.now(timezone.utc),
            'total_certificates': total_with_issuer
        }
        ca_records.append(ca_record)
    
    print_success(f"Prepared {len(ca_records)} CA records")
    
    # Display top 10 CAs
    print()
    print_info("Top 10 Certificate Authorities:")
    print()
    for record in ca_records[:10]:
        bar_length = int((record['count'] / max_count) * 40)
        bar = '█' * bar_length
        print(f"  {record['rank']:2}. {record['name'][:40]:<40} {bar} {record['count']:>7,} ({record['percentage']:>5.1f}%)")
    print()
    
    # Step 6: Store in target collection
    print_progress("Step 6/6: Storing results in database...")
    
    try:
        # Clear existing data
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        # Insert new data
        if ca_records:
            result = target_collection.insert_many(ca_records)
            print_success(f"Inserted {len(result.inserted_ids)} records")
        
        # Create index on rank for fast sorting
        target_collection.create_index('rank')
        target_collection.create_index('computed_at')
        print_success("Created indexes on target collection")
        
        # Store metadata document
        metadata = {
            '_id': 'metadata',
            'last_computed': datetime.now(timezone.utc),
            'computation_duration_seconds': duration,
            'total_cas': len(ca_records),
            'total_certificates': total_with_issuer,
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
    print_success("CA ANALYTICS COMPUTATION COMPLETED SUCCESSFULLY!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Database: {BOLD}tranco-latest-8-lakh-results{RESET}")
    print_info(f"Collection: {BOLD}ca-analytics{RESET}")
    print_info(f"Total CAs: {BOLD}{len(ca_records):,}{RESET}")
    print_info(f"Computation Time: {BOLD}{duration:.1f}s{RESET}")
    print()
    print_info("Next steps:")
    print(f"  1. Update your API to read from this collection")
    print(f"  2. Set up a cron job to run this script every 6-12 hours")
    print(f"  3. Example: Add to crontab: 0 */12 * * * /path/to/python compute_ca_analytics.py")
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
