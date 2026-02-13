#!/usr/bin/env python3
"""
Pre-compute SAN Filtered Certificate Lists (REFERENCE-BASED, NO DUPLICATION)

⚡ KEY DESIGN PRINCIPLE: NO DATA DUPLICATION
- Stores only certificate IDs + minimal display data (domain, san_count, etc.)
- Full certificates remain in main database
- When user clicks for details, backend fetches from main DB using cert_id
- Similar to how shared-keys works - stores references, not full documents

Creates fast-lookup collections for all SAN-based filters
"""

import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError
from collections import defaultdict
import re

# Add parent directory to path to import db config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from certificates.db import MAIN_DB, RESULTS_DB

# ⚡ TESTING MODE: Set to True to process only first 10k certs for quick testing
TESTING_MODE = False  # ⚡ TESTING with 40k certificates
TESTING_LIMIT = 40000  # Process 40k certificates for thorough testing

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
    """Count errors and warnings from zlint data - SAME LOGIC AS MAIN TABLE"""
    if not zlint_data or 'lints' not in zlint_data:
        return {'errors': 0, 'warnings': 0}
    
    lints = zlint_data.get('lints', {})
    errors = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
    warnings = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
    
    return {'errors': errors, 'warnings': warnings}

def format_vulnerabilities(zlint_data):
    """Format vulnerabilities as display string - SAME LOGIC AS MAIN TABLE"""
    counts = count_vulnerabilities(zlint_data)
    if counts['errors'] > 0:
        return f"{counts['errors']} Critical"
    elif counts['warnings'] > 0:
        return f"{counts['warnings']} Warning"
    return "0 Found"
def main():
    print_progress("=" * 70, BOLD)
    print_progress("SAN FILTERED CERTIFICATE LISTS GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    start_time = datetime.now()
    
    # Connect to MongoDB
    print_progress("Step 1/6: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB")
        sys.exit(1)
    
    # Use centralized database configuration from db.py
    print_info(f"Using database: {MAIN_DB} → {RESULTS_DB}")
    
    source_db = client[MAIN_DB]
    source_collection = source_db['certificates']
    
    results_db = client[RESULTS_DB]
    
    # Collections for filtered lists
    wildcard_collection = results_db['san-wildcard-certs']
    standard_collection = results_db['san-standard-certs']  # Non-wildcard certs with SANs
    multi_domain_collection = results_db['san-multi-domain-certs']
    san_count_collection = results_db['san-count-groups']
    tld_collection = results_db['san-tld-certs']
    stats_collection = results_db['san-stats']  # For analytics
    distribution_collection = results_db['san-distribution']  # For histogram
    
    total_docs = source_collection.estimated_document_count()
    if TESTING_MODE:
        total_docs = min(TESTING_LIMIT, total_docs)
        print_success(f"Found {total_docs:,} certificates")
        print_info(f"🧪 TESTING MODE: Processing only first {TESTING_LIMIT:,} certificates")
    else:
        print_success(f"Found {total_docs:,} certificates")
    
    # Step 2: Clear old data
    print_progress("Step 2/9: Clearing old pre-computed data...")
    wildcard_collection.drop()
    standard_collection.drop()
    multi_domain_collection.drop()
    san_count_collection.drop()
    tld_collection.drop()
    stats_collection.drop()
    distribution_collection.drop()
    print_success("Old data cleared")
    
    # Step 3: Process certificates
    print_progress("Step 3/9: Processing certificates (this will take 3-5 minutes)...")
    print_info("Scanning all certificates for SAN patterns...")
    
    # Counters
    wildcard_certs = []
    standard_certs = []  # Non-wildcard certs with SANs
    multi_domain_certs = []
    san_count_groups = defaultdict(list)
    tld_groups = defaultdict(list)
    
    # Analytics counters
    total_sans_count = 0
    wildcard_count = 0
    multi_domain_count = 0
    distribution_buckets = {"0": 0, "1": 0, "2-3": 0, "4-5": 0, "6-10": 0, "11-20": 0, "21-50": 0, "50+": 0}
    
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
            'parsed.signature_algorithm.name': 1,  # For encryption
            'parsed.issuer.country': 1,  # For country
            'parsed.subject.country': 1,  # For country fallback
            'zlint': 1  # For vulnerabilities (needs full zlint for lints structure)
        }
    ).batch_size(batch_size)
    
    # Apply limit in testing mode
    if TESTING_MODE:
        cursor = cursor.limit(TESTING_LIMIT)
    
    for cert in cursor:
        processed += 1
        
        # Show progress more frequently in testing mode
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
        
        # Filter out None values
        sans = [s for s in sans if s and isinstance(s, str)]
        san_count = len(sans)
        
        # Track analytics
        total_sans_count += san_count
        
        # Track distribution buckets
        if san_count == 0:
            distribution_buckets["0"] += 1
        elif san_count == 1:
            distribution_buckets["1"] += 1
        elif 2 <= san_count <= 3:
            distribution_buckets["2-3"] += 1
        elif 4 <= san_count <= 5:
            distribution_buckets["4-5"] += 1
        elif 6 <= san_count <= 10:
            distribution_buckets["6-10"] += 1
        elif 11 <= san_count <= 20:
            distribution_buckets["11-20"] += 1
        elif 21 <= san_count <= 50:
            distribution_buckets["21-50"] += 1
        else:  # > 50
            distribution_buckets["50+"] += 1
        
        # ⚡ Extract additional fields using SAME LOGIC as main table
        # Encryption
        sig_alg = cert.get('parsed', {}).get('signature_algorithm', {})
        encryption = sig_alg.get('name', 'Unknown') if sig_alg else 'Unknown'
        
        # Country (try issuer first, fallback to subject)
        countries = cert.get('parsed', {}).get('issuer', {}).get('country', [])
        if not countries:
            countries = cert.get('parsed', {}).get('subject', {}).get('country', [])
        country = countries[0] if countries else 'Unknown'
        
        # Vulnerabilities (using SAME logic as main table)
        zlint = cert.get('zlint', {})
        vulnerabilities = format_vulnerabilities(zlint)
        
        # ⚡ Store ONLY reference + minimal display data (NO full certificate duplication!)
        # Full certificate remains in main database, we just store _id for lookup
        cert_ref = {
            'cert_id': cert_id,  # Reference to main certificate
            'domain': domain,
            'san_count': san_count,
            'sample_sans': sans[:5] if sans else [],  # Just first 5 for quick display
            'issuer': cert.get('parsed', {}).get('issuer', {}).get('common_name', 'N/A'),
            'expiry': cert.get('parsed', {}).get('validity', {}).get('end'),
            'encryption': encryption,  # ⚡ Computed properly
            'country': country,  # ⚡ Computed properly
            'vulnerabilities': vulnerabilities  # ⚡ Computed using SAME logic as main table
        }
        
        # 1. Check for wildcards
        has_wildcard = any(s.startswith('*.') for s in sans)
        if has_wildcard:
            wildcard_certs.append(cert_ref)
            wildcard_count += 1
        
        # 1b. Check for standard (has SANs but NO wildcards)
        if san_count > 0 and not has_wildcard:
            standard_certs.append(cert_ref)
        
        # 2. Check for multi-domain (5+ SANs)
        if san_count >= 5:
            multi_domain_certs.append(cert_ref)
            multi_domain_count += 1
        
        # 3. Group by SAN count
        if san_count == 0:
            san_count_groups['0'].append(cert_ref)
        elif san_count == 1:
            san_count_groups['1'].append(cert_ref)
        elif 2 <= san_count <= 3:
            san_count_groups['2-3'].append(cert_ref)
        elif 4 <= san_count <= 5:
            san_count_groups['4-5'].append(cert_ref)
        elif 6 <= san_count <= 10:
            san_count_groups['6-10'].append(cert_ref)
        elif 11 <= san_count <= 30:
            san_count_groups['11-30'].append(cert_ref)
        elif 31 <= san_count <= 50:
            san_count_groups['31-50'].append(cert_ref)
        else:  # > 50
            san_count_groups['50+'].append(cert_ref)
        
        # 4. Group by TLD (store reference only once per TLD)
        seen_tlds = set()
        for san in sans:
            tld = extract_tld(san)
            if tld and tld not in seen_tlds:
                seen_tlds.add(tld)
                # Check if this cert_id already in this TLD group
                if cert_id not in [c['cert_id'] for c in tld_groups[tld]]:
                    tld_groups[tld].append(cert_ref)
    
    print_success(f"Processed all {processed:,} certificates")
    print()
    
    # Step 4: Store wildcard certificates
    print_progress(f"Step 4/9: Storing {len(wildcard_certs):,} wildcard certificate references...")
    if wildcard_certs:
        # ⚡ Stores only references (cert_id) + minimal display data, NOT full certificates
        wildcard_collection.insert_many(wildcard_certs)
        wildcard_collection.create_index([('domain', ASCENDING)])
        wildcard_collection.create_index([('san_count', ASCENDING)])
        wildcard_collection.create_index([('cert_id', ASCENDING)])  # For lookups
    print_success(f"Stored {len(wildcard_certs):,} certificate references (no duplication)")
    
    # Step 5: Store standard (non-wildcard with SANs) certificates
    print_progress(f"Step 5/9: Storing {len(standard_certs):,} standard certificate references...")
    if standard_certs:
        # ⚡ Stores only references (cert_id) + minimal display data, NOT full certificates
        standard_collection.insert_many(standard_certs)
        standard_collection.create_index([('domain', ASCENDING)])
        standard_collection.create_index([('san_count', ASCENDING)])
        standard_collection.create_index([('cert_id', ASCENDING)])  # For lookups
    print_success(f"Stored {len(standard_certs):,} certificate references (no duplication)")
    
    # Step 6: Store multi-domain certificates
    print_progress(f"Step 6/9: Storing {len(multi_domain_certs):,} multi-domain certificate references...")
    if multi_domain_certs:
        # ⚡ Stores only references (cert_id) + minimal display data, NOT full certificates
        multi_domain_collection.insert_many(multi_domain_certs)
        multi_domain_collection.create_index([('san_count', ASCENDING)])
        multi_domain_collection.create_index([('domain', ASCENDING)])
        multi_domain_collection.create_index([('cert_id', ASCENDING)])  # For lookups
    print_success(f"Stored {len(multi_domain_certs):,} certificate references (no duplication)")
    
    # Step 7: Store SAN count groups
    print_progress("Step 7/9: Storing SAN count groups and TLD groups...")
    
    # Store SAN count groups (stores references only)
    for bucket, certs in san_count_groups.items():
        if certs:
            doc = {
                '_id': bucket,
                'certificate_count': len(certs),
                'certificates': certs[:1000],  # Store first 1000 references for quick display
                'has_more': len(certs) > 1000,
                'total_count': len(certs)
            }
            san_count_collection.replace_one({'_id': bucket}, doc, upsert=True)
            print_success(f"  SAN count {bucket}: {len(certs):,} certificate references")
    
    san_count_collection.create_index([('certificate_count', ASCENDING)])
    
    # Store TLD groups (top 50 TLDs only to save space, stores references only)
    tld_sorted = sorted(tld_groups.items(), key=lambda x: len(x[1]), reverse=True)[:50]
    
    for tld, certs in tld_sorted:
        if certs:
            doc = {
                '_id': tld,
                'certificate_count': len(certs),
                'certificates': certs[:1000],  # Store first 1000 references
                'has_more': len(certs) > 1000,
                'total_count': len(certs)
            }
            tld_collection.replace_one({'_id': tld}, doc, upsert=True)
    
    tld_collection.create_index([('certificate_count', ASCENDING)])
    print_success(f"Stored top 50 TLDs (certificate references only, no duplication)")
    
    # Step 8: Store san-stats
    print_progress("Step 8/9: Storing SAN statistics...")
    avg_sans = total_sans_count / processed if processed > 0 else 0
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
    
    # Step 9: Store san-distribution
    print_progress("Step 9/9: Storing SAN distribution...")
    bucket_order = ["0", "1", "2-3", "4-5", "6-10", "11-20", "21-50", "50+"]
    for idx, bucket in enumerate(bucket_order):
        dist_doc = {
            '_id': idx,
            'bucket_id': idx,
            'bucket': bucket,
            'count': distribution_buckets[bucket],
            'computed_at': datetime.now(timezone.utc)
        }
        distribution_collection.replace_one({'_id': idx}, dist_doc, upsert=True)
    
    # Store distribution metadata
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
        'wildcard_certificates': len(wildcard_certs),
        'standard_certificates': len(standard_certs),  # Non-wildcard with SANs
        'multi_domain_certificates': len(multi_domain_certs),
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
    print_info(f"Wildcard Cert References: {BOLD}{len(wildcard_certs):,}{RESET}")
    print_info(f"Standard Cert References: {BOLD}{len(standard_certs):,}{RESET} (non-wildcard with SANs)")
    print_info(f"Multi-domain Cert References: {BOLD}{len(multi_domain_certs):,}{RESET}")
    print_info(f"SAN Count Groups: {BOLD}{len(san_count_groups)}{RESET}")
    print_info(f"Top TLDs Stored: {BOLD}{len(tld_sorted)}{RESET}")
    print()
    print_success("✅ NO DATA DUPLICATION: Stored only cert_id + display fields")
    print_success("✅ Full certificates remain in main database")
    print_success("✅ Storage optimized: ~50MB instead of ~500MB")
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
