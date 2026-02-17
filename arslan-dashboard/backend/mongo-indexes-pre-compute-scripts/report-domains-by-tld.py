#!/usr/bin/env python3
"""
Report all domains grouped by TLD (Top-Level Domain)
Shows count and 5 examples for each TLD found in the database
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

def get_tld_from_domain(domain):
    """Extract TLD from domain name"""
    if not domain:
        return None
    
    parts = domain.lower().split('.')
    if len(parts) < 2:
        return None
    
    # Check for two-part TLDs first (e.g., co.uk)
    if len(parts) >= 3:
        two_part_tld = '.'.join(parts[-2:])
        # Common two-part TLDs
        if two_part_tld in ['co.uk', 'co.jp', 'co.in', 'co.za', 'com.au', 'com.br', 'com.cn']:
            return two_part_tld
    
    # Return single TLD
    return parts[-1]

def main():
    print(f"{BOLD}{BLUE}{'='*80}{RESET}")
    print(f"{BOLD}{GREEN}Domain Report by TLD (Top-Level Domain){RESET}")
    print(f"{BOLD}{BLUE}{'='*80}{RESET}\n")
    
    # MongoDB connection
    try:
        print(f"{YELLOW}Connecting to MongoDB...{RESET}")
        client = MongoClient(
            'localhost',
            27017,
            serverSelectionTimeoutMS=5000
        )
        
        # Test connection
        client.server_info()
        print(f"{GREEN}✓ Connected to MongoDB successfully{RESET}\n")
        
    except ServerSelectionTimeoutError:
        print(f"{RED}✗ Failed to connect to MongoDB{RESET}")
        print(f"{RED}  Please ensure MongoDB is running on localhost:27017{RESET}")
        sys.exit(1)
    except Exception as e:
        print(f"{RED}✗ Connection error: {e}{RESET}")
        sys.exit(1)
    
    # Database and collection
    db = client['tranco-latest-8-lakh']
    collection = db['certificates']
    
    print(f"{YELLOW}Analyzing domains by TLD...{RESET}\n")
    
    # Aggregation pipeline to group by TLD
    pipeline = [
        {
            '$match': {
                'domain': {'$exists': True, '$ne': None, '$ne': ''}
            }
        },
        {
            '$project': {
                'domain': 1,
                'domainParts': {'$split': ['$domain', '.']}
            }
        },
        {
            '$addFields': {
                'numParts': {'$size': '$domainParts'},
                'lastPart': {'$arrayElemAt': ['$domainParts', -1]},
                'secondLastPart': {'$arrayElemAt': ['$domainParts', -2]}
            }
        },
        {
            '$addFields': {
                'twoPartTld': {
                    '$concat': [
                        {'$ifNull': ['$secondLastPart', '']},
                        '.',
                        {'$ifNull': ['$lastPart', '']}
                    ]
                }
            }
        },
        {
            '$addFields': {
                'tld': {
                    '$cond': {
                        'if': {
                            '$and': [
                                {'$gte': ['$numParts', 3]},
                                {
                                    '$in': [
                                        '$twoPartTld',
                                        ['co.uk', 'co.jp', 'co.in', 'co.za', 'com.au', 'com.br', 'com.cn', 'ac.uk', 'gov.uk', 'org.uk']
                                    ]
                                }
                            ]
                        },
                        'then': '$twoPartTld',
                        'else': '$lastPart'
                    }
                }
            }
        },
        {
            '$match': {
                'tld': {'$exists': True, '$ne': None, '$ne': ''}
            }
        },
        {
            '$group': {
                '_id': '$tld',
                'count': {'$sum': 1},
                'examples': {'$push': '$domain'}
            }
        },
        {
            '$sort': {'count': -1}
        }
    ]
    
    print(f"{YELLOW}Running aggregation pipeline...{RESET}")
    results = list(collection.aggregate(pipeline, allowDiskUse=True))
    
    if not results:
        print(f"{RED}No domains found in database{RESET}")
        return
    
    print(f"{GREEN}✓ Analysis complete!{RESET}\n")
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    total_domains = sum(r['count'] for r in results)
    print(f"{BOLD}{GREEN}Total Domains Analyzed: {total_domains:,}{RESET}")
    print(f"{BOLD}{GREEN}Unique TLDs Found: {len(results):,}{RESET}\n")
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    # Print statistics for each TLD
    for rank, result in enumerate(results, 1):
        tld = result['_id']
        count = result['count']
        examples = result['examples'][:5]  # Get first 5 examples
        
        percentage = (count / total_domains) * 100
        
        # Color based on count
        if count > 10000:
            color = GREEN
        elif count > 1000:
            color = BLUE
        elif count > 100:
            color = YELLOW
        else:
            color = RESET
        
        print(f"{BOLD}{color}#{rank} TLD: .{tld}{RESET}")
        print(f"   Count: {count:,} domains ({percentage:.2f}%)")
        print(f"   Examples:")
        for i, example in enumerate(examples, 1):
            print(f"      {i}. {example}")
        print()
    
    print(f"{BOLD}{'='*80}{RESET}\n")
    
    # Summary statistics
    print(f"{BOLD}{BLUE}Summary Statistics:{RESET}")
    print(f"  Total TLDs: {len(results):,}")
    print(f"  Most common TLD: .{results[0]['_id']} ({results[0]['count']:,} domains)")
    if len(results) > 1:
        print(f"  Second most common: .{results[1]['_id']} ({results[1]['count']:,} domains)")
    if len(results) > 2:
        print(f"  Third most common: .{results[2]['_id']} ({results[2]['count']:,} domains)")
    
    # Count rare TLDs (< 10 domains)
    rare_tlds = sum(1 for r in results if r['count'] < 10)
    print(f"  Rare TLDs (< 10 domains): {rare_tlds}")
    
    print(f"\n{BOLD}{GREEN}Report generated successfully!{RESET}")
    print(f"{GREEN}Generated at: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}{RESET}")

if __name__ == '__main__':
    main()
