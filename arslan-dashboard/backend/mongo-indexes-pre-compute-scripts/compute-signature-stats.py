#!/usr/bin/env python
"""
Pre-compute Signature Stats for Signature & Hashes Page
========================================================

This script computes comprehensive signature and hash statistics by aggregating
data from 878K+ certificates and storing the results in a separate database.

Run this script:
    cd /Users/macbookair/Desktop/University/FYP/arslan-dashboard/backend
    source ~/.pyenv/versions/SSL-crawler/bin/activate
    python compute_signature_stats.py

Add to cron for automatic updates:
    0 */12 * * * cd /path/to/backend && /path/to/python compute_signature_stats.py

Performance:
    - Source: 878,849 certificates (tranco-latest-8-lakh)
    - Processing: ~240 seconds for full aggregation
    - Output: Single document with all stats
    - Result DB: tranco-latest-8-lakh-results.signature-stats
"""

import os
import sys
import django
from datetime import datetime, timezone

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ssl_dashboard.settings')
django.setup()

from certificates.db import MongoDBClient

def compute_signature_stats():
    """
    Compute comprehensive signature and hash statistics.
    Aggregates: algorithm distribution, hash distribution, key sizes, weak hash count, etc.
    """
    print("=" * 80)
    print("PRE-COMPUTING SIGNATURE STATS")
    print("=" * 80)
    print()
    
    # Connect to source and results databases
    source_db = MongoDBClient.get_db('tranco-latest-8-lakh')
    results_db = MongoDBClient.get_db('tranco-latest-8-lakh-results')
    
    source_collection = source_db['certificates']
    results_collection = results_db['signature-stats']
    
    # Get total count
    total = source_collection.count_documents({})
    print(f"📊 Total certificates: {total:,}")
    print()
    
    if total == 0:
        print("❌ No certificates found!")
        return
    
    start_time = datetime.now()
    
    # ============================================================================
    # PIPELINE 1: Signature Algorithm Distribution
    # ============================================================================
    print("⏳ Computing signature algorithm distribution...")
    algo_pipeline = [
        {'$group': {
            '_id': '$parsed.signature_algorithm.name',
            'count': {'$sum': 1}
        }},
        {'$match': {'_id': {'$ne': None}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    algo_results = list(source_collection.aggregate(algo_pipeline, allowDiskUse=True))
    
    algo_colors = {
        'SHA256-RSA': '#3b82f6',
        'SHA384-RSA': '#60a5fa', 
        'SHA512-RSA': '#1d4ed8',
        'SHA256-ECDSA': '#10b981',
        'SHA384-ECDSA': '#34d399',
        'SHA512-ECDSA': '#059669',
        'SHA1-RSA': '#f59e0b',
        'MD5-RSA': '#ef4444',
    }
    
    algorithm_distribution = []
    for item in algo_results:
        name = item['_id'] or 'Unknown'
        count = item['count']
        algorithm_distribution.append({
            'name': name,
            'count': count,
            'percentage': round((count / total) * 100, 2),
            'color': algo_colors.get(name, '#6b7280')
        })
    
    print(f"   ✓ Found {len(algorithm_distribution)} signature algorithms")
    
    # ============================================================================
    # PIPELINE 2: Hash Algorithm Distribution
    # ============================================================================
    print("⏳ Computing hash algorithm distribution...")
    hash_pipeline = [
        {'$project': {
            'sigAlgo': '$parsed.signature_algorithm.name'
        }},
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
                        {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD2', 'options': 'i'}}, 'then': 'MD2'},
                    ],
                    'default': '$sigAlgo'
                }
            }
        }},
        {'$match': {'hash': {'$ne': None, '$ne': ''}}},
        {'$group': {
            '_id': '$hash',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
    hash_results = list(source_collection.aggregate(hash_pipeline, allowDiskUse=True))
    
    hash_colors = {
        'SHA-512': '#1d4ed8',
        'SHA-384': '#3b82f6',
        'SHA-256': '#10b981',
        'SHA-224': '#34d399',
        'SHA-1': '#f59e0b',
        'MD5': '#ef4444',
        'MD2': '#dc2626',
    }
    
    hash_security = {
        'SHA-512': 'secure',
        'SHA-384': 'secure', 
        'SHA-256': 'secure',
        'SHA-224': 'secure',
        'SHA-1': 'deprecated',
        'MD5': 'critical',
        'MD2': 'critical',
    }
    
    hash_distribution = []
    weak_hash_count = 0
    compliant_count = 0
    
    for item in hash_results:
        name = item['_id']
        count = item['count']
        hash_distribution.append({
            'name': name,
            'count': count,
            'percentage': round((count / total) * 100, 2),
            'color': hash_colors.get(name, '#6b7280'),
            'security': hash_security.get(name, 'unknown')
        })
        
        if name in ['SHA-1', 'MD5']:
            weak_hash_count += count
        
        if name in ['SHA-256', 'SHA-384', 'SHA-512']:
            compliant_count += count
    
    print(f"   ✓ Found {len(hash_distribution)} hash algorithms")
    print(f"   ⚠️  Weak hash count: {weak_hash_count:,}")
    
    # ============================================================================
    # PIPELINE 3: Key Size Distribution
    # ============================================================================
    print("⏳ Computing key size distribution...")
    keysize_pipeline = [
        {'$project': {
            'algo': '$parsed.subject_key_info.key_algorithm.name',
            'rsaLen': '$parsed.subject_key_info.rsa_public_key.length',
            'ecLen': '$parsed.subject_key_info.ecdsa_public_key.length'
        }},
        {'$addFields': {
            'keySize': {'$ifNull': ['$rsaLen', '$ecLen']}
        }},
        {'$group': {
            '_id': {'algo': '$algo', 'size': '$keySize'},
            'count': {'$sum': 1}
        }},
        {'$match': {'_id.size': {'$ne': None}}},
        {'$sort': {'count': -1}},
        {'$limit': 10}
    ]
    keysize_results = list(source_collection.aggregate(keysize_pipeline, allowDiskUse=True))
    
    keysize_distribution = []
    key_score = 0
    for item in keysize_results:
        algo = item['_id'].get('algo', 'Unknown')
        size = item['_id'].get('size', 0)
        count = item['count']
        name = f"{algo} {size}" if size else algo
        percentage = round((count / total) * 100, 2)
        
        keysize_distribution.append({
            'name': name,
            'algorithm': algo,
            'size': size,
            'count': count,
            'percentage': percentage,
            'color': '#3b82f6' if algo == 'RSA' else '#10b981'
        })
        
        # Calculate key score
        pct = percentage / 100
        if size >= 4096:
            key_score += 100 * pct
        elif size >= 2048:
            key_score += 80 * pct
        elif size >= 1024:
            key_score += 40 * pct
        elif size >= 256:  # ECDSA
            key_score += 90 * pct
    
    print(f"   ✓ Found {len(keysize_distribution)} key sizes")
    
    # ============================================================================
    # Count self-signed certificates
    # ============================================================================
    print("⏳ Counting self-signed certificates...")
    self_signed_count = source_collection.count_documents(
        {'parsed.signature.self_signed': True}
    )
    print(f"   ✓ Self-signed count: {self_signed_count:,}")
    
    # ============================================================================
    # Calculate metrics
    # ============================================================================
    hash_compliance_rate = round((compliant_count / total) * 100, 1) if total > 0 else 0
    
    # Strength Score calculation
    hash_score = hash_compliance_rate
    algo_score = 85
    for item in algorithm_distribution:
        if 'ECDSA' in item.get('name', ''):
            algo_score += item.get('percentage', 0) * 0.15
    algo_score = min(100, algo_score)
    
    strength_score = int((key_score * 0.4) + (hash_score * 0.4) + (algo_score * 0.2))
    strength_score = max(0, min(100, strength_score))
    
    # ============================================================================
    # Get max encryption type
    # ============================================================================
    print("⏳ Finding max encryption type...")
    enc_type_pipeline = [
        {'$group': {
            '_id': '$parsed.subject_key_info.key_algorithm.name',
            'count': {'$sum': 1}
        }},
        {'$match': {'_id': {'$ne': None}}},
        {'$sort': {'count': -1}},
        {'$limit': 1}
    ]
    enc_type_result = list(source_collection.aggregate(enc_type_pipeline, allowDiskUse=True))
    
    max_encryption_type = None
    if enc_type_result:
        enc_name = enc_type_result[0]['_id']
        enc_count = enc_type_result[0]['count']
        max_encryption_type = {
            'name': enc_name,
            'count': enc_count,
            'percentage': round((enc_count / total) * 100, 2)
        }
    
    # ============================================================================
    # Store results
    # ============================================================================
    print()
    print("💾 Storing results in database...")
    
    result_doc = {
        'algorithmDistribution': algorithm_distribution,
        'hashDistribution': hash_distribution,
        'keySizeDistribution': keysize_distribution,
        'weakHashCount': weak_hash_count,
        'hashComplianceRate': hash_compliance_rate,
        'strengthScore': strength_score,
        'selfSignedCount': self_signed_count,
        'totalCertificates': total,
        'maxEncryptionType': max_encryption_type,
        'computedAt': datetime.now(timezone.utc).isoformat(),
        'sourceCollection': 'tranco-latest-8-lakh.certificates',
        'documentCount': total
    }
    
    # Replace existing document (only keep one)
    results_collection.delete_many({})
    results_collection.insert_one(result_doc)
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("✅ SIGNATURE STATS COMPUTATION COMPLETE")
    print("=" * 80)
    print(f"Total certificates:     {total:,}")
    print(f"Algorithms found:       {len(algorithm_distribution)}")
    print(f"Hash types found:       {len(hash_distribution)}")
    print(f"Key sizes found:        {len(keysize_distribution)}")
    print(f"Weak hash count:        {weak_hash_count:,}")
    print(f"Hash compliance:        {hash_compliance_rate}%")
    print(f"Strength score:         {strength_score}/100")
    print(f"Self-signed:            {self_signed_count:,}")
    print(f"Processing time:        {elapsed:.1f} seconds")
    print(f"Output collection:      tranco-latest-8-lakh-results.signature-stats")
    print()
    print("🔄 API will now read from pre-computed results (sub-millisecond response)")
    print("=" * 80)

if __name__ == '__main__':
    try:
        compute_signature_stats()
    except KeyboardInterrupt:
        print("\n\n⚠️  Computation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
