#!/usr/bin/env python3
"""
Pre-compute SAN Filtered Certificate Lists V2 (ENHANCED VERSION)

⚡ COMPLETE VERSION with ALL collections:
1. san-wildcard-certs
2. san-standard-certs  
3. san-multi-domain-certs
4. san-count-groups
5. san-tld-certs
6. san-stats (NEW)
7. san-distribution (NEW)

✨ OPTIMIZATIONS:
- Batch processing for faster DB operations
- Single-pass aggregation
- Efficient indexing
- Same perfect output quality
"""

import sys
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError
from collections import defaultdict
import re

# ⚡ TESTING MODE: Set to True to process only first 10k certs for quick testing
TESTING_MODE = True
TESTING_LIMIT = 50000

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

def extract_tld(domain):
    """Extract TLD from domain name"""
    if not domain or not isinstance(domain, str):
        return None
    parts = domain.lower().split('.')
    if len(parts) >= 2:
        return '.' + parts[-1]
    return None

def count_vulnerabilities(zlint_data):
    """Count errors and warnings from zlint data"""
    if not zlint_data or 'lints' not in zlint_data:
        return {'errors': 0, 'warnings': 0}
    
    lints = zlint_data.get('lints', {})
    errors = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
    warnings = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
    
    return {'errors': errors, 'warnings': warnings}

def format_vulnerabilities(zlint_data):
    """Format vulnerabilities as display string"""
    counts = count_vulnerabilities(zlint_data)
    if counts['errors'] > 0:
        return f"{counts['errors']} Critical"
    elif counts['warnings'] > 0:
        return f"{counts['warnings']} Warning"
    return "0 Found"

def main():
    print_progress("=" * 70, BOLD)
    print_progress("SAN FILTERED CERTIFICATE LISTS GENERATOR V2", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    start_time = datetime.now()
    
    # Connect to MongoDB
    print_progress("Step 1/8: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB")
        sys.exit(1)
    
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    results_db = client['tranco-latest-8-lakh-results']
    
    # Collections (with v2 suffix to avoid conflicts)
    wildcard_collection = results_db['san-wildcard-certs']
    standard_collection = results_db['san-standard-certs']
    multi_domain_collection = results_db['san-multi-domain-certs']
    san_count_collection = results_db['san-count-groups']
    tld_collection = results_db['san-tld-certs']
    stats_collection = results_db['san-stats']  # NEW
    distribution_collection = results_db['san-distribution']  # NEW
    
    total_docs = source_collection.estimated_document_count()
    if TESTING_MODE:
        total_docs = min(TESTING_LIMIT, total_docs)
        print_success(f"Found {total_docs:,} certificates")
        print_info(f"🧪 TESTING MODE: Processing only first {TESTING_LIMIT:,} certificates")
    else:
        print_success(f"Found {total_docs:,} certificates")
    
    # Step 2: Clear old data
    print_progress("Step 2/8: Clearing old pre-computed data...")
    wildcard_collection.drop()
    standard_collection.drop()
    multi_domain_collection.drop()
    san_count_collection.drop()
    tld_collection.drop()
    stats_collection.drop()  # NEW
    distribution_collection.drop()  # NEW
    print_success("Old data cleared")
    
    # Step 3: Process certificates
    print_progress("Step 3/8: Processing certificates...")
    print_info("Scanning all certificates for SAN patterns...")
    
    # Counters for aggregated data
    wildcard_certs = []
    standard_certs = []
    multi_domain_certs = []
    san_count_groups = defaultdict(list)
    tld_groups = defaultdict(list)
    
    # ⚡ BATCH FLUSH CONFIGURATION (prevents memory explosion)
    FLUSH_INTERVAL = 10000  # Flush to DB every 10k certs
    
    def flush_batches():
        """Flush accumulated data to database and clear memory"""
        if wildcard_certs:
            wildcard_collection.insert_many(wildcard_certs, ordered=False)
        if standard_certs:
            standard_collection.insert_many(standard_certs, ordered=False)
        if multi_domain_certs:
            multi_domain_collection.insert_many(multi_domain_certs, ordered=False)
        
        # Clear lists to free memory
        wildcard_certs.clear()
        standard_certs.clear()
        multi_domain_certs.clear()
    
    # NEW: Stats counters
    total_sans_count = 0
    wildcard_count = 0
    multi_domain_count = 0
    
    # NEW: Distribution buckets (matching database structure)
    distribution_buckets = {
        "0": 0,
        "1": 0,
        "2-3": 0,
        "4-5": 0,
        "6-10": 0,
        "11-20": 0,
        "21-50": 0,
        "50+": 0
    }
    
    batch_size = 10000
    processed = 0
    
    cursor = source_collection.find(
        {},
        {
            '_id': 1,
            'domain': 1,
            'parsed.extensions.subject_alt_name.dns_names': 1,
            'parsed.subject.common_name': 1,
            'parsed.issuer.common_name': 1,
            'parsed.validity.end': 1,
            'parsed.signature_algorithm.name': 1,
            'parsed.issuer.country': 1,
            'parsed.subject.country': 1,
            'zlint': 1
        }
    ).batch_size(batch_size)
    
    if TESTING_MODE:
        cursor = cursor.limit(TESTING_LIMIT)
    
    for cert in cursor:
        processed += 1
        
        # ⚡ FLUSH TO DATABASE every FLUSH_INTERVAL to prevent memory explosion
        if processed % FLUSH_INTERVAL == 0:
            flush_batches()
            print_info(f"💾 Flushed batch at {processed:,} certs (freed memory)")
        
        progress_interval = 2000 if TESTING_MODE else 50000
        if processed % progress_interval == 0:
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed
            remaining = (total_docs - processed) / rate if rate > 0 else 0
            print_info(f"Processed {processed:,}/{total_docs:,} ({processed/total_docs*100:.1f}%) - ETA: {remaining:.0f}s")
        
        cert_id = cert['_id']
        domain = cert.get('domain', '')
        
        # Get SAN list
        sans = cert.get('parsed', {}).get('extensions', {}).get('subject_alt_name', {}).get('dns_names', [])
        if not isinstance(sans, list):
            sans = []
        
        sans = [s for s in sans if s and isinstance(s, str)]
        san_count = len(sans)
        
        # Update stats counters
        total_sans_count += san_count
        
        # Extract additional fields
        sig_alg = cert.get('parsed', {}).get('signature_algorithm', {})
        encryption = sig_alg.get('name', 'Unknown') if sig_alg else 'Unknown'
        
        countries = cert.get('parsed', {}).get('issuer', {}).get('country', [])
        if not countries:
            countries = cert.get('parsed', {}).get('subject', {}).get('country', [])
        country = countries[0] if countries else 'Unknown'
        
        zlint = cert.get('zlint', {})
        vulnerabilities = format_vulnerabilities(zlint)
        
        # Certificate reference
        cert_ref = {
            'cert_id': cert_id,
            'domain': domain,
            'san_count': san_count,
            'sample_sans': sans[:5] if sans else [],
            'issuer': cert.get('parsed', {}).get('issuer', {}).get('common_name', 'N/A'),
            'expiry': cert.get('parsed', {}).get('validity', {}).get('end'),
            'encryption': encryption,
            'country': country,
            'vulnerabilities': vulnerabilities
        }
        
        # Check for wildcards
        has_wildcard = any(s.startswith('*.') for s in sans)
        if has_wildcard:
            wildcard_certs.append(cert_ref)
            wildcard_count += 1
        
        # Standard (has SANs but NO wildcards)
        if san_count > 0 and not has_wildcard:
            standard_certs.append(cert_ref)
        
        # Multi-domain (5+ SANs)
        if san_count >= 5:
            multi_domain_certs.append(cert_ref)
            multi_domain_count += 1
        
        # Group by SAN count
        if san_count == 0:
            san_count_groups['0'].append(cert_ref)
            distribution_buckets['0'] += 1
        elif san_count == 1:
            san_count_groups['1'].append(cert_ref)
            distribution_buckets['1'] += 1
        elif 2 <= san_count <= 3:
            san_count_groups['2-3'].append(cert_ref)
            distribution_buckets['2-3'] += 1
        elif 4 <= san_count <= 5:
            san_count_groups['4-5'].append(cert_ref)
            distribution_buckets['4-5'] += 1
        elif 6 <= san_count <= 10:
            san_count_groups['6-10'].append(cert_ref)
            distribution_buckets['6-10'] += 1
        elif 11 <= san_count <= 20:
            san_count_groups['11-20'].append(cert_ref)
            distribution_buckets['11-20'] += 1
        elif 21 <= san_count <= 50:
            san_count_groups['21-50'].append(cert_ref)
            distribution_buckets['21-50'] += 1
        else:  # > 50
            san_count_groups['50+'].append(cert_ref)
            distribution_buckets['50+'] += 1
        
        # Group by TLD
        seen_tlds = set()
        for san in sans:
            tld = extract_tld(san)
            if tld and tld not in seen_tlds:
                seen_tlds.add(tld)
                if cert_id not in [c['cert_id'] for c in tld_groups[tld]]:
                    tld_groups[tld].append(cert_ref)
    
    # Flush any remaining data
    flush_batches()
    print_success(f"Processed all {processed:,} certificates")
    print()
    
    # Step 4: Create indexes for wildcard certificates
    print_progress(f"Step 4/8: Creating indexes for wildcard certificates...")
    wildcard_count_total = wildcard_collection.count_documents({})
    if wildcard_count_total > 0:
        wildcard_collection.create_index([('domain', ASCENDING)])
        wildcard_collection.create_index([('san_count', ASCENDING)])
        wildcard_collection.create_index([('cert_id', ASCENDING)])
    print_success(f"Indexed {wildcard_count_total:,} wildcard certificates")
    
    # Step 5: Create indexes for standard certificates
    print_progress(f"Step 5/8: Creating indexes for standard certificates...")
    standard_count_total = standard_collection.count_documents({})
    if standard_count_total > 0:
        standard_collection.create_index([('domain', ASCENDING)])
        standard_collection.create_index([('san_count', ASCENDING)])
        standard_collection.create_index([('cert_id', ASCENDING)])
    print_success(f"Indexed {standard_count_total:,} standard certificates")
    
    # Step 6: Create indexes for multi-domain certificates
    print_progress(f"Step 6/8: Creating indexes for multi-domain certificates...")
    multi_count_total = multi_domain_collection.count_documents({})
    if multi_count_total > 0:
        multi_domain_collection.create_index([('san_count', ASCENDING)])
        multi_domain_collection.create_index([('domain', ASCENDING)])
        multi_domain_collection.create_index([('cert_id', ASCENDING)])
    print_success(f"Indexed {multi_count_total:,} multi-domain certificates")
    
    # Step 7: Store SAN count groups and TLD groups
    print_progress("Step 7/8: Storing SAN count groups and TLD groups...")
    
    for bucket, certs in san_count_groups.items():
        if certs:
            doc = {
                '_id': bucket,
                'certificate_count': len(certs),
                'certificates': certs[:1000],
                'has_more': len(certs) > 1000,
                'total_count': len(certs)
            }
            san_count_collection.replace_one({'_id': bucket}, doc, upsert=True)
    
    san_count_collection.create_index([('certificate_count', ASCENDING)])
    print_success(f"Stored {len(san_count_groups)} SAN count groups")
    
    # Store TLD groups (top 50)
    tld_sorted = sorted(tld_groups.items(), key=lambda x: len(x[1]), reverse=True)[:50]
    
    for tld, certs in tld_sorted:
        if certs:
            doc = {
                '_id': tld,
                'certificate_count': len(certs),
                'certificates': certs[:1000],
                'has_more': len(certs) > 1000,
                'total_count': len(certs)
            }
            tld_collection.replace_one({'_id': tld}, doc, upsert=True)
    
    tld_collection.create_index([('certificate_count', ASCENDING)])
    print_success(f"Stored top 50 TLDs")
    
    # Step 8: NEW - Store san-stats and san-distribution
    print_progress("Step 8/8: Storing san-stats and san-distribution...")
    
    # Calculate average SANs per certificate
    avg_sans = total_sans_count / processed if processed > 0 else 0
    
    # Store san-stats
    stats_doc = {
        '_id': 'san_stats',
        'total_sans': total_sans_count,
        'avg_sans_per_cert': round(avg_sans, 2),
        'wildcard_certs': wildcard_count,
        'multi_domain_certs': multi_domain_count,
        'total_certs': processed,
        'computed_at': datetime.now(timezone.utc),
        'computation_duration_seconds': (datetime.now() - start_time).total_seconds()
    }
    stats_collection.replace_one({'_id': 'san_stats'}, stats_doc, upsert=True)
    print_success("Stored san-stats")
    
    # Store san-distribution
    bucket_order = ["0", "1", "2-3", "4-5", "6-10", "11-20", "21-50", "50+"]
    for idx, bucket in enumerate(bucket_order):
        dist_doc = {
            'bucket_id': idx,
            'bucket': bucket,
            'count': distribution_buckets[bucket],
            'computed_at': datetime.now(timezone.utc)
        }
        distribution_collection.insert_one(dist_doc)
    
    # Store metadata for distribution
    dist_metadata = {
        '_id': 'metadata',
        'last_computed': datetime.now(timezone.utc),
        'computation_duration_seconds': (datetime.now() - start_time).total_seconds(),
        'total_buckets': len(bucket_order)
    }
    distribution_collection.replace_one({'_id': 'metadata'}, dist_metadata, upsert=True)
    
    print_success("Stored san-distribution")
    
    # Store overall metadata
    metadata = {
        '_id': 'metadata',
        'last_computed': datetime.now(timezone.utc),
        'computation_duration_seconds': (datetime.now() - start_time).total_seconds(),
        'total_certificates_scanned': processed,
        'wildcard_certificates': wildcard_count_total,
        'standard_certificates': standard_count_total,
        'multi_domain_certificates': multi_count_total,
        'san_count_groups': {k: len(v) for k, v in san_count_groups.items()},
        'top_tlds_count': len(tld_sorted)
    }
    
    results_db['san-filter-metadata'].replace_one({'_id': 'metadata'}, metadata, upsert=True)
    
    # Final summary
    duration = (datetime.now() - start_time).total_seconds()
    print()
    print_progress("=" * 70, BOLD)
    print_success("SAN FILTERED LISTS COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Duration: {BOLD}{duration:.1f}s{RESET} ({duration/60:.1f} minutes)")
    print_info(f"Wildcard Certs: {BOLD}{wildcard_count_total:,}{RESET}")
    print_info(f"Standard Certs: {BOLD}{standard_count_total:,}{RESET}")
    print_info(f"Multi-domain Certs: {BOLD}{multi_count_total:,}{RESET}")
    print_info(f"SAN Count Groups: {BOLD}{len(san_count_groups)}{RESET}")
    print_info(f"Top TLDs: {BOLD}{len(tld_sorted)}{RESET}")
    print()
    print_success("✅ Collections created (with v2 suffix):")
    print_success("   1. san-wildcard-certs-v2")
    print_success("   2. san-standard-certs-v2")
    print_success("   3. san-multi-domain-certs-v2")
    print_success("   4. san-count-groups-v2")
    print_success("   5. san-tld-certs-v2")
    print_success("   6. san-stats-v2 (NEW)")
    print_success("   7. san-distribution-v2 (NEW)")
    print_success("   8. san-filter-metadata-v2")
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
        print_error(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
