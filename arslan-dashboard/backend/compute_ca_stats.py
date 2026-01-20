#!/usr/bin/env python3
"""
Pre-compute CA Stats (for metric cards) - stores a single document with all stats
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
    print_progress("CA STATS MATERIALIZED VIEW GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Step 1: Connect to MongoDB
    print_progress("Step 1/7: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    # Step 2: Access source database and collection
    print_progress("Step 2/7: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    # Get total document count
    total_certs = source_collection.estimated_document_count()
    print_success(f"Found {total_certs:,} total certificates")
    
    # Step 3: Access target database
    print_progress("Step 3/7: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['ca-stats']
    print_success("Target database and collection ready")
    
    # Step 4: Count total unique CAs
    print_progress("Step 4/7: Counting total unique CAs...")
    start_time = datetime.now()
    
    ca_pipeline = [
        {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
        {'$group': {'_id': '$parsed.issuer.organization'}},
        {'$count': 'total'}
    ]
    ca_result = list(source_collection.aggregate(
        ca_pipeline,
        hint='idx_issuer_org',
        allowDiskUse=True
    ))
    total_cas = ca_result[0]['total'] if ca_result else 0
    
    duration_cas = (datetime.now() - start_time).total_seconds()
    print_success(f"Found {total_cas:,} unique CAs in {duration_cas:.1f}s")
    
    # Step 5: Get top CA
    print_progress("Step 5/7: Finding top CA...")
    start_time = datetime.now()
    
    top_ca_pipeline = [
        {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
        {'$group': {'_id': '$parsed.issuer.organization', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}},
        {'$limit': 1}
    ]
    top_ca_result = list(source_collection.aggregate(
        top_ca_pipeline,
        hint='idx_issuer_org',
        allowDiskUse=True
    ))
    
    top_ca = None
    top_ca_count = 0
    top_ca_percentage = 0
    if top_ca_result:
        top_ca = top_ca_result[0]['_id'] or 'Unknown'
        top_ca_count = top_ca_result[0]['count']
        top_ca_percentage = round((top_ca_count / total_certs) * 100, 1) if total_certs > 0 else 0
    
    duration_top = (datetime.now() - start_time).total_seconds()
    print_success(f"Top CA: {top_ca} with {top_ca_count:,} certs ({top_ca_percentage}%) in {duration_top:.1f}s")
    
    # Step 6: Count self-signed certificates (uses index!)
    print_progress("Step 6/7: Counting self-signed certificates...")
    start_time = datetime.now()
    
    self_signed_count = source_collection.count_documents(
        {'parsed.signature.self_signed': True},
        hint='idx_self_signed'
    )
    
    duration_self = (datetime.now() - start_time).total_seconds()
    print_success(f"Found {self_signed_count:,} self-signed certs in {duration_self:.3f}s (indexed)")
    
    # Step 7: Count unique CA countries (uses index!)
    print_progress("Step 7/7: Counting unique CA countries...")
    start_time = datetime.now()
    
    country_pipeline = [
        {'$unwind': {'path': '$parsed.issuer.country', 'preserveNullAndEmptyArrays': True}},
        {'$group': {'_id': '$parsed.issuer.country'}},
        {'$match': {'_id': {'$ne': None}}},
        {'$count': 'total'}
    ]
    
    country_result = list(source_collection.aggregate(
        country_pipeline,
        hint='idx_issuer_country',
        allowDiskUse=True
    ))
    unique_countries = country_result[0]['total'] if country_result else 0
    
    duration_countries = (datetime.now() - start_time).total_seconds()
    print_success(f"Found {unique_countries} unique countries in {duration_countries:.1f}s (indexed)")
    
    # Prepare final stats document
    print()
    print_progress("Preparing final stats document...")
    
    total_duration = duration_cas + duration_top + duration_self + duration_countries
    
    stats_document = {
        '_id': 'ca_stats',
        'total_cas': total_cas,
        'total_certs': total_certs,
        'top_ca': {
            'name': top_ca,
            'count': top_ca_count,
            'percentage': top_ca_percentage
        },
        'self_signed_count': self_signed_count,
        'unique_countries': unique_countries,
        'computed_at': datetime.now(timezone.utc),
        'computation_duration_seconds': round(total_duration, 2)
    }
    
    # Store in target collection
    print_progress("Storing results in database...")
    
    try:
        # Replace the single document
        target_collection.replace_one(
            {'_id': 'ca_stats'},
            stats_document,
            upsert=True
        )
        print_success("Stored CA stats document")
        
    except Exception as e:
        print_error(f"Failed to store results: {str(e)}")
        sys.exit(1)
    
    # Final summary
    print()
    print_progress("=" * 70, BOLD)
    print_success("CA STATS COMPUTATION COMPLETED SUCCESSFULLY!")
    print_progress("=" * 70, BOLD)
    print()
    print_info("Results:")
    print(f"  • Total CAs: {BOLD}{total_cas:,}{RESET}")
    print(f"  • Total Certificates: {BOLD}{total_certs:,}{RESET}")
    print(f"  • Top CA: {BOLD}{top_ca}{RESET} ({top_ca_count:,} certs, {top_ca_percentage}%)")
    print(f"  • Self-signed: {BOLD}{self_signed_count:,}{RESET}")
    print(f"  • Unique Countries: {BOLD}{unique_countries}{RESET}")
    print(f"  • Total Computation Time: {BOLD}{total_duration:.2f}s{RESET}")
    print()
    print_info(f"Stored in: {BOLD}tranco-latest-8-lakh-results.ca-stats{RESET}")
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
