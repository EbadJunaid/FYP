#!/usr/bin/env python3
"""
Pre-compute Geographic Distribution and store in materialized view collection
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

# TLD to Country mapping
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
    print_progress("GEOGRAPHIC DISTRIBUTION MATERIALIZED VIEW GENERATOR", BOLD)
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
    target_collection = target_db['geographic-distribution']
    print_success("Target database and collection ready")
    
    # Step 4: Run aggregation pipeline to extract TLDs
    print_progress("Step 4/6: Extracting TLDs and grouping...")
    print_info("This will take 2-3 minutes to scan all documents...")
    print()
    
    pipeline = [
        # Match documents with domain field
        {'$match': {'domain': {'$exists': True, '$ne': None, '$ne': ''}}},
        # Split domain by '.' and get last element (TLD)
        {'$project': {
            'domain_parts': {'$split': ['$domain', '.']},
        }},
        {'$project': {
            'tld': {'$arrayElemAt': ['$domain_parts', -1]}
        }},
        # Filter out null/empty TLDs
        {'$match': {'tld': {'$exists': True, '$ne': None, '$ne': ''}}},
        # Group by TLD and count
        {'$group': {
            '_id': '$tld',
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
            allowDiskUse=True
        ))
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print_success(f"Aggregation completed in {duration:.1f} seconds")
        print_success(f"Found {len(results)} unique TLDs")
        print()
        
    except Exception as e:
        print_error(f"Aggregation failed: {str(e)}")
        sys.exit(1)
    
    # Step 5: Map TLDs to countries and aggregate
    print_progress("Step 5/6: Mapping TLDs to countries...")
    
    if not results:
        print_error("No results to store")
        sys.exit(1)
    
    # Map TLDs to countries
    country_counts = {}
    unknown_tlds = []
    
    for result in results:
        tld = result['_id'].lower() if result['_id'] else 'unknown'
        count = result['count']
        
        # Get country from TLD
        country = get_tld_country(f'example.{tld}')
        
        if country == 'Unknown':
            unknown_tlds.append((tld, count))
        
        # Aggregate counts by country
        if country in country_counts:
            country_counts[country] += count
        else:
            country_counts[country] = count
    
    # Sort countries by count
    sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)
    
    total_with_domain = sum(r['count'] for r in results)
    max_count = sorted_countries[0][1] if sorted_countries else 1
    
    print_success(f"Mapped {len(sorted_countries)} countries")
    
    # Show top TLDs that couldn't be mapped
    if unknown_tlds:
        print_info(f"Found {len(unknown_tlds)} unknown TLDs (showing top 10):")
        for tld, count in sorted(unknown_tlds, key=lambda x: x[1], reverse=True)[:10]:
            print(f"      .{tld}: {count:,}")
        print()
    
    # Color palette for visualization
    colors = [
        '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
        '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
        '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#d946ef',
        '#eab308', '#6b7280'
    ]
    
    # Transform results into API-ready format
    geo_records = []
    for i, (country, count) in enumerate(sorted_countries):
        geo_record = {
            'geo_id': f'geo-{i}',
            'country': country,
            'count': count,
            'max_count': max_count,
            'percentage': round((count / total_with_domain) * 100, 1),
            'color': colors[i % len(colors)],
            'rank': i + 1,
            'computed_at': datetime.now(timezone.utc),
            'total_certificates': total_with_domain
        }
        geo_records.append(geo_record)
    
    print_success(f"Prepared {len(geo_records)} country records")
    
    # Display top 10 countries
    print()
    print_info("Top 10 Countries:")
    print()
    for record in geo_records[:10]:
        bar_length = int((record['count'] / max_count) * 40)
        bar = '█' * bar_length
        print(f"  {record['rank']:2}. {record['country'][:40]:<40} {bar} {record['count']:>7,} ({record['percentage']:>5.1f}%)")
    print()
    
    # Step 6: Store in target collection
    print_progress("Step 6/6: Storing results in database...")
    
    try:
        # Clear existing data
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        # Insert new data
        if geo_records:
            result = target_collection.insert_many(geo_records)
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
            'total_countries': len(geo_records),
            'total_certificates': total_with_domain,
            'total_tlds': len(results),
            'unknown_tlds': len(unknown_tlds),
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
    print_success("GEOGRAPHIC DISTRIBUTION COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Database: {BOLD}tranco-latest-8-lakh-results{RESET}")
    print_info(f"Collection: {BOLD}geographic-distribution{RESET}")
    print_info(f"Total Countries: {BOLD}{len(geo_records):,}{RESET}")
    print_info(f"Total TLDs: {BOLD}{len(results):,}{RESET}")
    print_info(f"Computation Time: {BOLD}{duration:.1f}s{RESET}")
    print()
    print_info("Next steps:")
    print(f"  1. API will now read from this collection for fast response")
    print(f"  2. Set up a cron job to run this script every 6-12 hours")
    print(f"  3. Example: 0 */12 * * * /path/to/python compute_geographic_distribution.py")
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
