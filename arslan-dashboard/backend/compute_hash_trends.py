#!/usr/bin/env python
"""
Pre-compute Hash Trends for Signature & Hashes Page
====================================================

This script computes hash algorithm adoption trends over time by aggregating
data from 878K+ certificates and storing the results in a separate database.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_hash_trends.py

Add to cron for automatic updates:
    0 */12 * * * cd /path/to/backend && /path/to/python compute_hash_trends.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~200 seconds for full aggregation
    - Output: ~36-48 documents (quarterly trends for 3 years)
    - Result DB: tranco-latest-8-lakh-results.hash-trends
"""

import os
import sys
import django
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_hash_trends(months: int = 36, granularity: str = 'quarterly'):
    """
    Compute hash algorithm adoption trends over time.
    
    Args:
        months: Number of months to look back (default 36 = 3 years)
        granularity: 'quarterly' or 'yearly'
    """
    print("=" * 80)
    print(f"PRE-COMPUTING HASH TRENDS ({granularity.upper()}, {months} months)")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['hash-trends']
    
    start_time = datetime.now()
    
    # Calculate date range
    now = datetime.now(timezone.utc)
    start_date = now - relativedelta(months=months)
    start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print(f"📅 Date range: {start_str} to present")
    print()
    
    # Build period grouping based on granularity
    if granularity == 'yearly':
        period_expr = {
            'year': {'$year': '$issuedDate'}
        }
    else:  # quarterly
        period_expr = {
            'year': {'$year': '$issuedDate'},
            'quarter': {'$ceil': {'$divide': [{'$month': '$issuedDate'}, 3]}}
        }
    
    # ============================================================================
    # Aggregate hash trends over time
    # ============================================================================
    print("⏳ Computing hash algorithm trends...")
    
    pipeline = [
        # Stage 1: Match documents in date range
        {'$match': {
            'parsed.validity.start': {'$gte': start_str}
        }},
        # Stage 2: Project only needed fields
        {'$project': {
            'sigAlgo': '$parsed.signature_algorithm.name',
            'issuedDate': {'$dateFromString': {
                'dateString': '$parsed.validity.start',
                'onError': None
            }}
        }},
        # Stage 3: Filter out null dates
        {'$match': {'issuedDate': {'$ne': None}}},
        # Stage 4: Extract hash algorithm
        {'$addFields': {
            'hash': {
                '$switch': {
                    'branches': [
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA512|SHA-512', 'options': 'i'}}, 'then': 'SHA-512'},
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA384|SHA-384', 'options': 'i'}}, 'then': 'SHA-384'},
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA256|SHA-256', 'options': 'i'}}, 'then': 'SHA-256'},
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA224|SHA-224', 'options': 'i'}}, 'then': 'SHA-224'},
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA1|SHA-1|withSHA1', 'options': 'i'}}, 'then': 'SHA-1'},
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD5', 'options': 'i'}}, 'then': 'MD5'},
                    ],
                    'default': 'Other'
                }
            },
            'period': period_expr
        }},
        # Stage 5: Group by period and hash
        {'$group': {
            '_id': {'period': '$period', 'hash': '$hash'},
            'count': {'$sum': 1}
        }},
        # Stage 6: Reshape for easier processing
        {'$group': {
            '_id': '$_id.period',
            'hashes': {'$push': {'hash': '$_id.hash', 'count': '$count'}},
            'total': {'$sum': '$count'}
        }},
        {'$sort': {'_id.year': 1, '_id.quarter': 1}}
    ]
    
    results = list(source_collection.aggregate(pipeline, allowDiskUse=True))
    
    print(f"   ✓ Found {len(results)} time periods")
    
    # ============================================================================
    # Process and format results
    # ============================================================================
    trends = []
    for item in results:
        period = item['_id']
        total = item['total']
        
        if granularity == 'yearly':
            period_label = str(period.get('year', 'Unknown'))
        else:
            year = period.get('year', 0)
            quarter = period.get('quarter', 0)
            period_label = f"Q{quarter} {year}"
        
        # Convert hash counts to percentages
        hash_pcts = {}
        for h in item.get('hashes', []):
            hash_name = h['hash']
            hash_pcts[hash_name] = round((h['count'] / total) * 100, 1) if total > 0 else 0
        
        trend_doc = {
            'period': period_label,
            'year': period.get('year', 0),
            'quarter': period.get('quarter', 0) if granularity == 'quarterly' else None,
            'total': total,
            'SHA-256': hash_pcts.get('SHA-256', 0),
            'SHA-384': hash_pcts.get('SHA-384', 0),
            'SHA-512': hash_pcts.get('SHA-512', 0),
            'SHA-1': hash_pcts.get('SHA-1', 0),
            'MD5': hash_pcts.get('MD5', 0),
            'Other': hash_pcts.get('Other', 0),
            'granularity': granularity,
            'months': months
        }
        trends.append(trend_doc)
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    # Add metadata
    for trend in trends:
        trend['computedAt'] = datetime.now(timezone.utc).isoformat()
        trend['sourceCollection'] = 'tranco-latest-8-lakh.certificates'
    
    # Replace existing documents for this granularity
    results_collection.delete_many({'granularity': granularity, 'months': months})
    if trends:
        results_collection.insert_many(trends)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ HASH TRENDS COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Time periods:           {len(trends)}")
    print(f"Granularity:            {granularity}")
    print(f"Date range:             {months} months")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.hash-trends")
    print()
    
    # Show sample trends
    if trends:
        print("Sample trends:")
        for trend in trends[:3]:
            print(f"   {trend['period']:12} - SHA-256: {trend['SHA-256']}%, SHA-1: {trend['SHA-1']}%, Total: {trend['total']:,}")
        if len(trends) > 3:
            print(f"   ... and {len(trends) - 3} more periods")
    
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        # Compute both quarterly and yearly trends
        compute_hash_trends(months=36, granularity='quarterly')
        print()
        compute_hash_trends(months=36, granularity='yearly')
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
