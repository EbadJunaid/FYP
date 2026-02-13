#!/usr/bin/env python3
"""
Pre-compute Shared Keys Analytics with Detailed Certificate Data
This script stores comprehensive information for each shared key group
for both table view and detail page display.
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

def get_key_size(cert):
    """Extract key size from certificate"""
    try:
        if cert.get('parsed', {}).get('subject_key_info', {}).get('rsa_public_key'):
            return cert['parsed']['subject_key_info']['rsa_public_key'].get('length', 0)
        elif cert.get('parsed', {}).get('subject_key_info', {}).get('ecdsa_public_key'):
            return cert['parsed']['subject_key_info']['ecdsa_public_key'].get('length', 0)
        return 0
    except:
        return 0

def calculate_days_until_expiry(validity_end_str):
    """Calculate days until certificate expiry"""
    try:
        if not validity_end_str:
            return None
        end_date = datetime.fromisoformat(validity_end_str.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        delta = end_date - now
        return delta.days
    except:
        return None

def main():
    print_progress("=" * 70, BOLD)
    print_progress("SHARED KEYS DETAILED ANALYTICS GENERATOR", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Connect to MongoDB
    print_progress("Step 1/4: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    print_progress("Step 2/4: Accessing databases...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    total_docs = source_collection.estimated_document_count()
    print_success(f"Found {total_docs:,} total certificates")
    
    target_db = client['tranco-latest-8-lakh-results']
    
    # Clear ALL old shared keys collections
    print_info("Deleting old shared keys collections...")
    old_collections = [
        'shared-keys-groups', 'shared-keys-stats', 'shared-keys-distribution', 
        'shared-keys-by-issuer', 'shared-keys-timeline', 'shared-keys-heatmap'
    ]
    for coll_name in old_collections:
        try:
            target_db[coll_name].drop()
            print_info(f"  Dropped: {coll_name}")
        except Exception:
            pass
    
    print_success("Old collections deleted")
    
    print_progress("Step 3/4: Identifying shared keys...")
    print_info("This will take 10-15 minutes to analyze all certificates...")
    print()
    
    start_time = datetime.now()
    
    # Find all shared public keys
    print_info("Finding shared public keys...")
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
    
    # Process each shared key group and collect detailed certificate information
    print_info("Processing shared key groups for detailed information...")
    print_info(f"This will process {len(shared_key_groups):,} groups...")
    print()
    
    detailed_collection = target_db['shared-keys-detailed']
    processed_count = 0
    total_certs_at_risk = 0
    
    for idx, group in enumerate(shared_key_groups):
        if (idx + 1) % 100 == 0:
            print_info(f"  Processed {idx + 1:,}/{len(shared_key_groups):,} groups...")
        
        public_key_hash = group['_id']
        
        # Fetch all certificates using this public key
        certificates = list(source_collection.find({
            'parsed.subject_key_info.fingerprint_sha256': public_key_hash
        }))
        
        if not certificates:
            continue
        
        # Extract detailed information for each certificate
        certificate_details = []
        all_domains = set()
        all_sans = []
        issuer_map = {}
        
        for cert in certificates:
            try:
                parsed = cert.get('parsed', {})
                extensions = parsed.get('extensions', {})
                san_ext = extensions.get('subject_alt_name', {})
                sans = san_ext.get('dns_names', [])
                
                # Get issuer information
                issuer_info = parsed.get('issuer', {})
                issuer_org = issuer_info.get('organization', ['Unknown'])[0] if issuer_info.get('organization') else 'Unknown'
                issuer_cn = issuer_info.get('common_name', ['Unknown'])[0] if issuer_info.get('common_name') else 'Unknown'
                issuer_dn = parsed.get('issuer_dn', 'Unknown')
                issuer_country = issuer_info.get('country', ['Unknown'])[0] if issuer_info.get('country') else 'Unknown'
                
                # Track issuer count
                if issuer_org not in issuer_map:
                    issuer_map[issuer_org] = {'name': issuer_org, 'cn': issuer_cn, 'count': 0}
                issuer_map[issuer_org]['count'] += 1
                
                # Get validity information
                validity = parsed.get('validity', {})
                validity_start = validity.get('start', '')
                validity_end = validity.get('end', '')
                validity_length_seconds = validity.get('length', 0)
                validity_days = validity_length_seconds / 86400 if validity_length_seconds else 0
                
                days_until_expiry = calculate_days_until_expiry(validity_end)
                is_expired = days_until_expiry is not None and days_until_expiry < 0
                is_expiring_soon = days_until_expiry is not None and 0 <= days_until_expiry < 30
                
                # Get subject information
                subject_info = parsed.get('subject', {})
                subject_cn = subject_info.get('common_name', ['Unknown'])[0] if subject_info.get('common_name') else 'Unknown'
                subject_dn = parsed.get('subject_dn', 'Unknown')
                
                # Get key information
                key_info = parsed.get('subject_key_info', {})
                key_algo = key_info.get('key_algorithm', {}).get('name', 'Unknown')
                key_size = get_key_size(cert)
                key_type = f"{key_algo}-{key_size}" if key_size > 0 else key_algo
                
                # Get signature information
                signature_info = parsed.get('signature_algorithm', {})
                signature_algo = signature_info.get('name', 'Unknown')
                
                # Get validation level
                validation_level = parsed.get('validation_level', 'Unknown')
                
                # Check for wildcard SANs
                wildcard_sans = [san for san in sans if '*' in san]
                has_wildcard = len(wildcard_sans) > 0
                
                # Get certificate fingerprint
                cert_fingerprint = parsed.get('fingerprint_sha256', 'Unknown')
                
                # Get certificate ID (MongoDB _id)
                cert_id = str(cert.get('_id', ''))
                
                # Get serial number
                serial_number = parsed.get('serial_number', 'Unknown')
                
                # Get self-signed status
                is_self_signed = parsed.get('signature', {}).get('self_signed', False)
                
                # Get domain
                domain = cert.get('domain', 'Unknown')
                all_domains.add(domain)
                all_sans.extend(sans)
                
                # Get scanned_at
                scanned_at = cert.get('scanned_at')
                if scanned_at:
                    scanned_at = scanned_at.isoformat() if hasattr(scanned_at, 'isoformat') else str(scanned_at)
                
                # Extended key usage
                eku = extensions.get('extended_key_usage', {})
                extended_key_usage = []
                if eku.get('server_auth'):
                    extended_key_usage.append('serverAuth')
                if eku.get('client_auth'):
                    extended_key_usage.append('clientAuth')
                
                # OCSP and issuer URLs
                aia = extensions.get('authority_info_access', {})
                ocsp_urls = aia.get('ocsp_urls', [])
                issuer_urls = aia.get('issuer_urls', [])
                
                # Build certificate detail object
                cert_detail = {
                    'certificate_id': cert_id,  # MongoDB _id for linking to detail page
                    'certificate_fingerprint': cert_fingerprint,
                    'certificate_fingerprint_short': cert_fingerprint[:16] if cert_fingerprint != 'Unknown' else 'Unknown',
                    'domain': domain,
                    'sans': sans,
                    'sans_count': len(sans),
                    'has_wildcard': has_wildcard,
                    'wildcard_sans': wildcard_sans,
                    'subject_cn': subject_cn,
                    'subject_dn': subject_dn,
                    'issuer_organization': issuer_org,
                    'issuer_cn': issuer_cn,
                    'issuer_dn': issuer_dn,
                    'issuer_country': issuer_country,
                    'validity_start': validity_start,
                    'validity_end': validity_end,
                    'validity_days': int(validity_days),
                    'is_expired': is_expired,
                    'days_until_expiry': days_until_expiry,
                    'is_expiring_soon': is_expiring_soon,
                    'validation_level': validation_level,
                    'key_algorithm': key_algo,
                    'key_size': key_size,
                    'key_type': key_type,
                    'signature_algorithm': signature_algo,
                    'is_self_signed': is_self_signed,
                    'serial_number': str(serial_number),
                    'extended_key_usage': extended_key_usage,
                    'ocsp_urls': ocsp_urls,
                    'issuer_urls': issuer_urls,
                    'scanned_at': scanned_at
                }
                
                certificate_details.append(cert_detail)
                
            except Exception as e:
                print_error(f"Error processing certificate: {str(e)}")
                continue
        
        if not certificate_details:
            continue
        
        # Calculate risk level
        cert_count = len(certificate_details)
        total_sans = len(set(all_sans))
        
        if cert_count >= 5 or total_sans >= 20:
            risk_level = 'HIGH'
        elif cert_count >= 3 or total_sans >= 10:
            risk_level = 'MEDIUM'
        else:
            risk_level = 'LOW'
        
        # Generate risk factors
        risk_factors = [
            f"{cert_count} certificates share the same private key",
            f"{len(all_domains)} different domains affected",
            f"{total_sans} SANs at risk if private key is compromised"
        ]
        
        if len(issuer_map) > 1:
            risk_factors.append(f"Certificates from {len(issuer_map)} different Certificate Authorities")
        
        # Get most affected domain (domain with most SANs)
        domain_sans_count = {}
        for cert_detail in certificate_details:
            domain = cert_detail['domain']
            sans_count = cert_detail['sans_count']
            if domain not in domain_sans_count or sans_count > domain_sans_count[domain]:
                domain_sans_count[domain] = sans_count
        
        most_affected_domain = max(domain_sans_count.items(), key=lambda x: x[1]) if domain_sans_count else ('Unknown', 0)
        
        # Get key type from first certificate
        key_type = certificate_details[0]['key_type']
        key_algo = certificate_details[0]['key_algorithm']
        key_size = certificate_details[0]['key_size']
        
        # Build issuers list
        issuers_list = [
            {
                'organization': issuer_data['name'],
                'common_name': issuer_data['cn'],
                'certificate_count': issuer_data['count']
            }
            for issuer_data in issuer_map.values()
        ]
        
        # Sort issuers by count descending
        issuers_list.sort(key=lambda x: x['certificate_count'], reverse=True)
        
        # Sample domains (first 3)
        sample_domains = list(all_domains)[:3]
        
        # Sample SANs (first 5 unique)
        unique_sans = list(set(all_sans))
        sample_sans = unique_sans[:5]
        
        # Build final document
        document = {
            '_id': public_key_hash,
            'public_key_hash': public_key_hash,
            'public_key_hash_short': public_key_hash[:16],
            
            # Summary for table view
            'certificate_count': cert_count,
            'total_domains': len(all_domains),
            'sample_domains': sample_domains,
            'total_sans': total_sans,
            'sample_sans': sample_sans,
            'unique_sans': unique_sans,
            
            # Key information
            'key_algorithm': key_algo,
            'key_size': key_size,
            'key_type': key_type,
            
            # Issuers
            'issuers': issuers_list,
            'issuer_count': len(issuers_list),
            
            # Risk assessment
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            
            # Most affected
            'most_affected_domain': {
                'domain': most_affected_domain[0],
                'sans_count': most_affected_domain[1]
            },
            
            # Full certificate details for detail page
            'certificates': certificate_details,
            
            # Metadata
            'computed_at': datetime.now(timezone.utc),
            'last_updated': datetime.now(timezone.utc)
        }
        
        # Store document
        detailed_collection.replace_one(
            {'_id': public_key_hash},
            document,
            upsert=True
        )
        
        processed_count += 1
        total_certs_at_risk += cert_count
    
    print_success(f"Processed {processed_count:,} shared key groups")
    print_success(f"Total certificates at risk: {total_certs_at_risk:,}")
    print()
    
    # Create indexes
    print_progress("Step 4/4: Creating indexes...")
    
    detailed_collection.create_index([('certificate_count', -1)])
    detailed_collection.create_index([('total_sans', -1)])
    detailed_collection.create_index([('risk_level', 1)])
    detailed_collection.create_index([('key_type', 1)])
    detailed_collection.create_index([('issuer_count', 1)])
    detailed_collection.create_index([('certificates.domain', 1)])
    detailed_collection.create_index([('issuers.organization', 1)])
    detailed_collection.create_index([('computed_at', -1)])
    
    print_success("Indexes created")
    
    # Calculate key statistics
    print_progress("Calculating public key statistics...")
    
    # Total Public Keys = All distinct keys (including shared ones)
    # Formula: non-shared keys + shared key groups
    total_public_keys = total_docs - total_certs_at_risk + processed_count
    
    # Unique Public Keys = Keys used by only ONE certificate (truly unique, not shared)
    # Formula: total certificates - certificates at risk
    unique_public_keys = total_docs - total_certs_at_risk
    
    print_success(f"Total Public Keys (distinct): {total_public_keys:,}")
    print_success(f"Unique Public Keys (non-shared): {unique_public_keys:,}")
    print_success(f"Shared Public Keys: {processed_count:,}")
    
    # Store metadata
    metadata = {
        '_id': 'metadata',
        'last_computed': datetime.now(timezone.utc),
        'computation_duration_seconds': (datetime.now() - start_time).total_seconds(),
        'total_shared_groups': processed_count,
        'total_certs_at_risk': total_certs_at_risk,
        'total_certificates_scanned': total_docs,
        'total_public_keys': total_public_keys,
        'unique_public_keys': unique_public_keys
    }
    
    detailed_collection.replace_one({'_id': 'metadata'}, metadata, upsert=True)
    print_success("Metadata stored")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print()
    print_progress("=" * 70, BOLD)
    print_success("SHARED KEYS DETAILED ANALYTICS COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Computation Time: {BOLD}{duration:.2f}s{RESET} ({duration/60:.1f} minutes)")
    print_info(f"Shared Key Groups: {BOLD}{processed_count:,}{RESET}")
    print_info(f"Certificates at Risk: {BOLD}{total_certs_at_risk:,}{RESET}")
    print_info(f"New Collection: {BOLD}shared-keys-detailed{RESET}")
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
