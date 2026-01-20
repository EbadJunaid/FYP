#!/usr/bin/env python
"""
Pre-compute Issuance Timeline for Validity Analysis Page
=========================================================

This script computes certificate issuance and expiration timeline by month
by aggregating data from 878K+ certificates.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_issuance_timeline.py

Add to cron for automatic updates:
    0 */6 * * * cd /path/to/backend && /path/to/python compute_issuance_timeline.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~250 seconds for full aggregation
    - Output: ~12-36 month documents
    - Result DB: tranco-latest-8-lakh-results.issuance-timeline
"""

import os
import sys
import django
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_issuance_timeline(months: int = 12):
    """
    Compute certificate issuance and expiration timeline by month.
    
    Args:
        months: Number of months to compute (default 12)
    """
    print("=" * 80)
    print(f"PRE-COMPUTING ISSUANCE TIMELINE ({months} months)")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['issuance-timeline']
    
    start_time = datetime.now()
    
    now = datetime.now(timezone.utc)
    
    # Calculate date range: last N months from the start of current month
    end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)
    start_date = now.replace(day=1) - relativedelta(months=months-1)
    
    start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    print(f"📅 Date range: {start_str} to {end_str}")
    print()
    
    # ============================================================================
    # PIPELINE 1: Issued certificates by month
    # ============================================================================
    print("⏳ Computing issued certificates by month...")
    
    issued_pipeline = [
        {
            '$match': {
                'parsed.validity.start': {
                    '$gte': start_str,
                    '$lte': end_str
                }
            }
        },
        {
            '$project': {
                'validFrom': '$parsed.validity.start'
            }
        },
        {
            '$addFields': {
                'validFromDate': {
                    '$dateFromString': {'dateString': '$validFrom', 'onError': None}
                }
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$validFromDate'},
                    'month': {'$month': '$validFromDate'}
                },
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'_id.year': 1, '_id.month': 1}}
    ]
    
    issued_results = list(source_collection.aggregate(issued_pipeline, allowDiskUse=True))
    
    print(f"   ✓ Found {len(issued_results)} months with issuances")
    
    # ============================================================================
    # PIPELINE 2: Expiring certificates by month
    # ============================================================================
    print("⏳ Computing expiring certificates by month...")
    
    expiring_pipeline = [
        {
            '$match': {
                'parsed.validity.end': {
                    '$gte': start_str,
                    '$lte': end_str
                }
            }
        },
        {
            '$project': {
                'validTo': '$parsed.validity.end'
            }
        },
        {
            '$addFields': {
                'validToDate': {
                    '$dateFromString': {'dateString': '$validTo', 'onError': None}
                }
            }
        },
        {
            '$group': {
                '_id': {
                    'year': {'$year': '$validToDate'},
                    'month': {'$month': '$validToDate'}
                },
                'count': {'$sum': 1}
            }
        },
        {'$sort': {'_id.year': 1, '_id.month': 1}}
    ]
    
    expiring_results = list(source_collection.aggregate(expiring_pipeline, allowDiskUse=True))
    
    print(f"   ✓ Found {len(expiring_results)} months with expirations")
    
    # ============================================================================
    # Process and format results
    # ============================================================================
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    # Create lookup dicts
    issued_lookup = {
        f"{r['_id']['year']}-{r['_id']['month']}": r['count']
        for r in issued_results
    }
    expiring_lookup = {
        f"{r['_id']['year']}-{r['_id']['month']}": r['count']
        for r in expiring_results
    }
    
    # Generate timeline data
    timeline = []
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    
    while current <= end_month:
        key = f"{current.year}-{current.month}"
        month_label = f"{month_names[current.month - 1]} '{str(current.year)[2:]}"
        
        issued_count = issued_lookup.get(key, 0)
        expiring_count = expiring_lookup.get(key, 0)
        
        timeline_doc = {
            'month': month_label,
            'year': current.year,
            'monthNum': current.month,
            'issued': issued_count,
            'expiring': expiring_count,
            'months': months,
            'computedAt': datetime.now(timezone.utc).isoformat(),
            'sourceCollection': 'tranco-latest-8-lakh.certificates'
        }
        timeline.append(timeline_doc)
        
        # Move to next month
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    # Replace existing documents for this month count
    results_collection.delete_many({'months': months})
    if timeline:
        results_collection.insert_many(timeline)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ ISSUANCE TIMELINE COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Time periods:           {len(timeline)} months")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.issuance-timeline")
    print()
    
    # Show sample timeline
    if timeline:
        print("Sample timeline:")
        for t in timeline[:5]:
            print(f"   {t['month']:12} - Issued: {t['issued']:5,}, Expiring: {t['expiring']:5,}")
        if len(timeline) > 5:
            print(f"   ... and {len(timeline) - 5} more months")
    
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        # Compute for default 12 months
        compute_issuance_timeline(months=12)
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
