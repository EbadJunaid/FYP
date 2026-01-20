#!/usr/bin/env python
"""
Pre-compute Validity Stats for Validity Analysis Page
======================================================

This script computes comprehensive validity statistics by aggregating
data from 878K+ certificates and storing the results in a separate database.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_validity_stats.py

Add to cron for automatic updates:
    0 */6 * * * cd /path/to/backend && /path/to/python compute_validity_stats.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~180 seconds for full aggregation
    - Output: Single document with all stats
    - Result DB: tranco-latest-8-lakh-results.validity-stats
"""

import os
import sys
import django
from datetime import datetime, timezone, timedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_validity_stats():
    """
    Compute comprehensive validity statistics.
    Includes: avg validity, expiring counts, compliance rate, min/max validity.
    """
    print("=" * 80)
    print("PRE-COMPUTING VALIDITY STATS")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['validity-stats']
    
    start_time = datetime.now()
    
    now = datetime.now(timezone.utc)
    now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    plus_30 = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
    plus_60 = (now + timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
    plus_90 = (now + timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print(f"📅 Current time: {now_iso}")
    print()
    
    # ============================================================================
    # PIPELINE: Validity duration statistics
    # ============================================================================
    print("⏳ Computing validity duration statistics...")
    
    pipeline = [
        {
            '$match': {
                'parsed.validity.length': {'$exists': True, '$gt': 0}
            }
        },
        {
            '$project': {
                'lengthSeconds': '$parsed.validity.length',
                'durationDays': {'$divide': ['$parsed.validity.length', 86400]}
            }
        },
        {
            '$group': {
                '_id': None,
                'avgDuration': {'$avg': '$durationDays'},
                'minDuration': {'$min': '$durationDays'},
                'maxDuration': {'$max': '$durationDays'},
                'total': {'$sum': 1},
                'compliantCount': {
                    '$sum': {
                        '$cond': [
                            {'$lte': ['$durationDays', 398]},
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]
    
    result = list(source_collection.aggregate(pipeline, allowDiskUse=True))
    stats = result[0] if result else {}
    
    total = stats.get('total', 0)
    compliant = stats.get('compliantCount', 0)
    
    print(f"   ✓ Total certificates: {total:,}")
    print(f"   ✓ Avg validity: {round(stats.get('avgDuration', 0))} days")
    print(f"   ✓ Min validity: {round(stats.get('minDuration', 0))} days")
    print(f"   ✓ Max validity: {round(stats.get('maxDuration', 0))} days")
    print(f"   ✓ Compliant (≤398d): {compliant:,} ({round(compliant/total*100, 1) if total > 0 else 0}%)")
    
    # ============================================================================
    # COUNT: Expiring certificates
    # ============================================================================
    print()
    print("⏳ Counting expiring certificates...")
    
    # Using index on validity.end for fast counting
    expiring_30 = source_collection.count_documents(
        {'parsed.validity.end': {'$gt': now_iso, '$lte': plus_30}},
        hint='idx_validity_end'
    )
    expiring_60 = source_collection.count_documents(
        {'parsed.validity.end': {'$gt': now_iso, '$lte': plus_60}},
        hint='idx_validity_end'
    )
    expiring_90 = source_collection.count_documents(
        {'parsed.validity.end': {'$gt': now_iso, '$lte': plus_90}},
        hint='idx_validity_end'
    )
    
    print(f"   ✓ Expiring in 30 days: {expiring_30:,}")
    print(f"   ✓ Expiring in 60 days: {expiring_60:,}")
    print(f"   ✓ Expiring in 90 days: {expiring_90:,}")
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    result_doc = {
        'averageValidityDays': round(stats.get('avgDuration', 0) or 0),
        'shortestValidityDays': round(stats.get('minDuration', 0) or 0),
        'longestValidityDays': round(stats.get('maxDuration', 0) or 0),
        'expiring30Days': expiring_30,
        'expiring60Days': expiring_60,
        'expiring90Days': expiring_90,
        'complianceRate': round((compliant / total * 100), 1) if total > 0 else 0,
        'totalCertificates': total,
        'computedAt': datetime.now(timezone.utc).isoformat(),
        'sourceCollection': 'tranco-latest-8-lakh.certificates',
        'referenceDate': now_iso
    }
    
    # Replace existing document (only keep one)
    results_collection.delete_many({})
    results_collection.insert_one(result_doc)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ VALIDITY STATS COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Total certificates:     {total:,}")
    print(f"Avg validity:           {result_doc['averageValidityDays']} days")
    print(f"Compliance rate:        {result_doc['complianceRate']}%")
    print(f"Expiring (30d):         {expiring_30:,}")
    print(f"Expiring (60d):         {expiring_60:,}")
    print(f"Expiring (90d):         {expiring_90:,}")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.validity-stats")
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        compute_validity_stats()
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
