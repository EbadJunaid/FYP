#!/usr/bin/env python3
"""
Pre-compute SAN Statistics - stores a single document with all SAN stats
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
    print_progress("SAN STATISTICS MATERIALIZED VIEW GENERATOR", BOLD)
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
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    # Step 3: Access target database
    print_progress("Step 3/4: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    target_collection = target_db['san-stats']
    print_success("Target database and collection ready")
    
    # Step 4: Compute SAN statistics
    print_progress("Step 4/4: Computing SAN statistics...")
    print_info("This will take 2-3 minutes to scan all documents...")
    print()
    
    start_time = datetime.now()
    
    pipeline = [
        {
            '$project': {
                'names': {
                    '$filter': {
                        'input': {'$ifNull': ['$parsed.extensions.subject_alt_name.dns_names', []]},
                        'as': 'n',
                        'cond': {'$ne': ['$$n', None]}
                    }
                }
            }
        },
        {
            '$addFields': {
                'sanCount': {'$size': '$names'},
                'hasWildcard': {
                    '$gt': [
                        {'$size': {
                            '$filter': {
                                'input': '$names',
                                'as': 'name',
                                'cond': {
                                    '$and': [
                                        {'$eq': [{'$type': '$$name'}, 'string']},
                                        {'$regexMatch': {'input': '$$name', 'regex': '^\\*\\.'}}
                                    ]
                                }
                            }
                        }},
                        0
                    ]
                }
            }
        },
        {
            '$addFields': {
                'isMultiDomain': {'$gte': ['$sanCount', 5]}
            }
        },
        {
            '$group': {
                '_id': None,
                'totalSans': {'$sum': '$sanCount'},
                'totalCerts': {'$sum': 1},
                'wildcardCerts': {'$sum': {'$cond': ['$hasWildcard', 1, 0]}},
                'multiDomainCerts': {'$sum': {'$cond': ['$isMultiDomain', 1, 0]}}
            }
        }
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
        
        if not results:
            print_error("No results computed")
            sys.exit(1)
        
        data = results[0]
        total_certs = data.get('totalCerts', 1) or 1
        
        stats_document = {
            '_id': 'san_stats',
            'total_sans': data.get('totalSans', 0),
            'avg_sans_per_cert': round(data.get('totalSans', 0) / total_certs, 2),
            'wildcard_certs': data.get('wildcardCerts', 0),
            'multi_domain_certs': data.get('multiDomainCerts', 0),
            'total_certs': total_certs,
            'computed_at': datetime.now(timezone.utc),
            'computation_duration_seconds': round(duration, 2)
        }
        
        print()
        print_info("Computed Statistics:")
        print(f"  • Total SANs: {BOLD}{stats_document['total_sans']:,}{RESET}")
        print(f"  • Avg SANs/Cert: {BOLD}{stats_document['avg_sans_per_cert']}{RESET}")
        print(f"  • Wildcard Certs: {BOLD}{stats_document['wildcard_certs']:,}{RESET}")
        print(f"  • Multi-domain Certs (5+ SANs): {BOLD}{stats_document['multi_domain_certs']:,}{RESET}")
        print(f"  • Total Certificates: {BOLD}{stats_document['total_certs']:,}{RESET}")
        print()
        
        # Store in target collection
        print_progress("Storing results in database...")
        
        target_collection.replace_one(
            {'_id': 'san_stats'},
            stats_document,
            upsert=True
        )
        print_success("Stored SAN stats document")
        
    except Exception as e:
        print_error(f"Computation failed: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Final summary
    print()
    print_progress("=" * 70, BOLD)
    print_success("SAN STATISTICS COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Stored in: {BOLD}tranco-latest-8-lakh-results.san-stats{RESET}")
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
