#!/usr/bin/env python3
"""
Report all domains that fall in the "Unknown" category during geographic distribution
Based on compute-geographic-distribution.py but focused on reporting unknowns
This script extracts TLDs, maps them to countries, and prints all domains with unknown TLDs
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

# TLD to Country mapping (same as original script)
TLD_TO_COUNTRY = {
    'pk': 'Pakistan',
    'us': 'United States',
    'com': 'United States',
    'uk': 'United Kingdom',
    'co.uk': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'jp': 'Japan',
    'ca': 'Canada',
    'au': 'Australia',
    'nl': 'Netherlands',
    'in': 'India',
    'cn': 'China',
    'br': 'Brazil',
    'kr': 'South Korea',
    'sg': 'Singapore',
    'ie': 'Ireland',
    'se': 'Sweden',
    'ch': 'Switzerland',
    'it': 'Italy',
    'es': 'Spain',
    'ru': 'Russia',
    'mx': 'Mexico',
    'za': 'South Africa',
    'nz': 'New Zealand',
    'org': 'International',
    'net': 'International',
    'io': 'International',
    'dev': 'International',
}

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

def get_tld_country(domain: str) -> str:
    """Derive country from domain TLD"""
    if not domain:
        return 'Unknown'
    parts = domain.lower().split('.')
    if len(parts) >= 2:
        # Check for two-part TLDs first (e.g., co.uk)
        two_part_tld = '.'.join(parts[-2:])
        if two_part_tld in TLD_TO_COUNTRY:
            return TLD_TO_COUNTRY[two_part_tld]
        # Check single TLD
        tld = parts[-1]
        return TLD_TO_COUNTRY.get(tld, 'Unknown')
    return 'Unknown'

def main():
    """Main execution function"""
    
    print_progress("=" * 70, BOLD)
    print_progress("UNKNOWN DOMAINS REPORTER", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Step 1: Connect to MongoDB
    print_progress("Step 1/4: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    # Step 2: Access source database and collection
    print_progress("Step 2/4: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    # Get total document count
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    # Step 3: Run aggregation pipeline to extract TLDs with domains
    print_progress("Step 3/4: Extracting TLDs and domains...")
    print_info("This will take 2-3 minutes to scan all documents...")
    print()
    
    pipeline = [
        # Match documents with domain field
        {'$match': {'domain': {'$exists': True, '$ne': None, '$ne': ''}}},
        # Split domain by '.' and get last element (TLD)
        {'$project': {
            'domain': 1,
            'domain_parts': {'$split': ['$domain', '.']},
        }},
        {'$project': {
            'domain': 1,
            'tld': {'$arrayElemAt': ['$domain_parts', -1]}
        }},
        # Filter out null/empty TLDs
        {'$match': {'tld': {'$exists': True, '$ne': None, '$ne': ''}}},
    ]
    
    try:
        # Run aggregation with progress tracking
        start_time = datetime.now()
        print_info(f"Aggregation started at: {start_time.strftime('%H:%M:%S')}")
        
        results = list(source_collection.aggregate(
            pipeline,
            allowDiskUse=True
        ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        print_success(f"Found {len(results)} certificates with domains")
        print()
        
    except Exception as e:
        print_error(f"Aggregation failed: {str(e)}")
        sys.exit(1)
    
    # Step 4: Identify and report unknown domains
    print_progress("Step 4/4: Identifying unknown domains...")
    
    if not results:
        print_error("No results to process")
        sys.exit(1)
    
    # Collect unknown domains with their TLDs
    unknown_domains = []
    tld_counts = {}
    
    for result in results:
        domain = result.get('domain', '')
        tld = result.get('tld', '').lower() if result.get('tld') else 'unknown'
        
        # Get country from TLD
        country = get_tld_country(domain)
        
        if country == 'Unknown':
            unknown_domains.append((domain, tld))
            tld_counts[tld] = tld_counts.get(tld, 0) + 1
    
    # Sort TLDs by count (most common first)
    sorted_tlds = sorted(tld_counts.items(), key=lambda x: x[1], reverse=True)
    
    print_success(f"Found {len(unknown_domains)} domains with unknown country")
    print_info(f"These domains have {len(sorted_tlds)} unique TLDs")
    print()
    
    # Display TLD summary
    print_progress("=" * 70, BOLD)
    print_progress("UNKNOWN TLDs SUMMARY (Top 50)", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    print(f"{'TLD':<15} {'Count':>10} {'Bar':>35}")
    print("-" * 70)
    
    max_count = sorted_tlds[0][1] if sorted_tlds else 1
    for tld, count in sorted_tlds[:50]:
        bar_length = int((count / max_count) * 30)
        bar = '█' * bar_length
        print(f"{tld:<15} {count:>10,} {bar}")
    
    print()
    print()
    
    # Display all unknown domains
    print_progress("=" * 70, BOLD)
    print_progress(f"ALL UNKNOWN DOMAINS ({len(unknown_domains)} total)", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    print(f"{'Domain':<50} {'TLD':<15}")
    print("-" * 70)
    
    for domain, tld in sorted(unknown_domains, key=lambda x: (x[1], x[0])):
        print(f"{domain:<50} .{tld:<15}")
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("REPORT COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Total domains with unknown country: {len(unknown_domains)}")
    print_info(f"Total unique unknown TLDs: {len(sorted_tlds)}")
    print_info(f"Report generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

if __name__ == '__main__':
    main()
