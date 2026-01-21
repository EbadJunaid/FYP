#!/usr/bin/env python3
"""
Pre-compute SAN TLD Breakdown - stores top TLDs from SAN entries
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
    print_progress("SAN TLD BREAKDOWN MATERIALIZED VIEW GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Connect to MongoDB
    print_progress("Step 1/5: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    print_progress("Step 2/5: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    print_progress("Step 3/5: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['san-tld-breakdown']
    print_success("Target database and collection ready")
    
    print_progress("Step 4/5: Computing SAN TLD breakdown...")
    print_info("This will take 2-3 minutes to process all SAN entries...")
    print()
    
    start_time = datetime.now()
    
    # Compute top 100 TLDs (API will limit to requested amount)
    pipeline = [
        # Filter documents that have dns_names
        {'$match': {
            'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
        }},
        # Unwind the dns_names array
        {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
        # Project and extract TLD from each dns name
        {'$project': {
            'dnsName': '$parsed.extensions.subject_alt_name.dns_names',
            'tld': {
                '$let': {
                    'vars': {
                        'parts': {'$split': ['$parsed.extensions.subject_alt_name.dns_names', '.']}
                    },
                    'in': {'$arrayElemAt': ['$$parts', -1]}
                }
            }
        }},
        # Filter out wildcards and empty TLDs
        {'$match': {
            'tld': {'$exists': True, '$ne': None, '$ne': ''},
            'dnsName': {'$not': {'$regex': '^\\*'}}
        }},
        # Group by TLD
        {'$group': {
            '_id': {'$toLower': '$tld'},
            'count': {'$sum': 1}
        }},
        # Sort by count
        {'$sort': {'count': -1}},
        # Get top 100
        {'$limit': 100}
    ]
    
    try:
        print_info(f"Aggregation started at: {start_time.strftime('%H:%M:%S')}")
        
        results = list(source_collection.aggregate(
            pipeline,
            hint='idx_san_dns_names',
            allowDiskUse=True
        ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        print_success(f"Found {len(results)} TLDs")
        print()
        
        # Prepare documents for storage
        tld_docs = []
        for i, r in enumerate(results):
            tld_docs.append({
                'tld_id': i,
                'tld': f".{r['_id']}",
                'count': r['count'],
                'rank': i + 1,
                'computed_at': datetime.now(timezone.utc)
            })
        
        # Display top 10
        print_info("Top 10 TLDs:")
        for doc in tld_docs[:10]:
            print(f"  {doc['rank']:2}. {doc['tld']:<10} = {doc['count']:>7,} entries")
        print()
        
        # Store in target collection
        print_progress("Step 5/5: Storing results in database...")
        
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        if tld_docs:
            target_collection.insert_many(tld_docs)
            print_success(f"Inserted {len(tld_docs)} TLD records")
        
        # Create indexes
        target_collection.create_index('rank')
        target_collection.create_index('computed_at')
        print_success("Created indexes")
        
        # Store metadata
        metadata = {
            '_id': 'metadata',
            'last_computed': datetime.now(timezone.utc),
            'computation_duration_seconds': duration,
            'total_tlds': len(tld_docs)
        }
        target_collection.replace_one(
            {'_id': 'metadata'},
            metadata,
            upsert=True
        )
        print_success("Stored metadata")
        
    except Exception as e:
        print_error(f"Computation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("SAN TLD BREAKDOWN COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Stored in: {BOLD}tranco-latest-8-lakh-results.san-tld-breakdown{RESET}")
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
