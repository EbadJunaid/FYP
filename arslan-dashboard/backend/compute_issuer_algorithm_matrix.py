#!/usr/bin/env python
"""
Pre-compute Issuer Algorithm Matrix for Signature & Hashes Page
================================================================

This script computes the issuer × algorithm matrix by aggregating data from
878K+ certificates and storing the results in a separate database.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_issuer_algorithm_matrix.py

Add to cron for automatic updates:
    0 */12 * * * cd /path/to/backend && /path/to/python compute_issuer_algorithm_matrix.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~180 seconds for full aggregation
    - Output: ~50 issuer × algorithm combinations
    - Result DB: tranco-latest-8-lakh-results.issuer-algorithm-matrix
"""

import os
import sys
import django
from datetime import datetime, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_issuer_algorithm_matrix(limit: int = 50):
    """
    Compute matrix of issuer × algorithm combinations with counts.
    
    Args:
        limit: Maximum number of combinations to store (default 50)
    """
    print("=" * 80)
    print(f"PRE-COMPUTING ISSUER ALGORITHM MATRIX (Top {limit})")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['issuer-algorithm-matrix']
    
    # Get total count
    total = source_collection.count_documents({})
    print(f"📊 Total certificates: {total:,}")
    print()
    
    start_time = datetime.now()
    
    # ============================================================================
    # Aggregate issuer × algorithm matrix
    # ============================================================================
    print("⏳ Computing issuer × algorithm combinations...")
    
    pipeline = [
        # Stage 1: Project needed fields only
        {'$project': {
            'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
            'algo': '$parsed.subject_key_info.key_algorithm.name',
            'rsaLen': '$parsed.subject_key_info.rsa_public_key.length',
            'ecLen': '$parsed.subject_key_info.ecdsa_public_key.length'
        }},
        # Stage 2: Compute key size
        {'$addFields': {
            'keySize': {'$ifNull': ['$rsaLen', '$ecLen']}
        }},
        # Stage 3: Filter out nulls
        {'$match': {
            'issuer': {'$ne': None},
            'algo': {'$ne': None}
        }},
        # Stage 4: Group by issuer + algo + keySize
        {'$group': {
            '_id': {
                'issuer': '$issuer',
                'algo': '$algo',
                'keySize': '$keySize'
            },
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
        {'$limit': limit}
    ]
    
    results = list(source_collection.aggregate(pipeline, allowDiskUse=True))
    
    print(f"   ✓ Found {len(results)} issuer × algorithm combinations")
    
    # ============================================================================
    # Process and format results
    # ============================================================================
    matrix = []
    top_issuers = set()
    
    for item in results:
        issuer = item['_id'].get('issuer', 'Unknown')
        algo = item['_id'].get('algo', 'Unknown')
        key_size = item['_id'].get('keySize', 0)
        count = item['count']
        
        # Format algorithm string like "RSA-2048"
        algo_str = f"{algo}-{key_size}" if key_size else algo
        
        matrix_doc = {
            'issuer': issuer,
            'algorithm': algo_str,
            'algorithmType': algo,
            'keySize': key_size,
            'count': count,
            'percentage': round((count / total) * 100, 2) if total > 0 else 0,
            'computedAt': datetime.now(timezone.utc).isoformat(),
            'sourceCollection': 'tranco-latest-8-lakh.certificates'
        }
        matrix.append(matrix_doc)
        top_issuers.add(issuer)
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    # Replace existing documents
    results_collection.delete_many({})
    if matrix:
        results_collection.insert_many(matrix)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ ISSUER ALGORITHM MATRIX COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Total combinations:     {len(matrix)}")
    print(f"Unique issuers:         {len(top_issuers)}")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.issuer-algorithm-matrix")
    print()
    
    # Show top combinations
    if matrix:
        print("Top issuer × algorithm combinations:")
        for i, item in enumerate(matrix[:10], 1):
            print(f"   {i:2}. {item['issuer']:30} × {item['algorithm']:15} = {item['count']:,}")
        if len(matrix) > 10:
            print(f"   ... and {len(matrix) - 10} more combinations")
    
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        compute_issuer_algorithm_matrix(limit=50)
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
