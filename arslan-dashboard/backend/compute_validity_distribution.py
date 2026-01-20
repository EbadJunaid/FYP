#!/usr/bin/env python
"""
Pre-compute Validity Distribution for Validity Analysis Page
=============================================================

This script computes the distribution of certificate validity periods by bucket
by aggregating data from 878K+ certificates.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_validity_distribution.py

Add to cron for automatic updates:
    0 */6 * * * cd /path/to/backend && /path/to/python compute_validity_distribution.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~200 seconds for full aggregation
    - Output: 4 bucket documents
    - Result DB: tranco-latest-8-lakh-results.validity-distribution
"""

import os
import sys
import django
from datetime import datetime, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_validity_distribution():
    """
    Compute distribution of certificate validity periods by bucket.
    Buckets: <90 days, 90-365 days, 1-2 years, >2 years
    """
    print("=" * 80)
    print("PRE-COMPUTING VALIDITY DISTRIBUTION")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['validity-distribution']
    
    start_time = datetime.now()
    
    # ============================================================================
    # PIPELINE: Bucket validity periods
    # ============================================================================
    print("⏳ Computing validity distribution by buckets...")
    
    pipeline = [
        {
            '$project': {
                'validFrom': '$parsed.validity.start',
                'validTo': '$parsed.validity.end',
            }
        },
        {
            '$addFields': {
                'validFromDate': {
                    '$dateFromString': {'dateString': '$validFrom', 'onError': None}
                },
                'validToDate': {
                    '$dateFromString': {'dateString': '$validTo', 'onError': None}
                }
            }
        },
        {
            '$addFields': {
                'durationDays': {
                    '$divide': [
                        {'$subtract': ['$validToDate', '$validFromDate']},
                        86400000
                    ]
                }
            }
        },
        {
            '$match': {'durationDays': {'$ne': None, '$gt': 0}}
        },
        {
            '$bucket': {
                'groupBy': '$durationDays',
                'boundaries': [0, 90, 365, 730, 100000],
                'default': 'Other',
                'output': {
                    'count': {'$sum': 1}
                }
            }
        }
    ]
    
    results = list(source_collection.aggregate(pipeline, allowDiskUse=True))
    
    print(f"   ✓ Found {len(results)} validity buckets")
    
    # ============================================================================
    # Process and format results
    # ============================================================================
    bucket_labels = {
        0: '< 90 Days',
        90: '90 Days - 1 Year',
        365: '1 - 2 Years',
        730: '> 2 Years'
    }
    
    bucket_colors = {
        0: '#3b82f6',    # Blue
        90: '#10b981',   # Green
        365: '#8b5cf6',  # Purple
        730: '#f59e0b'   # Orange
    }
    
    total = sum(r.get('count', 0) for r in results)
    
    distribution = []
    for r in results:
        bucket_id = r.get('_id')
        if bucket_id in bucket_labels:
            count = r.get('count', 0)
            percentage = round((count / total * 100), 1) if total > 0 else 0
            
            dist_doc = {
                'range': bucket_labels[bucket_id],
                'bucketId': bucket_id,
                'count': count,
                'percentage': percentage,
                'color': bucket_colors.get(bucket_id, '#6b7280'),
                'computedAt': datetime.now(timezone.utc).isoformat(),
                'sourceCollection': 'tranco-latest-8-lakh.certificates'
            }
            distribution.append(dist_doc)
            
            print(f"   • {bucket_labels[bucket_id]:20} {count:8,} ({percentage:5.1f}%)")
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    # Replace existing documents
    results_collection.delete_many({})
    if distribution:
        results_collection.insert_many(distribution)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ VALIDITY DISTRIBUTION COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Total certificates:     {total:,}")
    print(f"Buckets:                {len(distribution)}")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.validity-distribution")
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        compute_validity_distribution()
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
