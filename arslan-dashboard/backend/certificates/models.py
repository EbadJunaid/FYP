# backend/certificates/models.py
# Pure Python representation of SSL Certificate Model with PyMongo queries

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from .db import db, MongoDBClient  # Don't import results_db directly - use MongoDBClient.get_results_db() instead
from .shared_keys_models import SharedKeyModel
from .san_models import SANModel
from .trends_models import TrendsModel
from .ca_models import CAModel
from .signature_hash_models import SignatureHashModel
from .shared_models import SharedModels
from .validity_models import ValidityModels

# TLD to Country mapping for deriving country from domain
# TLD_TO_COUNTRY = {
#     'pk': 'Pakistan',
#     'us': 'United States',
#     'com': 'United States',
#     'uk': 'United Kingdom',
#     'co.uk': 'United Kingdom',
#     'de': 'Germany',
#     'fr': 'France',
#     'jp': 'Japan',
#     'ca': 'Canada',
#     'au': 'Australia',
#     'nl': 'Netherlands',
#     'in': 'India',
#     'cn': 'China',
#     'br': 'Brazil',
#     'kr': 'South Korea',
#     'sg': 'Singapore',
#     'ie': 'Ireland',
#     'se': 'Sweden',
#     'ch': 'Switzerland',
#     'it': 'Italy',
#     'es': 'Spain',
#     'ru': 'Russia',
#     'mx': 'Mexico',
#     'za': 'South Africa',
#     'nz': 'New Zealand',
#     'org': 'International',
#     'net': 'International',
#     'io': 'International',
#     'dev': 'International',
#     'ebad': 'ebad',  # For testing unknown TLD handling
#     'soy' : 'say' # For testing again 
# }


class CertificateModel:
    """
    Model class for SSL Certificate documents in MongoDB.
    Handles CRUD operations and aggregation queries.
    """
    collection = db['certificates']
    
   
    @staticmethod
    def get_status(validity_end: str) -> str:
        """Determine certificate status based on validity end date"""
        try:
            end_date = datetime.fromisoformat(validity_end.replace('Z', '+00:00'))
            now = datetime.now(timezone.utc)
            days_remaining = (end_date - now).days
            
            if days_remaining < 0:
                return 'EXPIRED'
            elif days_remaining <= 30:
                return 'EXPIRING_SOON'
            else:
                return 'VALID'
        except:
            return 'VALID'
    
    @staticmethod
    def get_grade_from_zlint(zlint_data: Dict) -> str:
        """Calculate grade based on zlint errors/warnings"""
        if not zlint_data or 'lints' not in zlint_data:
            return 'A'
        
        lints = zlint_data.get('lints', {})
        error_count = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
        warn_count = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
        
        if error_count >= 3:
            return 'F'
        elif error_count >= 2:
            return 'C'
        elif error_count >= 1:
            return 'B'
        elif warn_count >= 3:
            return 'B+'
        elif warn_count >= 1:
            return 'A-'
        else:
            return 'A+'
    
    @staticmethod
    def count_vulnerabilities(zlint_data: Dict) -> Dict[str, int]:
        """Count errors and warnings from zlint data"""
        if not zlint_data or 'lints' not in zlint_data:
            return {'errors': 0, 'warnings': 0}
        
        lints = zlint_data.get('lints', {})
        errors = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error')
        warnings = sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn')
        
        return {'errors': errors, 'warnings': warnings}
    
    @staticmethod
    def format_vulnerabilities(zlint_data: Dict) -> str:
        """Format vulnerabilities as display string"""
        counts = CertificateModel.count_vulnerabilities(zlint_data)
        if counts['errors'] > 0:
            return f"{counts['errors']} Critical"
        elif counts['warnings'] > 0:
            return f"{counts['warnings']} Warning"
        return "0 Found"
    
    @classmethod
    def build_filter_query(
        cls,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        countries: Optional[List[str]] = None,
        issuers: Optional[List[str]] = None,
        grades: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        validation_levels: Optional[List[str]] = None
    ) -> Dict:
        """
        Build MongoDB $match filter from query params.
        All filters are combined with AND logic.
        
        Date range uses overlap check:
        - Certificate is included if valid at ANY point during the range
        - Query: validFrom <= endDate AND validTo >= startDate
        """
        filters = []
        now = datetime.now(timezone.utc)
        
        # Date range filter - certificates where validity.end is within the range
        # User request: certificates ending within the date range (end_date between filter start and end)
        if start_date and end_date:
            try:
                start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                # Certificate's end date should be >= filter start AND <= filter end
                filters.append({
                    '$and': [
                        {'parsed.validity.end': {'$gte': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}},
                        {'parsed.validity.end': {'$lte': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ')}}
                    ]
                })
            except (ValueError, AttributeError):
                pass  # Invalid date format, skip filter
        
        # Country filter (derived from TLD)
        if countries and len(countries) > 0:
            # We'll filter on common_name TLD - need to use $where or compute in aggregation
            # For now, we'll skip and handle in aggregation stage
            pass
        
        # Issuer filter - OPTIMIZED to use indexed parsed.issuer_org_primary field
        if issuers and len(issuers) > 0:
            # Use the simpler indexed field for fast lookups
            filters.append({
                'parsed.issuer_org_primary': {'$in': issuers}
            })
        
        # Grade filter - needs to be computed, handled in specific methods
        # For now, store for reference
        
        # Status filter
        if statuses and len(statuses) > 0:
            status_filters = []
            for status in statuses:
                if status.upper() == 'VALID':
                    # Valid = not expired and not expiring soon (>30 days)
                    thirty_days = now + timedelta(days=30)
                    status_filters.append({
                        'parsed.validity.end': {'$gt': thirty_days.strftime('%Y-%m-%dT%H:%M:%SZ')}
                    })
                elif status.upper() == 'EXPIRED':
                    status_filters.append({
                        'parsed.validity.end': {'$lte': now.strftime('%Y-%m-%dT%H:%M:%SZ')}
                    })
                elif status.upper() == 'EXPIRING_SOON':
                    # Expiring in next 30 days
                    thirty_days = now + timedelta(days=30)
                    status_filters.append({
                        '$and': [
                            {'parsed.validity.end': {'$gt': now.strftime('%Y-%m-%dT%H:%M:%SZ')}},
                            {'parsed.validity.end': {'$lte': thirty_days.strftime('%Y-%m-%dT%H:%M:%SZ')}}
                        ]
                    })
                elif status.upper() == 'WEAK':
                    # Weak encryption - RSA key < 2048
                    status_filters.append({
                        '$and': [
                            {'parsed.subject_key_info.key_algorithm.name': 'RSA'},
                            {'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}}
                        ]
                    })
            if status_filters:
                filters.append({'$or': status_filters})
        
        # Validation level filter
        if validation_levels and len(validation_levels) > 0:
            # EV, OV, DV derived from policy identifiers or subject organization presence
            level_filters = []
            for level in validation_levels:
                if level.upper() == 'EV':
                    # EV certs have specific policy OIDs and extended validation
                    level_filters.append({
                        'parsed.extensions.certificate_policies': {'$exists': True}
                    })
                elif level.upper() == 'OV':
                    # OV certs have organization in subject
                    level_filters.append({
                        'parsed.subject.organization': {'$exists': True}
                    })
                elif level.upper() == 'DV':
                    # DV certs typically don't have organization
                    level_filters.append({
                        'parsed.subject.organization': {'$exists': False}
                    })
            if level_filters:
                filters.append({'$or': level_filters})
        
        # Combine all filters with AND
        if not filters:
            return {}
        elif len(filters) == 1:
            return filters[0]
        else:
            return {'$and': filters}
    
    @staticmethod
    def serialize_certificate(doc: Dict) -> Dict:
        """Serialize a certificate document for API response"""
        parsed = doc.get('parsed', {})
        validity = parsed.get('validity', {})
        subject = parsed.get('subject', {})
        issuer = parsed.get('issuer', {})
        key_info = parsed.get('subject_key_info', {})
        zlint = doc.get('zlint', {})
        extensions = parsed.get('extensions', {})
        
        # Use domain field directly from document, fallback to common_name
        domain = doc.get('domain', '')
        if not domain:
            domain = subject.get('common_name', ['Unknown'])[0] if subject.get('common_name') else 'Unknown'
        
        issuer_org = issuer.get('organization', ['Unknown'])[0] if issuer.get('organization') else 'Unknown'
        
        # Get key algorithm name and length
        algo_name = key_info.get('key_algorithm', {}).get('name', 'Unknown')
        key_length = 0
        if key_info.get('rsa_public_key'):
            key_length = key_info['rsa_public_key'].get('length', 0)
        elif key_info.get('ecdsa_public_key'):
            key_length = key_info['ecdsa_public_key'].get('length', 0)
        
        # Create full encryption type string (e.g., "RSA 2048 SHA-256")
        sig_algo = parsed.get('signature_algorithm', {}).get('name', '')
        if key_length:
            encryption_type = f"{algo_name} {key_length}"
            if sig_algo and 'SHA' in sig_algo.upper():
                encryption_type += f" {sig_algo.split('-')[-1] if '-' in sig_algo else sig_algo}"
        else:
            encryption_type = algo_name
        
        # Get validation level directly from parsed field
        validation_level = parsed.get('validation_level', 'DV')
        
        # Build zlintDetails - only include error/warn lints if present
        zlint_details = {}
        if zlint.get('errors_present', False) or zlint.get('warnings_present', False):
            lints = zlint.get('lints', {})
            for lint_name, lint_data in lints.items():
                if isinstance(lint_data, dict):
                    result = lint_data.get('result', '')
                    if result in ('error', 'warn'):
                        zlint_details[lint_name] = lint_data
        
        # Extract key usage flags
        key_usage = extensions.get('key_usage', {})
        key_usage_dict = {
            'digitalSignature': key_usage.get('digital_signature', False),
            'keyEncipherment': key_usage.get('key_encipherment', False),
            'dataEncipherment': key_usage.get('data_encipherment', False),
            'keyCertSign': key_usage.get('key_cert_sign', False),
            'crlSign': key_usage.get('crl_sign', False),
        } if key_usage else None
        
        # Extract extended key usage
        ext_key_usage = extensions.get('extended_key_usage', {})
        ext_key_usage_dict = {
            'serverAuth': ext_key_usage.get('server_auth', False),
            'clientAuth': ext_key_usage.get('client_auth', False),
            'codeSigning': ext_key_usage.get('code_signing', False),
            'emailProtection': ext_key_usage.get('email_protection', False),
        } if ext_key_usage else None
        
        # Get common name (first entry)
        common_name = subject.get('common_name', [''])[0] if subject.get('common_name') else ''
        
        # Get signature info
        signature = parsed.get('signature', {})
        is_self_signed = signature.get('self_signed', False)

        # Get public key details
        public_key = ''
        if key_info.get('rsa_public_key'):
            public_key = key_info['rsa_public_key'].get('modulus', '')
        elif key_info.get('ecdsa_public_key'):
            # For ECDSA, we might want x and y coordinates or just indicate ECDSA
            # For now, we'll try to get 'public_key' if it exists, or leave empty
            public_key = key_info['ecdsa_public_key'].get('public_key', '')
            
        spki_fingerprint = key_info.get('fingerprint_sha256', '')
        
        return {
            'id': str(doc.get('_id', '')),
            'domain': domain,
            'issuer': issuer_org,
            'issuerDn': parsed.get('issuer_dn', ''),
            'validFrom': validity.get('start', ''),
            'validTo': validity.get('end', ''),
            'status': CertificateModel.get_status(validity.get('end', '')),
            'grade': CertificateModel.get_grade_from_zlint(zlint),
            'encryptionType': encryption_type,
            'keyLength': key_length,
            'signatureAlgorithm': parsed.get('signature_algorithm', {}).get('name', 'Unknown'),
            'vulnerabilities': CertificateModel.format_vulnerabilities(zlint),
            'vulnerabilityCount': CertificateModel.count_vulnerabilities(zlint),
            'san': parsed.get('names', []),
            'country': CertificateModel.get_tld_country(domain),
            'scanDate': validity.get('start', ''),
            'validationLevel': validation_level,
            'zlintDetails': zlint_details if zlint_details else None,
            # Enhanced fields
            'commonName': common_name,
            'subjectDn': parsed.get('subject_dn', ''),
            'selfSigned': is_self_signed,
            'serialNumber': parsed.get('serial_number', ''),
            'fingerprintSha256': parsed.get('fingerprint_sha256', ''),
            'fingerprintSha1': parsed.get('fingerprint_sha1', ''),
            'fingerprintMd5': parsed.get('fingerprint_md5', ''),
            'validityLength': validity.get('length', 0),
            'isCa': extensions.get('basic_constraints', {}).get('is_ca', False),
            'keyUsage': key_usage_dict,
            'extendedKeyUsage': ext_key_usage_dict,
            'crlDistributionPoints': extensions.get('crl_distribution_points', []),
            'authorityInfoAccess': extensions.get('authority_info_access', {}).get('issuer_urls', []),
            'publicKey': public_key,
            'spkiFingerprint': spki_fingerprint,
            'spkiSubjectFingerprint': doc.get('spki_subject_fingerprint', ''),
        }
    
    @classmethod
    def get_all(cls, page: int = 1, page_size: int = 10, 
                status: Optional[str] = None, 
                country: Optional[str] = None,
                issuer: Optional[str] = None,
                search: Optional[str] = None,
                encryption_type: Optional[str] = None,
                has_vulnerabilities: Optional[bool] = None,
                expiring_month: Optional[int] = None,
                expiring_year: Optional[int] = None,
                expiring_days: Optional[int] = None,
                validity_bucket: Optional[str] = None,
                issued_month: Optional[int] = None,
                issued_year: Optional[int] = None,
                issued_within_days: Optional[int] = None,
                # New Signature/Hash page filters
                signature_algorithm: Optional[str] = None,
                weak_hash: Optional[bool] = None,
                self_signed: Optional[bool] = None,
                key_size: Optional[int] = None,
                hash_type: Optional[str] = None,
                # SAN Analytics page filters
                san_tld: Optional[str] = None,
                san_type: Optional[str] = None,
                san_count_min: Optional[int] = None,
                san_count_max: Optional[int] = None,
                expiring_start: Optional[str] = None,
                expiring_end: Optional[str] = None,
                # Shared Keys page filter
                shared_key: Optional[bool] = None,
                base_filter: Optional[Dict] = None) -> Dict:
        """Get paginated list of certificates with optional filters
        
        Args:
            expiring_days: Filter for certs expiring within N days (e.g., 30, 60, 90)
            validity_bucket: Filter by validity period bucket (e.g., "0-90", "90-365", "365-730", "730+")
            issued_month: Filter by issuance month (1-12)
            issued_year: Filter by issuance year (e.g., 2025)
            issued_within_days: Filter for certs issued within N days (e.g., 30)
            signature_algorithm: Filter by exact signature algorithm (e.g., "SHA256-RSA")
            weak_hash: Filter certs with weak hash (MD5, SHA-1)
            self_signed: Filter self-signed certificates
            key_size: Filter by exact key size (e.g., 2048, 4096)
            hash_type: Filter by hash algorithm (e.g., "SHA-256", "SHA-1")
            san_tld: Filter by TLD in SAN entries (e.g., ".com", ".pk")
            san_type: Filter by SAN type ("wildcard" or "standard")
            san_count_min: Filter by minimum SAN count
            san_count_max: Filter by maximum SAN count
            expiring_start: Filter by exact expiration start date (ISO string)
            expiring_end: Filter by exact expiration end date (ISO string)
            shared_key: Filter for certs involved in true key reuse (different certs sharing same public key)
            base_filter: Global filter query from build_filter_query() - merged with specific filters
        """
        
        now = cls.get_current_time_iso()
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Build query based on filters
        query = {}
        
        # Apply base filter from global filters (date range, etc)
        if base_filter:
            query = base_filter.copy()
        
        if search:
            # ⚡ OPTIMIZED: Use MongoDB text search index instead of regex
            # Text index (idx_text_search) enables fast full-text search
            query['$text'] = {'$search': search}
        
        if issuer:
            if issuer.lower() == 'others':
                # Get top 10 CAs and exclude them using $nin
                top_ca_pipeline = [
                    {'$project': {
                        'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
                    }},
                    {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
                    {'$group': {
                        '_id': '$issuer_org',
                        'count': {'$sum': 1}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 10}
                ]
                top_cas = [r['_id'] for r in cls.collection.aggregate(top_ca_pipeline)]
                # Match certificates where issuer is NOT in top 10
                query['$and'] = query.get('$and', [])
                query['$and'].append({
                    '$or': [
                        {'parsed.issuer.organization': {'$nin': top_cas}},
                        {'parsed.issuer.organization': {'$exists': False}}
                    ]
                })
            else:
                # FIX: Use the actual issuer.organization field that exists in the database
                # parsed.issuer.organization is an array, so we use $in to match any element
                query['parsed.issuer.organization'] = {'$in': [issuer]}
        
        # Apply status filter - VALID includes ALL non-expired certificates
        if status:
            status_upper = status.upper()
            if status_upper == 'EXPIRED':
                query['parsed.validity.end'] = {'$lt': now}
            elif status_upper == 'EXPIRING_SOON':
                query['parsed.validity.end'] = {'$gte': now, '$lte': now_plus_30}
            elif status_upper == 'VALID':
                # VALID = ALL non-expired certificates (includes expiring_soon)
                query['parsed.validity.end'] = {'$gt': now}
        
        # Filter by encryption type (e.g., "RSA 2048", "ECDSA 256")
        if encryption_type:
            parts = encryption_type.split()
            if len(parts) >= 1:
                algo_name = parts[0]
                query['parsed.subject_key_info.key_algorithm.name'] = algo_name
                if len(parts) >= 2:
                    try:
                        key_length = int(parts[1])
                        # Check both RSA and ECDSA key length fields
                        if algo_name.upper() == 'RSA':
                            query['parsed.subject_key_info.rsa_public_key.length'] = key_length
                        elif algo_name.upper() in ['ECDSA', 'EC']:
                            query['parsed.subject_key_info.ecdsa_public_key.length'] = key_length
                    except ValueError:
                        pass
        
        # Filter by exact signature algorithm (e.g., "SHA256-RSA", "ECDSA-SHA256")
        if signature_algorithm:
            query['parsed.signature_algorithm.name'] = signature_algorithm
        
        # Filter by weak hash (SHA-1, MD5) - for Weak Hash Alert card
        if weak_hash:
            query['$or'] = query.get('$or', [])
            if not query['$or']:
                query['$or'] = [
                    {'parsed.signature_algorithm.name': {'$regex': '^SHA1|^SHA-1', '$options': 'i'}},
                    {'parsed.signature_algorithm.name': {'$regex': '^MD5', '$options': 'i'}}
                ]
        
        # Filter by self-signed certificates
        if self_signed:
            query['parsed.signature.self_signed'] = True
        
        # Filter by exact key size (e.g., 2048, 4096)
        if key_size:
            query['$or'] = query.get('$or', [])
            if not query['$or']:
                query['$or'] = [
                    {'parsed.subject_key_info.rsa_public_key.length': key_size},
                    {'parsed.subject_key_info.ecdsa_public_key.length': key_size}
                ]
        
        # Filter by hash type (e.g., "SHA-256", "SHA-1")
        if hash_type:
            # Map hash type to regex pattern for signature_algorithm.name
            hash_patterns = {
                'SHA-256': '^SHA256',
                'SHA-384': '^SHA384',
                'SHA-512': '^SHA512',
                'SHA-1': '^SHA1|^SHA-1',
                'MD5': '^MD5'
            }
            pattern = hash_patterns.get(hash_type, f'^{hash_type.replace("-", "")}')
            query['parsed.signature_algorithm.name'] = {'$regex': pattern, '$options': 'i'}
        
        # Filter by expiring month/year - get certs that expire/expired in that month
        if expiring_month and expiring_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(expiring_year, expiring_month)
            month_start = f"{expiring_year}-{expiring_month:02d}-01T00:00:00Z"
            month_end = f"{expiring_year}-{expiring_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.end'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by custom expiration range (e.g. for weekly view)
        if expiring_start and expiring_end:
            # If both month filter and range filter are present, range takes precedence
            # or we could combine them, but range is usually more specific
            query['parsed.validity.end'] = {'$gte': expiring_start, '$lte': expiring_end}
        
        # Filter by issued month/year - get certs that were issued (validFrom) in that month
        if issued_month and issued_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(issued_year, issued_month)
            month_start = f"{issued_year}-{issued_month:02d}-01T00:00:00Z"
            month_end = f"{issued_year}-{issued_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.start'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by issued within N days (for "Issued (30d)" card click)
        if issued_within_days:
            now_dt = datetime.now(timezone.utc)
            past_date = (now_dt - timedelta(days=issued_within_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Certificates with validity start date within the last N days
            query['parsed.validity.start'] = {
                '$gte': past_date,  # Issued within last N days
                '$lte': now  # Up to now
            }
        
        # Filter by expiring within N days (distinct from 30-day expiring_soon status)
        if expiring_days:
            now_dt = datetime.now(timezone.utc)
            target_date = (now_dt + timedelta(days=expiring_days)).strftime('%Y-%m-%dT%H:%M:%SZ')
            # Override any existing validity.end filter
            query['parsed.validity.end'] = {
                '$gt': now,  # Not yet expired
                '$lte': target_date  # Within expiring_days window
            }
        
        # Filter by validity period bucket (duration in days)
        # ✅ OPTIMIZED: Use pre-computed validity.length field instead of date parsing
        if validity_bucket:
            # Extract min/max days from bucket string
            # Buckets: "0-90", "90-365", "365-730", "730+"
            bucket_ranges = {
                '0-90': (0, 90),
                '90-365': (90, 365),
                '365-730': (365, 730),
                '730+': (730, 100000)
            }
            if validity_bucket in bucket_ranges:
                min_days, max_days = bucket_ranges[validity_bucket]
                # Convert days to seconds (validity.length is in seconds)
                min_seconds = min_days * 86400
                max_seconds = max_days * 86400
                
                # Use direct query on validity.length field (pre-computed in DB)
                # This is MUCH faster than date parsing aggregation
                query['parsed.validity.length'] = {
                    '$gte': min_seconds,
                    '$lt': max_seconds
                }
        
        # Handle has_vulnerabilities with OPTIMIZED query using boolean flag
        if has_vulnerabilities:
            # Use the zlint.errors_present boolean flag for fast indexed lookup
            # This is the same approach as Global Health / Active Certs - FAST
            vuln_query = {'zlint.errors_present': True}
            
            # Get total count - simple indexed query
            total = cls.collection.count_documents(vuln_query)
            
            # Get paginated results - simple find with skip/limit
            skip = (page - 1) * page_size
            cursor = cls.collection.find(vuln_query).skip(skip).limit(page_size)
            
            certificates = []
            for doc in cursor:
                cert = cls.serialize_certificate(doc)
                certificates.append(cert)
            
            return {
                'certificates': certificates,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': max(1, (total + page_size - 1) // page_size)
                }
            }
        
        # ⚡ OPTIMIZED: Handle country filter using pre-computed certificate IDs
        # PERFORMANCE: 110 seconds → 0.1 seconds (1,100x faster!)
        if country:
            print(f"[COUNTRY FILTER] Using pre-computed IDs for: {country}")
            try:
                # Get certificate IDs from pre-computed collection
                country_collection = MongoDBClient.get_results_db()['geographic-distribution-1']
                country_doc = country_collection.find_one({'_id': country})
                
                if not country_doc:
                    print(f"[COUNTRY FILTER] No pre-computed data for: {country}")
                    # Fall back to empty result
                    return {
                        'certificates': [],
                        'pagination': {
                            'page': page,
                            'pageSize': page_size,
                            'total': 0,
                            'totalPages': 0
                        }
                    }
                
                # Get all certificate IDs for this country
                cert_ids = country_doc.get('certificate_ids', [])
                total = len(cert_ids)
                
                print(f"[COUNTRY FILTER] Found {total} certificates for {country}")
                
                # Paginate certificate IDs
                skip = (page - 1) * page_size
                page_ids = cert_ids[skip:skip + page_size]
                
                # Fetch full certificates by ID (FAST - indexed lookup!)
                certificates = []
                for doc in cls.collection.find({'_id': {'$in': page_ids}}):
                    cert = cls.serialize_certificate(doc)
                    certificates.append(cert)
                
                return {
                    'certificates': certificates,
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': total,
                        'totalPages': max(1, (total + page_size - 1) // page_size)
                    }
                }
                
            except Exception as e:
                print(f"[COUNTRY FILTER] Error accessing pre-computed data: {e}")
                # Fall back to empty result rather than slow regex
                return {
                    'certificates': [],
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'totalPages': 0
                    }
                }
        
        # SAN TLD filter - filter certs where any dns_name ends with the TLD
        if san_tld:
            # Remove leading dot if present for regex
            tld_pattern = san_tld.lstrip('.')
            # Match dns_names ending with the TLD
            query['parsed.extensions.subject_alt_name.dns_names'] = {
                '$regex': f'\\.{tld_pattern}$',
                '$options': 'i'
            }
        
        # SAN type filter - filter by wildcard or standard SANs
        if san_type:
            if san_type.lower() == 'wildcard':
                # Match certs with at least one wildcard SAN (starts with *.)
                query['parsed.extensions.subject_alt_name.dns_names'] = {
                    '$regex': '^\\*\\.',
                    '$options': 'i'
                }
            elif san_type.lower() == 'standard':
                # Match certs where no SAN starts with *. 
                # This is trickier - we'll use $not to exclude wildcards
                query['$and'] = query.get('$and', [])
                query['$and'].append({
                    'parsed.extensions.subject_alt_name.dns_names': {
                        '$exists': True,
                        '$ne': []
                    }
                })
                query['$and'].append({
                    'parsed.extensions.subject_alt_name.dns_names': {
                        '$not': {'$regex': '^\\*\\.'}
                    }
                    
                    })
        
        # ⚡ OPTIMIZED: Shared key filter - use pre-computed materialized view
        # Previously this ran a 2-minute aggregation on every request
        if shared_key:
            try:
                # Get shared key fingerprints from pre-computed materialized view
                shared_groups_collection = MongoDBClient.get_results_db()['shared-keys-groups']
                
                # Get all shared key fingerprints (excluding metadata doc)
                shared_fingerprints = list(shared_groups_collection.find(
                    {'_id': {'$ne': 'metadata'}},
                    {'_id': 1}
                ))
                
                shared_fingerprints = [doc['_id'] for doc in shared_fingerprints]
            except Exception:
                # Fallback to original slow method if materialized view not available
                # (This should only happen if compute_shared_keys.py hasn't been run)
                shared_keys_pipeline = [
                    {'$match': {
                        'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
                        'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
                    }},
                    {'$group': {
                        '_id': '$parsed.subject_key_info.fingerprint_sha256',
                        'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'}
                    }},
                    {'$addFields': {
                        'distinct_certs': {'$size': '$cert_fingerprints'}
                    }},
                    {'$match': {'distinct_certs': {'$gt': 1}}},
                    {'$project': {'_id': 1}}
                ]
                
                shared_fingerprints = [r['_id'] for r in cls.collection.aggregate(shared_keys_pipeline, allowDiskUse=True)]
            
            if shared_fingerprints:
                # Filter certs to only those with shared public keys
                if '$and' not in query:
                    query['$and'] = []
                query['$and'].append({
                    'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
                })
            else:
                # No shared keys found, return empty result
                return {
                    'certificates': [],
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'totalPages': 0
                    }
                }
        
        # SAN count filter - filter by number of SANs (dns_names array size)
        if san_count_min is not None or san_count_max is not None:
            # Use aggregation pipeline for array size filtering
            pipeline = [
                {'$match': query if query else {}},
                # Add a field for the count of dns_names
                {'$addFields': {
                    'sanCount': {
                        '$size': {'$ifNull': ['$parsed.extensions.subject_alt_name.dns_names', []]}
                    }
                }},
            ]
            
            # Build match condition for san count
            san_count_match = {}
            if san_count_min is not None:
                san_count_match['$gte'] = san_count_min
            if san_count_max is not None:
                san_count_match['$lte'] = san_count_max
            
            if san_count_match:
                pipeline.append({'$match': {'sanCount': san_count_match}})
            
            # Get total count first
            count_pipeline = pipeline + [{'$count': 'total'}]
            count_result = list(cls.collection.aggregate(count_pipeline, allowDiskUse=True))
            total = count_result[0]['total'] if count_result else 0
            
            # Get paginated results
            skip = (page - 1) * page_size
            result_pipeline = pipeline + [
                {'$skip': skip},
                {'$limit': page_size}
            ]
            
            certificates = []
            for doc in cls.collection.aggregate(result_pipeline, allowDiskUse=True):
                cert = cls.serialize_certificate(doc)
                certificates.append(cert)
            
            return {
                'certificates': certificates,
                'pagination': {
                    'page': page,
                    'pageSize': page_size,
                    'total': total,
                    'totalPages': max(1, (total + page_size - 1) // page_size)
                }
            }
        
        # Get total count with filters applied
        # ✅ OPTIMIZATION: Use estimated_document_count() when query is empty (878K docs)
        if not query or query == {}:
            total = cls.collection.estimated_document_count()
        elif issuer and not search and issuer.lower() != 'others':
            # ULTRA-FAST: Get count from pre-computed CA analytics for exact issuer matches
            # This avoids expensive count operations on large result sets
            try:
                ca_analytics = MongoDBClient.get_results_db()['ca-analytics']
                ca_doc = ca_analytics.find_one({'name': issuer})
                print("before if condition")
                if ca_doc:
                    print("hello in if codition")
                    total = ca_doc['count']
                else:
                    print("hello in else codition")
                    # Fallback to aggregation count if not in pre-computed data
                    pipeline = [{'$match': query}, {'$count': 'total'}]
                    count_result = list(cls.collection.aggregate(pipeline))
                    total = count_result[0]['total'] if count_result else 0
            except Exception as e:
                # Fallback to standard count on error
                total = cls.collection.count_documents(query)
        else:
            total = cls.collection.count_documents(query)
        
        # Get paginated results
        # ✅ OPTIMIZATION: Sort by _id (indexed) for fast pagination
        # When using issuer filter, skip sort to avoid expensive in-memory sort operation
        skip = (page - 1) * page_size
        if search:
            # Text search: MongoDB automatically uses text index, no hint needed
            cursor = cls.collection.find(query).sort('_id', 1).skip(skip).limit(page_size)
        elif issuer:
            # Issuer filter: Return results in natural order to avoid expensive in-memory sort
            # MongoDB would have to sort 339K+ documents if we add sort here
            # Better to return results in natural order (insertion order)
            cursor = cls.collection.find(query).skip(skip).limit(page_size)
        else:
            # Regular query: Use hint to optimize with _id index
            cursor = cls.collection.find(query).sort('_id', 1).hint('_id_').skip(skip).limit(page_size)
        
        certificates = []
        for doc in cursor:
            cert = cls.serialize_certificate(doc)
            certificates.append(cert)
        
        return {
            'certificates': certificates,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'totalPages': max(1, (total + page_size - 1) // page_size)
            }
        }
    
    @classmethod
    def get_by_id(cls, cert_id: str) -> Optional[Dict]:
        """Get single certificate by ID"""
        try:
            doc = cls.collection.find_one({'_id': ObjectId(cert_id)})
            if doc:
                return cls.serialize_certificate(doc)
            return None
        except Exception as e:
            print(f"Error getting certificate by ID: {e}")
            return None
    
    
    @classmethod
    def get_unique_filters(cls) -> Dict:
        """Get unique values for filter dropdowns"""
        # Get unique issuers
        issuer_pipeline = [
            {'$unwind': '$parsed.issuer.organization'},
            {'$group': {'_id': '$parsed.issuer.organization'}},
            {'$sort': {'_id': 1}},
            {'$limit': 50}
        ]
        issuers = [doc['_id'] for doc in cls.collection.aggregate(issuer_pipeline)]
        
        # Get unique countries from domains (TLDs)
        domain_pipeline = [
            {'$unwind': '$parsed.subject.common_name'},
            {'$group': {'_id': '$parsed.subject.common_name'}},
            {'$limit': 1000}
        ]
        domains = [doc['_id'] for doc in cls.collection.aggregate(domain_pipeline)]
        
        countries = list(set(cls.get_tld_country(d) for d in domains if d))
        countries = [c for c in countries if c != 'Unknown']
        countries.sort()
        
        return {
            'issuers': issuers,
            'countries': countries,
            'statuses': ['VALID', 'EXPIRED', 'EXPIRING_SOON', 'WEAK'],
            'grades': ['A+', 'A', 'A-', 'B+', 'B', 'C', 'D', 'F'],
            'validationLevels': ['DV', 'OV', 'EV']
        }
    
    @classmethod
    def get_encryption_strength(cls, base_filter: Optional[Dict] = None) -> List[Dict]:
        """Get encryption algorithm distribution with EXACT counts using compound indexes
        
        This method uses count_documents() with COMPOUND INDEX hints:
        - idx_algo_rsa_length: (algorithm.name + rsa_public_key.length)
        - idx_algo_ecdsa_length: (algorithm.name + ecdsa_public_key.length)
        
        These compound indexes make each count query SUPER FAST (0.1s instead of 33s!)
        Same pattern as global-health API: multiple count_documents() calls.
        
        Args:
            base_filter: Global filter query (domain, issuer, etc.)
        
        Returns:
            List of dicts with algorithm name, type, count, and percentage
        """
        import time
        start = time.time()
        
        print("[ENCRYPTION] Starting exact count queries with compound indexes...")
        
        # Get total count first (fast)
        if base_filter:
            total = cls.collection.count_documents(base_filter)
        else:
            total = cls.collection.estimated_document_count()
        
        if total == 0:
            return []
        
        # Prepare base filter for all queries
        base_query = base_filter.copy() if base_filter else {}
        
        # Define all algorithm + key length combinations we want to count
        # Each has its specific compound index for MAXIMUM speed!
        algorithms_to_count = [
            # RSA variants - use idx_algo_rsa_length
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 2048, 'display': 'RSA 2048', 'hint': 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 4096, 'display': 'RSA 4096', 'hint': 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 3072, 'display': 'RSA 3072', 'hint': 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 1024, 'display': 'RSA 1024', 'hint': 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 8192, 'display': 'RSA 8192', 'hint': 'idx_algo_rsa_length'},
            
            # ECDSA variants - use idx_algo_ecdsa_length
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 256, 'display': 'ECDSA 256', 'hint': 'idx_algo_ecdsa_length'},
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 384, 'display': 'ECDSA 384', 'hint': 'idx_algo_ecdsa_length'},
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 521, 'display': 'ECDSA 521', 'hint': 'idx_algo_ecdsa_length'},
        ]
        
        # Execute count queries with compound index hints
        encryption_counts = []
        for config in algorithms_to_count:
            t_start = time.time()
            
            # Build query: algorithm name AND key length
            query = base_query.copy()
            query['parsed.subject_key_info.key_algorithm.name'] = config['algo']
            query[f"parsed.subject_key_info.{config['field']}"] = config['length']
            
            # Count with COMPOUND index hint - this is the KEY to speed!
            count = cls.collection.count_documents(
                query,
                hint=config['hint']  # Use the compound index
            )
            
            if count > 0:  # Only include if we have certificates
                encryption_counts.append({
                    'algo': config['algo'],
                    'display': config['display'],
                    'count': count
                })
                print(f"[ENCRYPTION] {config['display']}: {count} certs ({time.time()-t_start:.3f}s)")
        
        # Sort by count descending
        encryption_counts.sort(key=lambda x: x['count'], reverse=True)
        
        # Color mapping based on encryption type
        type_colors = {
            'RSA': '#3b82f6',      # Blue
            'ECDSA': '#10b981',    # Green
            'EC': '#10b981',       # Green
            'DSA': '#ef4444',      # Red (deprecated)
        }
        
        type_labels = {
            'RSA': 'Standard',
            'ECDSA': 'Modern',
            'EC': 'Modern',
            'DSA': 'Deprecated',
        }
        
        # Format results
        encryption_data = []
        for i, item in enumerate(encryption_counts[:10]):  # Top 10
            algo = item['algo']
            encryption_data.append({
                'id': f'enc-{i}',
                'name': item['display'],
                'type': type_labels.get(algo, 'Standard'),
                'count': item['count'],
                'percentage': round((item['count'] / total) * 100, 1),
                'color': type_colors.get(algo, '#6b7280')
            })
        
        elapsed = time.time() - start
        print(f"[ENCRYPTION] ✅ Completed ALL exact counts in {elapsed:.2f}s")
        
        return encryption_data
    
   
    
    # ============================================================
    # COMMENT FOR NOTIFICATION ICON - Backend Method
    # ============================================================
    # @classmethod
    # def get_notifications(cls) -> Dict:
    #     """
    #     Get real-time notification data based on certificate status.
    #     Uses efficient aggregation for counting.
    #     """
    #     from datetime import datetime, timezone, timedelta
    #     
    #     now = datetime.now(timezone.utc)
    #     now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    #     plus_2_days = (now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
    #     plus_7_days = (now + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
    #     yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    #     
    #     # Use $facet for efficient multi-aggregation in single query
    #     pipeline = [
    #         {'$facet': {
    #             'expiring_2_days': [
    #                 {'$match': {
    #                     'parsed.validity.end': {'$gte': now_str, '$lte': plus_2_days}
    #                 }},
    #                 {'$count': 'count'}
    #             ],
    #             'expiring_7_days': [
    #                 {'$match': {
    #                     'parsed.validity.end': {'$gte': now_str, '$lte': plus_7_days}
    #                 }},
    #                 {'$count': 'count'}
    #             ],
    #             'vulnerabilities': [
    #                 {'$match': {
    #                     'zlint.errors_present': True,
    #                     'parsed.validity.end': {'$gt': now_str}
    #                 }},
    #                 {'$count': 'count'}
    #             ],
    #             'weak_encryption': [
    #                 {'$match': {
    #                     'parsed.subject_key_info.key_algorithm.name': 'RSA',
    #                     'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}
    #                 }},
    #                 {'$count': 'count'}
    #             ],
    #             'newly_expired': [
    #                 {'$match': {
    #                     'parsed.validity.end': {'$gte': yesterday, '$lt': now_str}
    #                 }},
    #                 {'$count': 'count'}
    #             ]
    #         }}
    #     ]
    #     
    #     result = list(cls.collection.aggregate(pipeline))
    #     
    #     if not result:
    #         return {'notifications': [], 'unreadCount': 0, 'totalCount': 0}
    #     
    #     facet_result = result[0]
    #     
    #     # Extract counts (default to 0 if empty)
    #     def get_count(key: str) -> int:
    #         arr = facet_result.get(key, [])
    #         return arr[0]['count'] if arr else 0
    #     
    #     expiring_2_days = get_count('expiring_2_days')
    #     expiring_7_days = get_count('expiring_7_days')
    #     vulnerabilities = get_count('vulnerabilities')
    #     weak_encryption = get_count('weak_encryption')
    #     newly_expired = get_count('newly_expired')
    #     
    #     notifications = []
    #     timestamp = now.isoformat()
    #     
    #     # Build notification list (only add if count > 0)
    #     if expiring_2_days > 0:
    #         notifications.append({
    #             'id': 'expiring-2-days',
    #             'type': 'error',
    #             'category': 'expiring',
    #             'title': f'{expiring_2_days} certificate{"s" if expiring_2_days > 1 else ""} expiring in 1-2 days',
    #             'description': 'Immediate attention required',
    #             'count': expiring_2_days,
    #             'filterParams': {'status': 'EXPIRING_SOON', 'days': 2},
    #             'timestamp': timestamp,
    #             'read': False
    #         })
    #     
    #     if expiring_7_days > expiring_2_days:  # Exclude already counted 2-day ones
    #         remaining = expiring_7_days - expiring_2_days
    #         if remaining > 0:
    #             notifications.append({
    #                 'id': 'expiring-7-days',
    #                 'type': 'warning',
    #                 'category': 'expiring',
    #                 'title': f'{remaining} certificate{"s" if remaining > 1 else ""} expiring in 3-7 days',
    #                 'description': 'Plan renewal soon',
    #                 'count': remaining,
    #                 'filterParams': {'status': 'EXPIRING_SOON', 'days': 7},
    #                 'timestamp': timestamp,
    #                 'read': False
    #             })
    #     
    #     if vulnerabilities > 0:
    #         notifications.append({
    #             'id': 'vulnerabilities',
    #             'type': 'error',
    #             'category': 'security',
    #             'title': f'{vulnerabilities} certificate{"s" if vulnerabilities > 1 else ""} with vulnerabilities',
    #             'description': 'ZLint detected security issues',
    #             'count': vulnerabilities,
    #             'filterParams': {'has_vulnerabilities': True},
    #             'timestamp': timestamp,
    #             'read': False
    #         })
    #     
    #     if weak_encryption > 0:
    #         notifications.append({
    #             'id': 'weak-encryption',
    #             'type': 'warning',
    #             'category': 'security',
    #             'title': f'{weak_encryption} certificate{"s" if weak_encryption > 1 else ""} with weak encryption',
    #             'description': 'RSA key length below 2048 bits',
    #             'count': weak_encryption,
    #             'filterParams': {'encryption_type': 'RSA weak'},
    #             'timestamp': timestamp,
    #             'read': False
    #         })
    #     
    #     if newly_expired > 0:
    #         notifications.append({
    #             'id': 'newly-expired',
    #             'type': 'error',
    #             'category': 'expired',
    #             'title': f'{newly_expired} certificate{"s" if newly_expired > 1 else ""} expired recently',
    #             'description': 'Expired in the last 24 hours',
    #             'count': newly_expired,
    #             'filterParams': {'status': 'EXPIRED'},
    #             'timestamp': timestamp,
    #             'read': False
    #         })
    #     
    #     return {
    #         'notifications': notifications,
    #         'unreadCount': len(notifications),
    #         'totalCount': len(notifications)
    #     }
    pass
    
    # ----- New implementation for Signature and Hashes starts here -----
       
    @classmethod
    def get_validation_distribution(cls) -> List[Dict]:
        """
        Get validation level distribution (DV, OV, EV).
        """
        total_certs = cls.collection.count_documents({})
        
        pipeline = [
            {'$group': {'_id': '$parsed.validation_level', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline))
        
        distribution = []
        for item in results:
            level = item['_id'] or 'Unknown'
            count = item['count']
            percentage = round((count / total_certs) * 100, 1) if total_certs > 0 else 0
            distribution.append({
                'level': level,
                'count': count,
                'percentage': percentage
            })
        
        return distribution

    # ==================== Shared METHODS ====================


    # ===========================
    # Slow and fast Shared METHODS  (using on-the-fly aggregation)  
    # ===========================
    @staticmethod
    def get_current_time_iso() -> str:
        """Get current time in ISO format for MongoDB queries"""
        return SharedModels.get_current_time_iso()
    
    @staticmethod
    def get_tld_country(domain: str) -> str:
        return SharedModels.get_tld_country(domain=domain)
    
    @classmethod
    def get_ca_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        return SharedModels.get_ca_distribution(limit=limit, base_filter=base_filter)

    @classmethod
    def get_ca_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        return SharedModels.get_ca_distribution_fast(limit=limit, base_filter=base_filter)

    @classmethod
    def get_validity_trends(cls, months_before: int = 4, months_after: int = 4, granularity: str = 'monthly') -> List[Dict]:
        return SharedModels.get_validity_trends(months_before, months_after, granularity)
   
    @classmethod
    def get_dashboard_metrics(cls) -> Dict:
        return SharedModels.get_dashboard_metrics()
       
    @classmethod
    def get_geographic_distribution_fast(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        return SharedModels.get_geographic_distribution_fast(limit=limit, base_filter=base_filter)
        
    @classmethod
    def get_geographic_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        return SharedModels.get_geographic_distribution(limit=limit, base_filter=base_filter)
    

    # ==================== Validity analysis METHODS ====================

    # ===========================
    # Fast Validity analysis METHODS  (using pre-computed statistics) 
    # ===========================
    
    @classmethod
    def get_validity_stats_fast(cls) -> Dict:
        return ValidityModels.get_validity_stats_fast()
    
    @classmethod
    def get_validity_distribution_fast(cls) -> list:
        return ValidityModels.get_validity_distribution_fast()
    
    @classmethod
    def get_issuance_timeline_fast(cls, months: int = 12) -> list:
        return ValidityModels.get_issuance_timeline_fast(months=months)
    
     # ===========================
    # Slow Validity analysis METHODS  (using on-the-fly aggregation)
    # ===========================

    @classmethod
    def get_validity_stats(cls) -> Dict:
        return ValidityModels.get_validity_stats()
    
    @classmethod
    def get_validity_distribution(cls) -> List[Dict]:
        return ValidityModels.get_validity_distribution()
    
    @classmethod
    def get_issuance_timeline(cls, months: int = 12) -> List[Dict]:
        return ValidityModels.get_issuance_timeline(months=months)


    # ==================== SIGNATURE AND HASH METHODS ====================

    # ===========================
    # Fast signature and hash METHODS  (using pre-computed statistics) 
    # ===========================

    @classmethod
    def get_signature_stats_fast(cls) -> Dict:
        """
        Get comprehensive signature and hash statistics (OPTIMIZED - reads from pre-computed data).
        
        PERFORMANCE:
        - Source: tranco-latest-8-lakh-results.signature-stats (1 document)
        - Response time: ~0.005 seconds (3,000x faster than original)
        - Original time: ~180 seconds (full aggregation on 878K docs)
        
        Returns pre-computed:
            - algorithmDistribution: signature algorithm counts/percentages
            - hashDistribution: hash algorithm counts/percentages
            - keySizeDistribution: key size counts/percentages
            - weakHashCount: count of MD5/SHA-1 certs
            - hashComplianceRate: % using SHA-256+
            - strengthScore: composite security score 0-100
            - selfSignedCount: count of self-signed certs
            - totalCertificates: total count
        """
        return SignatureHashModel.get_signature_stats_fast()
    
    @classmethod
    def get_hash_trends_fast(cls, months: int = 36, granularity: str = 'quarterly') -> List[Dict]:
        """
        Get hash algorithm adoption trends over time (OPTIMIZED - reads from pre-computed data).
        
        PERFORMANCE:
        - Source: tranco-latest-8-lakh-results.hash-trends (~36-48 documents)
        - Response time: ~0.003 seconds (3,000x faster than original)
        - Original time: ~200 seconds (full aggregation on 878K docs)
        
        Args:
            months: Number of months to look back (default 36 = 3 years)
            granularity: 'quarterly' or 'yearly'
        
        Returns:
            List of dicts with period and hash percentages
        """
        return SignatureHashModel.get_hash_trends_fast(months=months, granularity=granularity)
    
    @classmethod
    def get_issuer_algorithm_matrix_fast(cls, limit: int = 10) -> List[Dict]:
        """
        Get matrix of issuer × algorithm combinations (OPTIMIZED - reads from pre-computed data).
        
        PERFORMANCE:
        - Source: tranco-latest-8-lakh-results.issuer-algorithm-matrix (~50 documents)
        - Response time: ~0.002 seconds (3,000x faster than original)
        - Original time: ~180 seconds (full aggregation on 878K docs)
        
        Args:
            limit: Maximum number of combinations to return (default 10)
        
        Returns:
            List of dicts with issuer, algorithm, keySize, and count
        """
        return SignatureHashModel.get_issuer_algorithm_matrix_fast(limit=limit)
    
    # ===========================
    # Slow Signature and hash METHODS  (using on-the-fly aggregation)  
    # ===========================

    @classmethod
    def get_signature_stats(cls) -> Dict:
        """
        Get comprehensive signature and hash statistics for the Signature & Hashes page.
        
        OPTIMIZED for millions of documents:
        - Uses efficient $group aggregations (single pass)
        - No $unwind or expensive operations
        - Minimal projections
        - Parallel counting for simple metrics
        
        Returns:
            - algorithmDistribution: signature algorithm counts/percentages
            - hashDistribution: hash algorithm counts/percentages
            - keySizeDistribution: key size counts/percentages
            - weakHashCount: count of MD5/SHA-1 certs
            - hashComplianceRate: % using SHA-256+
            - strengthScore: composite security score 0-100
            - selfSignedCount: count of self-signed certs
            - totalCertificates: total count
        """
        
        # Get total count (fast indexed query)
        return SignatureHashModel.get_signature_stats()
    
    @classmethod
    def get_hash_trends(cls, months: int = 36, granularity: str = 'quarterly') -> List[Dict]:
        """
        Get hash algorithm adoption trends over time based on issuance dates.
        
        OPTIMIZED for millions of documents:
        - Uses $match with date range first (uses index)
        - Single aggregation pass
        - Groups by period + hash in one operation
        
        Args:
            months: Number of months to look back (default 36 = 3 years)
            granularity: 'quarterly' or 'yearly'
        
        Returns:
            List of dicts with period and hash percentages
        """
        return SignatureHashModel.get_hash_trends(months=months, granularity=granularity)
    
    @classmethod
    def get_issuer_algorithm_matrix(cls, limit: int = 10) -> List[Dict]:
        """
        Get matrix of issuer × algorithm combinations with counts.
        
        OPTIMIZED for millions of documents:
        - Single pass aggregation
        - $group on compound key
        - Limited to top issuers
        
        Returns:
            List of dicts with issuer, algorithm, keySize, and count
        """
        
        return SignatureHashModel.get_issuer_algorithm_matrix(limit=limit)
 

    # ==================== CA ANALYTICS METHODS ====================


    # ===========================
    # Slow CA METHODS  (using on-the-fly aggregation)  
    # ===========================

    @classmethod
    def get_ca_stats(cls) -> Dict:
        return CAModel.get_ca_stats()
    
    @classmethod
    def get_issuer_validation_matrix(cls, limit: int = 10) -> List[Dict]:
        return CAModel.get_issuer_validation_matrix(limit)

        # ===========================
    # FAST CA METHODS (using materialized views)    
    # ===========================

    @classmethod
    def get_ca_stats_fast(cls) -> Dict:
        return CAModel.get_ca_stats_fast()
    
    @classmethod
    def get_issuer_validation_matrix_fast(cls, limit: int = 10) -> List[Dict]:
        return CAModel.get_issuer_validation_matrix_fast(limit)

        # ==================== SAN ANALYTICS METHODS ====================


    # ===========================
    # Slow SAN METHODS (using on-the-fly aggregation)
    # ===========================
    
    @classmethod
    def get_san_stats(cls) -> Dict[str, Any]:
        return SANModel.get_san_stats()

    @classmethod
    def get_san_distribution(cls) -> List[Dict[str, Any]]:
        return SANModel.get_san_distribution()

    @classmethod
    def get_san_tld_breakdown(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return SANModel.get_san_tld_breakdown(limit)

    @classmethod
    def get_san_wildcard_breakdown(cls) -> Dict[str, int]:
        return SANModel.get_san_wildcard_breakdown()

    # ===========================
    # FAST SAN METHODS (using materialized views)
    # ===========================
    
    @classmethod
    def get_san_stats_fast(cls) -> Dict[str, Any]:
        return SANModel.get_san_stats_fast()

    @classmethod
    def get_san_distribution_fast(cls) -> List[Dict[str, Any]]:
        return SANModel.get_san_distribution_fast()

    @classmethod
    def get_san_tld_breakdown_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return SANModel.get_san_tld_breakdown_fast(limit)

    @classmethod
    def get_san_wildcard_breakdown_fast(cls) -> Dict[str, int]:
        return SANModel.get_san_wildcard_breakdown_fast()

    @classmethod
    def get_san_filtered_certs_fast(cls, filter_type: str, filter_value: str = None,
                                     page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        return SANModel.get_san_filtered_certs_fast(filter_type, filter_value, page, page_size)



# ========== TRENDS ANALYTICS METHODS ==========

    @classmethod
    def get_trends_stats(cls) -> Dict[str, Any]:
        return TrendsModel.get_trends_stats()

    @classmethod
    def get_key_size_timeline(cls, months: int = 12) -> List[Dict[str, Any]]:
        return TrendsModel.get_key_size_timeline(months)

    @classmethod
    def get_expiration_forecast(cls, months: int = 12) -> List[Dict[str, Any]]:
        return TrendsModel.get_expiration_forecast(months)

    @classmethod
    def get_algorithm_adoption(cls, months: int = 12) -> List[Dict[str, Any]]:
        return TrendsModel.get_algorithm_adoption(months)

    @classmethod
    def get_validation_level_trends(cls, months: int = 12) -> List[Dict[str, Any]]:
        return TrendsModel.get_validation_level_trends(months)

    # ==================== SHARED KEYS ANALYTICS ====================
    # 
    # IMPORTANT: "Shared keys" means multiple DIFFERENT certificates using the same public key.
    # We identify this by:
    # 1. Grouping by public key fingerprint (parsed.subject_key_info.fingerprint_sha256)
    # 2. Counting DISTINCT certificate fingerprints (parsed.fingerprint_sha256) in each group
    # 3. Only considering it "shared" if there are 2+ distinct certificate fingerprints
    #
    # This excludes SAN certificates that are technically the same cert with different domain lists.
    # ===========================
    # Slow SHARED KEYS METHODS (using on-the-fly aggregation)
    # ===========================
    @classmethod
    def get_shared_key_stats(cls) -> Dict[str, Any]:
        return SharedKeyModel.get_shared_key_stats()

    @classmethod
    def get_shared_key_distribution(cls) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_key_distribution()
    
    @classmethod
    def get_shared_keys_by_issuer(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_keys_by_issuer(limit)  
    
    @classmethod  
    def get_shared_key_timeline(cls, months: int = 12) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_key_timeline(months)
    
    @classmethod
    def get_shared_key_heatmap(cls, limit: int = 10) -> List[Dict[str, Any]]:
       return SharedKeyModel.get_shared_key_heatmap(limit)
    
    # ===========================
    # FAST SHARED KEYS METHODS (using materialized views)
    # ===========================
    @classmethod
    def get_shared_key_stats_fast(cls) -> Dict[str, Any]:
        return SharedKeyModel.get_shared_key_stats_fast()

    @classmethod
    def get_shared_key_distribution_fast(cls) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_key_distribution_fast()

    @classmethod
    def get_shared_keys_by_issuer_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_keys_by_issuer_fast(limit)

    @classmethod
    def get_shared_key_timeline_fast(cls, months: int = 12) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_key_timeline_fast(months)

    @classmethod
    def get_shared_key_heatmap_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        return SharedKeyModel.get_shared_key_heatmap_fast(limit)

    @classmethod
    def get_shared_keys_list(cls, page: int = 1, page_size: int = 10, 
                             sort_by: str = 'certificate_count', sort_order: str = 'desc',
                             risk_level: str = None, key_type: str = None, 
                             min_cert_count: int = None, issuer: str = None) -> Dict[str, Any]:
        return SharedKeyModel.get_shared_keys_list(
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
            risk_level=risk_level,
            key_type=key_type,
            min_cert_count=min_cert_count,
            issuer=issuer
        )

    @classmethod
    def get_shared_key_detail(cls, public_key_hash: str) -> Dict[str, Any]:
        return SharedKeyModel.get_shared_key_detail(public_key_hash)
