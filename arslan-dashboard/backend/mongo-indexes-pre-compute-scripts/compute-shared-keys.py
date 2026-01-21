#!/usr/bin/env python3
"""
Pre-compute Shared Keys Analytics - stores all shared key data
This script should be run periodically (e.g., every 6-12 hours via cron job)
"""

import sys
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# Color codes
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_progress(message, color=BLUE):
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}{BOLD}[{timestamp}]{RESET} {color}{message}{RESET}")

def print_success(message):
    print_progress(f"✓ {message}", GREEN)

def print_error(message):
    print_progress(f"✗ {message}", RED)

def print_info(message):
    print_progress(f"ℹ {message}", YELLOW)

def main():
    print_progress("=" * 70, BOLD)
    print_progress("SHARED KEYS ANALYTICS MATERIALIZED VIEW GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Connect to MongoDB
    print_progress("Step 1/5: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    print_progress("Step 2/5: Accessing source database...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    print_progress("Step 3/5: Setting up target database...")
    target_db = client['tranco-latest-8-lakh-results']
    
    # Clear old collections completely
    print_info("Clearing old collections...")
    for coll_name in ['shared-keys-groups', 'shared-keys-stats', 'shared-keys-distribution', 
                      'shared-keys-by-issuer', 'shared-keys-timeline', 'shared-keys-heatmap']:
        try:
            target_db[coll_name].drop()
        except Exception as e:
            pass  # Ignore if collection doesn't exist
    
    print_success("Target collections ready")
    
    print_progress("Step 4/5: Computing shared key groups...")
    print_info("This will take 3-5 minutes to analyze all certificates...")
    print()
    
    start_time = datetime.now()
    
    # Step A: Find all truly shared keys (keys with 2+ distinct cert fingerprints)
    print_info("Step 4A: Identifying truly shared public keys...")
    shared_keys_pipeline = [
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
            'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
        }},
        {'$group': {
            '_id': '$parsed.subject_key_info.fingerprint_sha256',
            'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'},
            'cert_count': {'$sum': 1}
        }},
        {'$addFields': {
            'distinct_certs': {'$size': '$cert_fingerprints'}
        }},
        {'$match': {'distinct_certs': {'$gt': 1}}}
    ]
    
    shared_key_groups = list(source_collection.aggregate(shared_keys_pipeline, allowDiskUse=True))
    print_success(f"Found {len(shared_key_groups):,} truly shared key groups")
    
    if not shared_key_groups:
        print_error("No shared keys found. Exiting.")
        sys.exit(0)
    
    # Store shared key groups for fast lookup
    print_info("Storing shared key groups...")
    groups_collection = target_db['shared-keys-groups']
    
    shared_fingerprints = []
    groups_docs = []
    for i, group in enumerate(shared_key_groups):
        shared_fingerprints.append(group['_id'])
        groups_docs.append({
            '_id': group['_id'],
            'distinct_certs': group['distinct_certs'],
            'cert_count': group['cert_count'],
            'computed_at': datetime.now(timezone.utc)
        })
    
    if groups_docs:
        groups_collection.insert_many(groups_docs)
        groups_collection.create_index('distinct_certs')
        print_success(f"Stored {len(groups_docs):,} shared key groups")
    
    # Step B: Compute overall stats
    print_info("Step 4B: Computing overall statistics...")
    
    # Count unique keys
    unique_keys_result = list(source_collection.aggregate([
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None}
        }},
        {'$group': {'_id': '$parsed.subject_key_info.fingerprint_sha256'}},
        {'$count': 'total'}
    ], allowDiskUse=True))
    
    unique_keys = unique_keys_result[0]['total'] if unique_keys_result else 0
    
    # Count certificates at risk
    total_certs_at_risk = sum(g['cert_count'] for g in shared_key_groups)
    
    # Find most affected domain
    top_domain_pipeline = [
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
        }},
        {'$group': {
            '_id': {'$arrayElemAt': ['$parsed.names', 0]},
            'key_fingerprint': {'$first': '$parsed.subject_key_info.fingerprint_sha256'},
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
        {'$limit': 1}
    ]
    
    top_domain_result = list(source_collection.aggregate(top_domain_pipeline, allowDiskUse=True))
    top_domain = top_domain_result[0] if top_domain_result else {'_id': 'N/A', 'count': 0}
    
    stats_doc = {
        '_id': 'shared_keys_stats',
        'unique_keys': unique_keys,
        'shared_key_groups': len(shared_key_groups),
        'certificates_at_risk': total_certs_at_risk,
        'most_affected_domain': {
            'name': top_domain.get('_id', 'N/A'),
            'count': top_domain.get('count', 0)
        },
        'computed_at': datetime.now(timezone.utc)
    }
    
    target_db['shared-keys-stats'].insert_one(stats_doc)
    print_success("Stored statistics")
    print_info(f"  • Unique Keys: {unique_keys:,}")
    print_info(f"  • Shared Key Groups: {len(shared_key_groups):,}")
    print_info(f"  • Certificates at Risk: {total_certs_at_risk:,}")
    print()
    
    # Step C: Compute distribution
    print_info("Step 4C: Computing distribution...")
    
    distribution = [
        {'bucket': '2', 'count': 0},
        {'bucket': '3-5', 'count': 0},
        {'bucket': '6-10', 'count': 0},
        {'bucket': '10+', 'count': 0}
    ]
    
    for group in shared_key_groups:
        dc = group['distinct_certs']
        if dc == 2:
            distribution[0]['count'] += 1
        elif 3 <= dc <= 5:
            distribution[1]['count'] += 1
        elif 6 <= dc <= 10:
            distribution[2]['count'] += 1
        else:
            distribution[3]['count'] += 1
    
    dist_docs = []
    for i, d in enumerate(distribution):
        dist_docs.append({
            'bucket_id': i,
            'bucket': d['bucket'],
            'count': d['count'],
            'computed_at': datetime.now(timezone.utc)
        })
    
    target_db['shared-keys-distribution'].insert_many(dist_docs)
    print_success("Stored distribution")
    for d in distribution:
        print_info(f"  • {d['bucket']:<10} = {d['count']:,} groups")
    print()
    
    # Step D: Compute by issuer
    print_info("Step 4D: Computing by issuer (top 100)...")
    
    issuer_pipeline = [
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
        }},
        {'$group': {
            '_id': {'$ifNull': [{'$arrayElemAt': ['$parsed.issuer.organization', 0]}, 'Unknown']},
            'shared_certs': {'$sum': 1}
        }},
        {'$sort': {'shared_certs': -1}},
        {'$limit': 100}
    ]
    
    issuer_results = list(source_collection.aggregate(issuer_pipeline, allowDiskUse=True))
    
    issuer_docs = []
    for i, r in enumerate(issuer_results):
        issuer_docs.append({
            'rank': i + 1,
            'issuer': r['_id'],
            'shared_certs': r['shared_certs'],
            'computed_at': datetime.now(timezone.utc)
        })
    
    if issuer_docs:
        target_db['shared-keys-by-issuer'].insert_many(issuer_docs)
        target_db['shared-keys-by-issuer'].create_index('rank')
        print_success(f"Stored {len(issuer_docs)} issuers")
        print_info(f"  Top: {issuer_docs[0]['issuer']} ({issuer_docs[0]['shared_certs']:,} certs)")
    print()
    
    # Step E: Compute timeline
    print_info("Step 4E: Computing timeline (last 12 months)...")
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=12 * 30)
    start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    timeline_pipeline = [
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints},
            'parsed.validity.start': {'$gte': start_str}
        }},
        {'$project': {
            'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
            'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}}
        }},
        {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
        {'$group': {
            '_id': {'year': '$year', 'month': '$month'},
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id.year': 1, '_id.month': 1}}
    ]
    
    timeline_results = list(source_collection.aggregate(timeline_pipeline, allowDiskUse=True))
    
    month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    timeline_docs = []
    for i, r in enumerate(timeline_results):
        year = r['_id']['year']
        month = r['_id']['month']
        timeline_docs.append({
            'order': i,
            'month': f"{month_names[month]} {year}",
            'monthNum': month,
            'year': year,
            'count': r['count'],
            'computed_at': datetime.now(timezone.utc)
        })
    
    if timeline_docs:
        target_db['shared-keys-timeline'].insert_many(timeline_docs)
        target_db['shared-keys-timeline'].create_index('order')
        print_success(f"Stored {len(timeline_docs)} timeline entries")
    else:
        print_info("No timeline data in last 12 months")
    print()
    
    # Step F: Compute heatmap
    print_info("Step 4F: Computing issuer x key-type heatmap...")
    
    heatmap_pipeline = [
        {'$match': {
            'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
        }},
        {'$project': {
            'issuer': {'$ifNull': [{'$arrayElemAt': ['$parsed.issuer.organization', 0]}, 'Unknown']},
            'key_algo': {'$ifNull': ['$parsed.subject_key_info.key_algorithm.name', 'Unknown']},
            'key_length': {'$ifNull': ['$parsed.subject_key_info.rsa_public_key.length', 0]}
        }},
        {'$addFields': {
            'key_type': {
                '$concat': [
                    '$key_algo',
                    '-',
                    {'$toString': '$key_length'}
                ]
            }
        }},
        {'$group': {
            '_id': {'issuer': '$issuer', 'key_type': '$key_type'},
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
    
    heatmap_results = list(source_collection.aggregate(heatmap_pipeline, allowDiskUse=True))
    
    heatmap_docs = []
    for r in heatmap_results:
        heatmap_docs.append({
            'issuer': r['_id']['issuer'],
            'key_type': r['_id']['key_type'],
            'count': r['count'],
            'computed_at': datetime.now(timezone.utc)
        })
    
    if heatmap_docs:
        target_db['shared-keys-heatmap'].insert_many(heatmap_docs)
        target_db['shared-keys-heatmap'].create_index([('issuer', 1), ('key_type', 1)])
        target_db['shared-keys-heatmap'].create_index('count')
        print_success(f"Stored {len(heatmap_docs)} heatmap cells")
    print()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_progress("Step 5/5: Creating indexes and metadata...")
    
    # Store metadata in each collection
    metadata = {
        'last_computed': datetime.now(timezone.utc),
        'computation_duration_seconds': duration,
        'total_shared_groups': len(shared_key_groups),
        'total_certs_at_risk': total_certs_at_risk
    }
    
    target_db['shared-keys-groups'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    target_db['shared-keys-stats'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    target_db['shared-keys-distribution'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    target_db['shared-keys-by-issuer'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    target_db['shared-keys-timeline'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    target_db['shared-keys-heatmap'].replace_one({'_id': 'metadata'}, {'_id': 'metadata', **metadata}, upsert=True)
    
    print_success("Stored metadata in all collections")
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("SHARED KEYS ANALYTICS COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Computation Time: {BOLD}{duration:.2f}s{RESET}")
    print_info(f"Shared Key Groups: {BOLD}{len(shared_key_groups):,}{RESET}")
    print_info(f"Certificates at Risk: {BOLD}{total_certs_at_risk:,}{RESET}")
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
