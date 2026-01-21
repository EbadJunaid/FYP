#!/usr/bin/env python3
"""
Pre-compute SAN Wildcard Breakdown - stores wildcard vs standard counts
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
    print_progress("SAN WILDCARD BREAKDOWN MATERIALIZED VIEW GENERATOR", BOLD)
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
    target_collection = target_db['san-wildcard-breakdown']
    print_success("Target database and collection ready")
    
    print_progress("Step 4/4: Computing SAN wildcard breakdown...")
    print_info("This will take 2-3 minutes to process all SAN entries...")
    print()
    
    start_time = datetime.now()
    
    pipeline = [
        # Filter documents that have dns_names
        {'$match': {
            'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
        }},
        # Unwind the dns_names array
        {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
        # Project to check if wildcard
        {'$project': {
            'isWildcard': {'$regexMatch': {'input': '$parsed.extensions.subject_alt_name.dns_names', 'regex': '^\\*\\.'}}
        }},
        # Group by wildcard status
        {'$group': {
            '_id': '$isWildcard',
            'count': {'$sum': 1}
        }}
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
        
        # Parse results
        breakdown = {'wildcard': 0, 'standard': 0}
        for r in results:
            if r['_id'] is True:
                breakdown['wildcard'] = r['count']
            else:
                breakdown['standard'] = r['count']
        
        # Create single document
        breakdown_doc = {
            '_id': 'san_wildcard_breakdown',
            'wildcard': breakdown['wildcard'],
            'standard': breakdown['standard'],
            'total': breakdown['wildcard'] + breakdown['standard'],
            'wildcard_percentage': round((breakdown['wildcard'] / (breakdown['wildcard'] + breakdown['standard']) * 100), 2) if (breakdown['wildcard'] + breakdown['standard']) > 0 else 0,
            'computed_at': datetime.now(timezone.utc),
            'computation_duration_seconds': round(duration, 2)
        }
        
        print()
        print_info("Wildcard Breakdown:")
        print(f"  • Wildcard: {BOLD}{breakdown_doc['wildcard']:,}{RESET} ({breakdown_doc['wildcard_percentage']}%)")
        print(f"  • Standard: {BOLD}{breakdown_doc['standard']:,}{RESET}")
        print(f"  • Total: {BOLD}{breakdown_doc['total']:,}{RESET}")
        print()
        
        # Store in target collection
        print_progress("Storing results in database...")
        
        target_collection.replace_one(
            {'_id': 'san_wildcard_breakdown'},
            breakdown_doc,
            upsert=True
        )
        print_success("Stored wildcard breakdown document")
        
    except Exception as e:
        print_error(f"Computation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("SAN WILDCARD BREAKDOWN COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Stored in: {BOLD}tranco-latest-8-lakh-results.san-wildcard-breakdown{RESET}")
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
