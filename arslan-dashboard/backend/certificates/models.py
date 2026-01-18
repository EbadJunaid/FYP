# backend/certificates/models.py
# Pure Python representation of SSL Certificate Model with PyMongo queries

from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from bson import ObjectId
from .db import db

# TLD to Country mapping for deriving country from domain
TLD_TO_COUNTRY = {
    'pk': 'Pakistan',
    'us': 'United States',
    'com': 'United States',
    'uk': 'United Kingdom',
    'co.uk': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'jp': 'Japan',
    'ca': 'Canada',
    'au': 'Australia',
    'nl': 'Netherlands',
    'in': 'India',
    'cn': 'China',
    'br': 'Brazil',
    'kr': 'South Korea',
    'sg': 'Singapore',
    'ie': 'Ireland',
    'se': 'Sweden',
    'ch': 'Switzerland',
    'it': 'Italy',
    'es': 'Spain',
    'ru': 'Russia',
    'mx': 'Mexico',
    'za': 'South Africa',
    'nz': 'New Zealand',
    'org': 'International',
    'net': 'International',
    'io': 'International',
    'dev': 'International',
}


class CertificateModel:
    """
    Model class for SSL Certificate documents in MongoDB.
    Handles CRUD operations and aggregation queries.
    """
    collection = db['certificates']
    
    @staticmethod
    def get_current_time_iso() -> str:
        """Get current time in ISO format for MongoDB queries"""
        return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    
    @staticmethod
    def get_tld_country(domain: str) -> str:
        """Derive country from domain TLD"""
        if not domain:
            return 'Unknown'
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            # Check for two-part TLDs first (e.g., co.uk)
            two_part_tld = '.'.join(parts[-2:])
            if two_part_tld in TLD_TO_COUNTRY:
                return TLD_TO_COUNTRY[two_part_tld]
            # Check single TLD
            tld = parts[-1]
            return TLD_TO_COUNTRY.get(tld, 'Unknown')
        return 'Unknown'
    
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
        
        # Issuer filter
        if issuers and len(issuers) > 0:
            filters.append({
                '$or': [
                    {'parsed.issuer.organization': {'$elemMatch': {'$in': issuers}}},
                    {'parsed.issuer.organization': {'$in': issuers}}  # Handle both array and string
                ]
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
            query['$or'] = [
                {'parsed.subject.common_name': {'$regex': search, '$options': 'i'}},
                {'domain': {'$regex': search, '$options': 'i'}}
            ]
        
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
                query['parsed.issuer.organization'] = {'$regex': issuer, '$options': 'i'}
        
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
                # Use aggregation to compute duration and filter
                # For simplicity, we'll convert to ms range
                min_ms = min_days * 86400000
                max_ms = max_days * 86400000
                
                # Use aggregation pipeline for duration-based filtering
                pipeline = [
                    {'$match': query} if query else {'$match': {}},
                    {'$addFields': {
                        'validFromDate': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}},
                        'validToDate': {'$dateFromString': {'dateString': '$parsed.validity.end', 'onError': None}}
                    }},
                    {'$addFields': {
                        'durationMs': {'$subtract': ['$validToDate', '$validFromDate']}
                    }},
                    {'$match': {
                        'durationMs': {'$gte': min_ms, '$lt': max_ms}
                    }},
                    {'$facet': {
                        'data': [{'$skip': (page - 1) * page_size}, {'$limit': page_size}],
                        'count': [{'$count': 'total'}]
                    }}
                ]
                
                try:
                    result = list(cls.collection.aggregate(pipeline))
                    if result:
                        data = result[0].get('data', [])
                        count_data = result[0].get('count', [])
                        total = count_data[0]['total'] if count_data else 0
                        
                        certificates = [cls.serialize_certificate(doc) for doc in data]
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
                    print(f"Validity bucket filter error: {e}")
                
                return {
                    'certificates': [],
                    'pagination': {
                        'page': page,
                        'pageSize': page_size,
                        'total': 0,
                        'totalPages': 0
                    }
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
        
        # Handle country filter BEFORE pagination using aggregation pipeline
        # Country is derived from TLD, so we need to compute it for each document
        if country:
            # Use aggregation to compute country from domain TLD and filter
            # Build reverse TLD lookup for matching
            tld_values_for_country = [tld for tld, cntry in TLD_TO_COUNTRY.items() if cntry == country]
            
            # Build regex patterns for TLD matching
            tld_patterns = []
            for tld in tld_values_for_country:
                if '.' in tld:
                    # Two-part TLD like 'co.uk' - escape the dot
                    escaped_tld = tld.replace('.', r'\.')
                    tld_patterns.append(r'.*\.' + escaped_tld + '$')
                else:
                    # Single TLD
                    tld_patterns.append(r'.*\.' + tld + '$')
            
            if tld_patterns:
                # Add TLD filter to query
                tld_regex = '|'.join(tld_patterns)
                if '$and' in query:
                    query['$and'].append({'domain': {'$regex': tld_regex, '$options': 'i'}})
                else:
                    query['domain'] = {'$regex': tld_regex, '$options': 'i'}
            else:
                # No TLDs map to this country, return empty result
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
        total = cls.collection.count_documents(query)
        
        # Get paginated results
        skip = (page - 1) * page_size
        cursor = cls.collection.find(query).skip(skip).limit(page_size)
        
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
    def get_dashboard_metrics(cls) -> Dict:
        """Calculate accurate global health and dashboard metrics using aggregation"""
        
        now = cls.get_current_time_iso()
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Get total count
        # print("total certificates call before",cls.get_current_time_iso())

        total = cls.collection.count_documents({})
        # print("total certificates call after",cls.get_current_time_iso())
        if total == 0:
            return {
                'globalHealth': {
                    'score': 0,
                    'maxScore': 100,
                    'trend': 0,
                    'status': 'CRITICAL',
                    'lastUpdated': '2m ago'
                },
                'activeCertificates': {'count': 0, 'trend': 0},
                'expiringSoon': {'count': 0, 'daysThreshold': 30, 'actionNeeded': False},
                'criticalVulnerabilities': {'count': 0, 'new': 0}
            }
        
        # Count expired certificates (validity.end < now)
        expired_count = cls.collection.count_documents({
            'parsed.validity.end': {'$lt': now}
        })
        
        # Count expiring soon (now <= validity.end <= now+30days)
        expiring_count = cls.collection.count_documents({
            'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}
        })
        
        # Active = total - expired
        active_count = total - expired_count
        
        # Count certificates with zlint errors (critical vulnerabilities)
        # Using aggregation to count ALL certificates with at least one error
        # No sampling - queries entire collection for accuracy
        vuln_pipeline = [
            {
                "$match": {
                    "zlint.errors_present": True,
                    "zlint.lints": {"$exists": True, "$ne": {}}
                }
            },
            {'$project': {
                'lints_array': {'$objectToArray': '$zlint.lints'}
            }},
            {'$unwind': '$lints_array'},
            {'$match': {'lints_array.v.result': 'error'}},
            {'$group': {'_id': '$_id'}},  # Group by document to count unique certs
            {'$count': 'total'}
        ]
        
        vuln_result = list(cls.collection.aggregate(vuln_pipeline))
        critical_vulns = vuln_result[0]['total'] if vuln_result else 0
        
        # Calculate health score based on active percentage and low vulnerability rate
        active_percentage = (active_count / total) * 100 if total > 0 else 0
        vuln_penalty = min(20, (critical_vulns / total) * 100) if total > 0 else 0
        health_score = int(min(100, max(0, active_percentage - vuln_penalty)))
        
        # Determine status
        if health_score >= 80:
            health_status = 'SECURE'
        elif health_score >= 50:
            health_status = 'AT_RISK'
        else:
            health_status = 'CRITICAL'
        
        return {
            'globalHealth': {
                'score': health_score,
                'maxScore': 100,
                'status': health_status,
                'lastUpdated': datetime.now(timezone.utc).strftime('%H:%M')
            },
            'activeCertificates': {
                'count': active_count,
                'total': total
            },
            'expiringSoon': {
                'count': expiring_count,
                'daysThreshold': 30,
                'actionNeeded': expiring_count > 100
            },
            'criticalVulnerabilities': {
                'count': critical_vulns,
                'new': max(0, critical_vulns // 10)
            },
            'expiredCertificates': {
                'count': expired_count
            }
        }
    
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
        """Get encryption type distribution with detailed subtypes (e.g., RSA 2048, ECDSA)
        
        Args:
            base_filter: Global filter query - applied before aggregation
        """
        
        # Get total certificates count (with or without filter)
        if base_filter:
            total = cls.collection.count_documents(base_filter)
        else:
            total = cls.collection.count_documents({})
        
        if total == 0:
            return []
        
        # Build aggregation pipeline
        pipeline = []
        
        # Apply base filter first if provided
        if base_filter:
            pipeline.append({'$match': base_filter})
        
        # Add aggregation stages
        pipeline.extend([
            {'$project': {
                'algo': '$parsed.subject_key_info.key_algorithm.name',
                'rsa_length': '$parsed.subject_key_info.rsa_public_key.length',
                'ec_length': '$parsed.subject_key_info.ecdsa_public_key.length'
            }},
            {'$addFields': {
                'key_length': {'$ifNull': ['$rsa_length', '$ec_length']}
            }},
            {'$group': {
                '_id': {
                    'algo': '$algo',
                    'length': '$key_length'
                },
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ])
        
        results = list(cls.collection.aggregate(pipeline))
        
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
        
        encryption_data = []
        for i, r in enumerate(results):
            algo = r['_id'].get('algo') or 'Unknown'
            length = r['_id'].get('length')
            
            # Create display name: "RSA 2048" or "ECDSA" if no length
            if length and algo in ['RSA', 'ECDSA', 'EC']:
                name = f"{algo} {length}"
            else:
                name = algo
            
            encryption_data.append({
                'id': f'enc-{i}',
                'name': name,
                'type': type_labels.get(algo, 'Standard'),
                'count': r['count'],
                'percentage': round((r['count'] / total) * 100, 1),
                'color': type_colors.get(algo, '#6b7280')
            })
        
        return encryption_data
    
    @classmethod
    def get_validity_trends(cls, months_before: int = 4, months_after: int = 4, granularity: str = 'monthly') -> List[Dict]:
        """Get certificate expiration trends by calendar period
        
        Args:
            months_before: Number of months to look back
            months_after: Number of months to look ahead
            granularity: 'monthly' or 'weekly' - determines the grouping period
        
        Returns:
            List of dicts with period, expirations count, and period metadata
        """
        from calendar import monthrange
        from dateutil.relativedelta import relativedelta
        
        trends = []
        now = datetime.now(timezone.utc)
        
        if granularity == 'weekly':
            # Weekly granularity: show last N weeks and next M weeks
            weeks_before = months_before * 4  # ~4 weeks per month
            weeks_after = months_after * 4
            
            for i in range(-weeks_before, weeks_after + 1):
                # Calculate week start (Monday) and end (Sunday)
                week_start = now + timedelta(weeks=i)
                # Adjust to Monday of that week
                week_start = week_start - timedelta(days=week_start.weekday())
                week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
                
                start_str = week_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_str = week_end.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Count certificates expiring in this week
                count = cls.collection.count_documents({
                    'parsed.validity.end': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                })
                
                # Week label: "Jan 6-12"
                week_label = f"{week_start.strftime('%b %d')}-{week_end.strftime('%d')}"
                is_current = (week_start <= now <= week_end)
                
                trends.append({
                    'month': week_label,  # Keep key as 'month' for frontend compatibility
                    'expirations': count,
                    'year': week_start.year,
                    'monthNum': week_start.month,
                    'weekNum': week_start.isocalendar()[1],
                    'weekStart': start_str,
                    'weekEnd': end_str,
                    'isCurrent': is_current,
                    'granularity': 'weekly'
                })
        else:
            # Monthly granularity (default)
            start_offset = -(months_before)
            end_offset = months_after
            
            for i in range(start_offset, end_offset + 1):
                # Calculate the target month using relativedelta
                target_date = now + relativedelta(months=i)
                year = target_date.year
                month = target_date.month
                
                # Get first day and last day of the month
                _, days_in_month = monthrange(year, month)
                month_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
                month_end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)
                
                start_str = month_start.strftime('%Y-%m-%dT%H:%M:%SZ')
                end_str = month_end.strftime('%Y-%m-%dT%H:%M:%SZ')
                
                # Count certificates expiring in this month
                count = cls.collection.count_documents({
                    'parsed.validity.end': {
                        '$gte': start_str,
                        '$lte': end_str
                    }
                })
                
                # Include year with month name for clarity (e.g., "Jan 2026")
                month_label = month_start.strftime('%b %Y')
                is_current = (year == now.year and month == now.month)
                
                trends.append({
                    'month': month_label,
                    'expirations': count,
                    'year': year,
                    'monthNum': month,
                    'isCurrent': is_current,
                    'granularity': 'monthly'
                })
        
        return trends
    
    @classmethod
    def get_ca_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """Get Certificate Authority distribution with accurate percentages
        Uses parsed.issuer.organization.0 (first element) for unique issuers
        
        Args:
            base_filter: Global filter query - applied before aggregation
        """
        
        # Get total certificates count (with or without filter)
        if base_filter:
            total = cls.collection.count_documents(base_filter)
        else:
            total = cls.collection.count_documents({})
        
        if total == 0:
            return []
        
        # Build aggregation pipeline
        pipeline = []
        
        # Apply base filter first if provided
        if base_filter:
            pipeline.append({'$match': base_filter})
        
        # Add aggregation stages - Use $arrayElemAt to get first organization element
        pipeline.extend([
            {'$project': {
                'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
            }},
            {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
            {'$group': {
                '_id': '$issuer_org',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
            {'$limit': limit}
        ])
        
        results = list(cls.collection.aggregate(pipeline))
        max_count = results[0]['count'] if results else 1
        
        # Extended color palette for all unique CAs
        colors = [
            '#10b981',  # Green - Let's Encrypt
            '#3b82f6',  # Blue - Google Trust Services
            '#8b5cf6',  # Purple - Sectigo
            '#f59e0b',  # Orange - DigiCert
            '#ef4444',  # Red - GoGetSSL
            '#06b6d4',  # Cyan - GoDaddy
            '#14b8a6',  # Teal - Amazon
            '#6366f1',  # Indigo - Starfield
            '#ec4899',  # Pink - cPanel
            '#84cc16',  # Lime - ZeroSSL
            '#f97316',  # Orange-600 - Cloudflare
            '#a855f7',  # Purple-500 - SSL Corp
            '#22c55e',  # Green-500 - WoTrus
            '#0ea5e9',  # Sky - Buypass
            '#d946ef',  # Fuchsia - Certainly
            '#eab308',  # Yellow - Entrust
            '#6b7280',  # Gray - Others
        ]
        
        ca_list = [
            {
                'id': f'ca-{i}',
                'name': r['_id'],
                'count': r['count'],
                'maxCount': max_count,
                'percentage': round((r['count'] / total) * 100, 1),
                'color': colors[i % len(colors)]
            }
            for i, r in enumerate(results)
        ]
        
        # Add "Others" entry for remaining CAs (if any exist beyond limit)
        top_ca_count = sum(r['count'] for r in results)
        others_count = total - top_ca_count
        if others_count > 0:
            ca_list.append({
                'id': 'ca-others',
                'name': 'Others',
                'count': others_count,
                'maxCount': max_count,
                'percentage': round((others_count / total) * 100, 1),
                'color': '#6b7280',  # Gray for Others
                'isOthers': True  # Flag to identify this is the aggregated "Others" entry
            })
        
        return ca_list
    
    @classmethod
    def get_geographic_distribution(cls, limit: int = 10, base_filter: Optional[Dict] = None) -> List[Dict]:
        """Get certificate distribution by country (from domain TLD)
        Optimized: Compute TLD directly in MongoDB aggregation
        
        Args:
            base_filter: Global filter query - applied before aggregation
        """
        
        # Get total certificates count (with or without filter)
        if base_filter:
            total = cls.collection.count_documents(base_filter)
        else:
            total = cls.collection.count_documents({})
        
        if total == 0:
            return []
        
        # Build aggregation pipeline
        pipeline = []
        
        # Apply base filter first if provided
        if base_filter:
            pipeline.append({'$match': base_filter})
        
        # Add domain extraction and grouping stages
        pipeline.extend([
            {'$match': {'domain': {'$exists': True, '$ne': None, '$ne': ''}}},
            {'$project': {
                'domain_parts': {'$split': ['$domain', '.']},
            }},
            {'$project': {
                'tld': {'$arrayElemAt': ['$domain_parts', -1]}
            }},
            {'$match': {'tld': {'$exists': True, '$ne': None}}},
            {'$group': {
                '_id': '$tld',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ])
        
        results = list(cls.collection.aggregate(pipeline))
        
        # Map TLDs to countries (small dataset, fast in Python)
        country_counts = {}
        for r in results:
            tld = r['_id'].lower() if r['_id'] else 'unknown'
            country = cls.get_tld_country('example.' + tld)  # Use helper with dummy domain
            if country != 'Unknown':
                country_counts[country] = country_counts.get(country, 0) + r['count']
        
        # Sort and limit
        sorted_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        colors = ['#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#6b7280']
        
        max_count = sorted_countries[0][1] if sorted_countries else 1
        
        return [
            {
                'id': f'geo-{i}',
                'country': country,
                'count': count,
                'maxCount': max_count,
                'percentage': round((count / total) * 100, 1),
                'color': colors[i % len(colors)]
            }
            for i, (country, count) in enumerate(sorted_countries)
        ]

    @classmethod
    def get_validity_stats(cls) -> Dict:
        """Get validity statistics for validity analysis page
        
        Uses parsed.validity.length (in seconds) for duration calculations.
        
        Returns:
            - averageValidityDays: avg number of days (length / 86400)
            - expiring30Days: count expiring in next 30 days
            - expiring60Days: count expiring in next 60 days
            - expiring90Days: count expiring in next 90 days
            - complianceRate: % of certs with validity <= 398 days
            - shortestValidityDays: min validity period
            - longestValidityDays: max validity period
        """
        now = datetime.now(timezone.utc)
        now_iso = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_30 = (now + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_60 = (now + timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_90 = (now + timedelta(days=90)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Use parsed.validity.length (in seconds) for duration calculations
        # This is a pre-computed field in the database
        pipeline = [
            {
                '$match': {
                    'parsed.validity.length': {'$exists': True, '$gt': 0}
                }
            },
            {
                '$project': {
                    'lengthSeconds': '$parsed.validity.length',
                    # Convert seconds to days for aggregation
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
        
        try:
            result = list(cls.collection.aggregate(pipeline))
            stats = result[0] if result else {}
        except Exception as e:
            print(f"Aggregation error: {e}")
            stats = {}
        
        # Count expiring in next 30/60/90 days (separate queries for accuracy)
        expiring_30 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_30}
        })
        expiring_60 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_60}
        })
        expiring_90 = cls.collection.count_documents({
            'parsed.validity.end': {'$gt': now_iso, '$lte': plus_90}
        })
        
        total = stats.get('total', 0) or cls.collection.count_documents({})
        compliant = stats.get('compliantCount', 0)
        
        return {
            'averageValidityDays': round(stats.get('avgDuration', 0) or 0),
            'shortestValidityDays': round(stats.get('minDuration', 0) or 0),
            'longestValidityDays': round(stats.get('maxDuration', 0) or 0),
            'expiring30Days': expiring_30,
            'expiring60Days': expiring_60,
            'expiring90Days': expiring_90,
            'complianceRate': round((compliant / total * 100), 1) if total > 0 else 0,
            'totalCertificates': total
        }
    
    @classmethod
    def get_validity_distribution(cls) -> List[Dict]:
        """Get distribution of certificate validity periods by bucket
        
        Buckets:
        - <90 days
        - 90 days - 1 year
        - 1-2 years  
        - >2 years
        """
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
                    'boundaries': [0, 90, 365, 730, 100000],  # 0-90, 90-365, 365-730, 730+
                    'default': 'Other',
                    'output': {
                        'count': {'$sum': 1}
                    }
                }
            }
        ]
        
        try:
            results = list(cls.collection.aggregate(pipeline))
        except Exception as e:
            print(f"Validity distribution error: {e}")
            results = []
        
        # Map bucket boundaries to labels
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
                distribution.append({
                    'range': bucket_labels[bucket_id],
                    'count': r.get('count', 0),
                    'percentage': round((r.get('count', 0) / total * 100), 1) if total > 0 else 0,
                    'color': bucket_colors.get(bucket_id, '#6b7280')
                })
        
        return distribution
    
    @classmethod
    def get_issuance_timeline(cls, months: int = 12) -> List[Dict]:
        """Get certificate issuance and expiration timeline by month
        
        Shows the last N months from current month (past data only).
        
        Returns monthly counts for:
        - issued: certificates issued (validFrom) in that month
        - expired: certificates expired (validTo) in that month (past only)
        """
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now(timezone.utc)
        
        # Calculate date range: last N months from the start of current month
        # Start from (months-1) months ago to include current month
        end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)  # End of current month
        start_date = now.replace(day=1) - relativedelta(months=months-1)  # Start of N months ago
        
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Issued certificates by month (using validFrom)
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
        
        # Expiring certificates by month (using validTo)
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
        
        try:
            issued_results = list(cls.collection.aggregate(issued_pipeline))
            expiring_results = list(cls.collection.aggregate(expiring_pipeline))
        except Exception as e:
            print(f"Issuance timeline error: {e}")
            issued_results = []
            expiring_results = []
        
        # Build month list
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
            
            timeline.append({
                'month': month_label,
                'year': current.year,
                'monthNum': current.month,
                'issued': issued_lookup.get(key, 0),
                'expiring': expiring_lookup.get(key, 0)
            })
            
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        
        return timeline

    @classmethod
    def get_notifications(cls) -> Dict:
        """
        Get real-time notification data based on certificate status.
        Uses efficient aggregation for counting.
        """
        from datetime import datetime, timezone, timedelta
        
        now = datetime.now(timezone.utc)
        now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_2_days = (now + timedelta(days=2)).strftime('%Y-%m-%dT%H:%M:%SZ')
        plus_7_days = (now + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%SZ')
        yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Use $facet for efficient multi-aggregation in single query
        pipeline = [
            {'$facet': {
                'expiring_2_days': [
                    {'$match': {
                        'parsed.validity.end': {'$gte': now_str, '$lte': plus_2_days}
                    }},
                    {'$count': 'count'}
                ],
                'expiring_7_days': [
                    {'$match': {
                        'parsed.validity.end': {'$gte': now_str, '$lte': plus_7_days}
                    }},
                    {'$count': 'count'}
                ],
                'vulnerabilities': [
                    {'$match': {
                        'zlint.errors_present': True,
                        'parsed.validity.end': {'$gt': now_str}
                    }},
                    {'$count': 'count'}
                ],
                'weak_encryption': [
                    {'$match': {
                        'parsed.subject_key_info.key_algorithm.name': 'RSA',
                        'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}
                    }},
                    {'$count': 'count'}
                ],
                'newly_expired': [
                    {'$match': {
                        'parsed.validity.end': {'$gte': yesterday, '$lt': now_str}
                    }},
                    {'$count': 'count'}
                ]
            }}
        ]
        
        result = list(cls.collection.aggregate(pipeline))
        
        if not result:
            return {'notifications': [], 'unreadCount': 0, 'totalCount': 0}
        
        facet_result = result[0]
        
        # Extract counts (default to 0 if empty)
        def get_count(key: str) -> int:
            arr = facet_result.get(key, [])
            return arr[0]['count'] if arr else 0
        
        expiring_2_days = get_count('expiring_2_days')
        expiring_7_days = get_count('expiring_7_days')
        vulnerabilities = get_count('vulnerabilities')
        weak_encryption = get_count('weak_encryption')
        newly_expired = get_count('newly_expired')
        
        notifications = []
        timestamp = now.isoformat()
        
        # Build notification list (only add if count > 0)
        if expiring_2_days > 0:
            notifications.append({
                'id': 'expiring-2-days',
                'type': 'error',
                'category': 'expiring',
                'title': f'{expiring_2_days} certificate{"s" if expiring_2_days > 1 else ""} expiring in 1-2 days',
                'description': 'Immediate attention required',
                'count': expiring_2_days,
                'filterParams': {'status': 'EXPIRING_SOON', 'days': 2},
                'timestamp': timestamp,
                'read': False
            })
        
        if expiring_7_days > expiring_2_days:  # Exclude already counted 2-day ones
            remaining = expiring_7_days - expiring_2_days
            if remaining > 0:
                notifications.append({
                    'id': 'expiring-7-days',
                    'type': 'warning',
                    'category': 'expiring',
                    'title': f'{remaining} certificate{"s" if remaining > 1 else ""} expiring in 3-7 days',
                    'description': 'Plan renewal soon',
                    'count': remaining,
                    'filterParams': {'status': 'EXPIRING_SOON', 'days': 7},
                    'timestamp': timestamp,
                    'read': False
                })
        
        if vulnerabilities > 0:
            notifications.append({
                'id': 'vulnerabilities',
                'type': 'error',
                'category': 'security',
                'title': f'{vulnerabilities} certificate{"s" if vulnerabilities > 1 else ""} with vulnerabilities',
                'description': 'ZLint detected security issues',
                'count': vulnerabilities,
                'filterParams': {'has_vulnerabilities': True},
                'timestamp': timestamp,
                'read': False
            })
        
        if weak_encryption > 0:
            notifications.append({
                'id': 'weak-encryption',
                'type': 'warning',
                'category': 'security',
                'title': f'{weak_encryption} certificate{"s" if weak_encryption > 1 else ""} with weak encryption',
                'description': 'RSA key length below 2048 bits',
                'count': weak_encryption,
                'filterParams': {'encryption_type': 'RSA weak'},
                'timestamp': timestamp,
                'read': False
            })
        
        if newly_expired > 0:
            notifications.append({
                'id': 'newly-expired',
                'type': 'error',
                'category': 'expired',
                'title': f'{newly_expired} certificate{"s" if newly_expired > 1 else ""} expired recently',
                'description': 'Expired in the last 24 hours',
                'count': newly_expired,
                'filterParams': {'status': 'EXPIRED'},
                'timestamp': timestamp,
                'read': False
            })
        
        return {
            'notifications': notifications,
            'unreadCount': len(notifications),
            'totalCount': len(notifications)
        }
    
    # ----- New implementation for Signature and Hashes starts here -----
    
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
        total = cls.collection.count_documents({})
        
        if total == 0:
            return {
                'algorithmDistribution': [],
                'hashDistribution': [],
                'keySizeDistribution': [],
                'weakHashCount': 0,
                'hashComplianceRate': 0,
                'strengthScore': 0,
                'selfSignedCount': 0,
                'totalCertificates': 0
            }
        
        # PIPELINE 1: Signature Algorithm Distribution (e.g., "SHA256-RSA", "SHA256-ECDSA")
        # Uses direct $group on indexed field - very efficient
        algo_pipeline = [
            {'$group': {
                '_id': '$parsed.signature_algorithm.name',
                'count': {'$sum': 1}
            }},
            {'$match': {'_id': {'$ne': None}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]
        algo_results = list(cls.collection.aggregate(algo_pipeline, allowDiskUse=True))
        
        # Calculate percentages and format
        algorithm_distribution = []
        algo_colors = {
            'SHA256-RSA': '#3b82f6',
            'SHA384-RSA': '#60a5fa', 
            'SHA512-RSA': '#1d4ed8',
            'SHA256-ECDSA': '#10b981',
            'SHA384-ECDSA': '#34d399',
            'SHA512-ECDSA': '#059669',
            'SHA1-RSA': '#f59e0b',  # Warning color
            'MD5-RSA': '#ef4444',   # Critical color
        }
        
        for item in algo_results:
            name = item['_id'] or 'Unknown'
            count = item['count']
            algorithm_distribution.append({
                'name': name,
                'count': count,
                'percentage': round((count / total) * 100, 2),
                'color': algo_colors.get(name, '#6b7280')
            })
        
        # PIPELINE 2: Hash Algorithm Distribution (extract hash from signature_algorithm.name)
        # Handles both formats: "SHA256-RSA", "ECDSA-SHA256", etc.
        hash_pipeline = [
            {'$project': {
                'sigAlgo': '$parsed.signature_algorithm.name'
            }},
            {'$addFields': {
                'hash': {
                    '$switch': {
                        'branches': [
                            # Match SHA512 at start or after hyphen (e.g., SHA512-RSA, ECDSA-SHA512)
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA512|SHA-512', 'options': 'i'}}, 'then': 'SHA-512'},
                            # Match SHA384 at start or after hyphen
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA384|SHA-384', 'options': 'i'}}, 'then': 'SHA-384'},
                            # Match SHA256 at start or after hyphen
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA256|SHA-256', 'options': 'i'}}, 'then': 'SHA-256'},
                            # Match SHA224
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA224|SHA-224', 'options': 'i'}}, 'then': 'SHA-224'},
                            # Match SHA1 (weak)
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA1|SHA-1|withSHA1', 'options': 'i'}}, 'then': 'SHA-1'},
                            # Match MD5 (critical)
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD5', 'options': 'i'}}, 'then': 'MD5'},
                            # Match MD2 (critical)
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD2', 'options': 'i'}}, 'then': 'MD2'},
                        ],
                        # If no match, use the original signature algorithm name
                        'default': '$sigAlgo'
                    }
                }
            }},
            # Filter out null/empty hashes
            {'$match': {'hash': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$hash',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        hash_results = list(cls.collection.aggregate(hash_pipeline, allowDiskUse=True))
        
        hash_colors = {
            'SHA-512': '#1d4ed8',  # Secure - dark blue
            'SHA-384': '#3b82f6',  # Secure - blue
            'SHA-256': '#10b981',  # Secure - green
            'SHA-224': '#34d399',  # Secure - light green
            'SHA-1': '#f59e0b',    # Deprecated - orange
            'MD5': '#ef4444',      # Critical - red
            'MD2': '#dc2626',      # Critical - dark red
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
            
            # Count weak hashes (SHA-1, MD5)
            if name in ['SHA-1', 'MD5']:
                weak_hash_count += count
            
            # Count compliant (SHA-256, SHA-384, SHA-512)
            if name in ['SHA-256', 'SHA-384', 'SHA-512']:
                compliant_count += count
        
        # PIPELINE 3: Key Size Distribution
        # Efficient direct grouping on key length field
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
        keysize_results = list(cls.collection.aggregate(keysize_pipeline, allowDiskUse=True))
        
        keysize_distribution = []
        for item in keysize_results:
            algo = item['_id'].get('algo', 'Unknown')
            size = item['_id'].get('size', 0)
            count = item['count']
            
            # Format name like "RSA 2048" or "ECDSA 256"
            name = f"{algo} {size}" if size else algo
            
            keysize_distribution.append({
                'name': name,
                'algorithm': algo,
                'size': size,
                'count': count,
                'percentage': round((count / total) * 100, 2),
                'color': '#3b82f6' if algo == 'RSA' else '#10b981'
            })
        
        # Count self-signed certificates (fast indexed query)
        self_signed_count = cls.collection.count_documents({
            'parsed.signature.self_signed': True
        })
        
        # Calculate hash compliance rate
        hash_compliance_rate = round((compliant_count / total) * 100, 1) if total > 0 else 0
        
        # Calculate Signature Strength Score (0-100)
        # Formula: (KeySizeScore * 0.4) + (HashScore * 0.4) + (AlgoScore * 0.2)
        
        # Key Size Score: Weighted by distribution
        key_score = 0
        for item in keysize_distribution:
            size = item.get('size', 0)
            pct = item.get('percentage', 0) / 100
            if size >= 4096:
                key_score += 100 * pct
            elif size >= 2048:
                key_score += 80 * pct
            elif size >= 1024:
                key_score += 40 * pct
            elif size >= 256:  # ECDSA
                key_score += 90 * pct
        
        # Hash Score: Based on compliance rate
        hash_score = hash_compliance_rate
        
        # Algorithm Score: Based on ECDSA vs RSA distribution
        algo_score = 85  # Default RSA score
        for item in algorithm_distribution:
            if 'ECDSA' in item.get('name', ''):
                algo_score += item.get('percentage', 0) * 0.15  # ECDSA bonus
        algo_score = min(100, algo_score)
        
        strength_score = int((key_score * 0.4) + (hash_score * 0.4) + (algo_score * 0.2))
        strength_score = max(0, min(100, strength_score))  # Clamp to 0-100
        
        # PIPELINE 4: Max Encryption Type (RSA vs ECDSA with highest count)
        enc_type_pipeline = [
            {'$group': {
                '_id': '$parsed.subject_key_info.key_algorithm.name',
                'count': {'$sum': 1}
            }},
            {'$match': {'_id': {'$ne': None}}},
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
        enc_type_result = list(cls.collection.aggregate(enc_type_pipeline, allowDiskUse=True))
        
        max_encryption_type = None
        if enc_type_result:
            enc_name = enc_type_result[0]['_id']
            enc_count = enc_type_result[0]['count']
            max_encryption_type = {
                'name': enc_name,
                'count': enc_count,
                'percentage': round((enc_count / total) * 100, 2) if total > 0 else 0
            }
        
        return {
            'algorithmDistribution': algorithm_distribution,
            'hashDistribution': hash_distribution,
            'keySizeDistribution': keysize_distribution,
            'weakHashCount': weak_hash_count,
            'hashComplianceRate': hash_compliance_rate,
            'strengthScore': strength_score,
            'selfSignedCount': self_signed_count,
            'totalCertificates': total,
            'maxEncryptionType': max_encryption_type
        }
    
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
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now(timezone.utc)
        start_date = now - relativedelta(months=months)
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Build period grouping based on granularity
        if granularity == 'yearly':
            period_expr = {
                'year': {'$year': '$issuedDate'}
            }
        else:  # quarterly
            period_expr = {
                'year': {'$year': '$issuedDate'},
                'quarter': {'$ceil': {'$divide': [{'$month': '$issuedDate'}, 3]}}
            }
        
        pipeline = [
            # Stage 1: Match documents in date range (uses index on validity.start)
            {'$match': {
                'parsed.validity.start': {'$gte': start_str}
            }},
            # Stage 2: Project only needed fields
            {'$project': {
                'sigAlgo': '$parsed.signature_algorithm.name',
                'issuedDate': {'$dateFromString': {
                    'dateString': '$parsed.validity.start',
                    'onError': None
                }}
            }},
            # Stage 3: Filter out null dates
            {'$match': {'issuedDate': {'$ne': None}}},
            # Stage 4: Extract hash algorithm
            {'$addFields': {
                'hash': {
                    '$switch': {
                        'branches': [
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': '^SHA512'}}, 'then': 'SHA-512'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': '^SHA384'}}, 'then': 'SHA-384'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': '^SHA256'}}, 'then': 'SHA-256'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': '^SHA1|^SHA-1'}}, 'then': 'SHA-1'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': '^MD5'}}, 'then': 'MD5'},
                        ],
                        'default': 'Other'
                    }
                },
                'period': period_expr
            }},
            # Stage 5: Group by period and hash
            {'$group': {
                '_id': {'period': '$period', 'hash': '$hash'},
                'count': {'$sum': 1}
            }},
            # Stage 6: Reshape for easier processing
            {'$group': {
                '_id': '$_id.period',
                'hashes': {'$push': {'hash': '$_id.hash', 'count': '$count'}},
                'total': {'$sum': '$count'}
            }},
            {'$sort': {'_id.year': 1, '_id.quarter': 1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        trends = []
        for item in results:
            period = item['_id']
            total = item['total']
            
            if granularity == 'yearly':
                period_label = str(period.get('year', 'Unknown'))
            else:
                year = period.get('year', 0)
                quarter = period.get('quarter', 0)
                period_label = f"Q{quarter} {year}"
            
            # Convert hash counts to percentages
            hash_pcts = {}
            for h in item.get('hashes', []):
                hash_name = h['hash']
                hash_pcts[hash_name] = round((h['count'] / total) * 100, 1) if total > 0 else 0
            
            trends.append({
                'period': period_label,
                'year': period.get('year', 0),
                'quarter': period.get('quarter', 0) if granularity == 'quarterly' else None,
                'total': total,
                'SHA-256': hash_pcts.get('SHA-256', 0),
                'SHA-384': hash_pcts.get('SHA-384', 0),
                'SHA-512': hash_pcts.get('SHA-512', 0),
                'SHA-1': hash_pcts.get('SHA-1', 0),
                'MD5': hash_pcts.get('MD5', 0),
                'Other': hash_pcts.get('Other', 0)
            })
        
        return trends
    
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
            {'$limit': 50}  # Limit total combinations
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        matrix = []
        for item in results:
            issuer = item['_id'].get('issuer', 'Unknown')
            algo = item['_id'].get('algo', 'Unknown')
            key_size = item['_id'].get('keySize', 0)
            count = item['count']
            
            # Format algorithm string like "RSA-2048"
            algo_str = f"{algo}-{key_size}" if key_size else algo
            
            matrix.append({
                'issuer': issuer,
                'algorithm': algo_str,
                'algorithmType': algo,
                'keySize': key_size,
                'count': count
            })
        
        return matrix
    
    @classmethod
    def get_ca_stats(cls) -> Dict:
        """
        Get CA Analytics stats for metric cards.
        Returns: total CAs, top CA, self-signed count, unique CA countries
        """
        # Get total unique CAs
        ca_pipeline = [
            {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
            {'$group': {'_id': '$parsed.issuer.organization'}},
            {'$count': 'total'}
        ]
        ca_result = list(cls.collection.aggregate(ca_pipeline))
        total_cas = ca_result[0]['total'] if ca_result else 0
        
        # Get top CA
        top_ca_pipeline = [
            {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
            {'$group': {'_id': '$parsed.issuer.organization', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
        top_ca_result = list(cls.collection.aggregate(top_ca_pipeline))
        total_certs = cls.collection.count_documents({})
        
        top_ca = None
        top_ca_count = 0
        top_ca_percentage = 0
        if top_ca_result:
            top_ca = top_ca_result[0]['_id'] or 'Unknown'
            top_ca_count = top_ca_result[0]['count']
            top_ca_percentage = round((top_ca_count / total_certs) * 100, 1) if total_certs > 0 else 0
        
        # Get self-signed count
        self_signed_count = cls.collection.count_documents({
            'parsed.signature.self_signed': True
        })
        
        # Get unique CA countries
        country_pipeline = [
            {'$unwind': {'path': '$parsed.issuer.country', 'preserveNullAndEmptyArrays': True}},
            {'$group': {'_id': '$parsed.issuer.country'}},
            {'$match': {'_id': {'$ne': None}}},
            {'$count': 'total'}
        ]
        country_result = list(cls.collection.aggregate(country_pipeline))
        unique_countries = country_result[0]['total'] if country_result else 0
        
        return {
            'total_cas': total_cas,
            'total_certs': total_certs,
            'top_ca': {
                'name': top_ca,
                'count': top_ca_count,
                'percentage': top_ca_percentage
            },
            'self_signed_count': self_signed_count,
            'unique_countries': unique_countries
        }
    
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
    
    @classmethod
    def get_issuer_validation_matrix(cls, limit: int = 10) -> List[Dict]:
        """
        Get matrix of issuer × validation level combinations with counts.
        Similar to get_issuer_algorithm_matrix but for validation levels (DV, OV, EV).
        
        Returns:
            List of dicts with issuer, validationLevel, and count
        """
        
        pipeline = [
            # Stage 1: Project needed fields only
            {'$project': {
                'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
                'validationLevel': {'$ifNull': ['$parsed.validation_level', 'Unknown']}
            }},
            # Stage 2: Filter out null issuers
            {'$match': {'issuer': {'$exists': True, '$ne': None}}},
            # Stage 3: Group by issuer + validationLevel
            {'$group': {
                '_id': {
                    'issuer': '$issuer',
                    'validationLevel': '$validationLevel'
                },
                'count': {'$sum': 1}
            }},
            # Stage 4: Sort by count for top issuers first
            {'$sort': {'count': -1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        # Extract unique issuers (top N by total count)
        issuer_totals = {}
        for r in results:
            issuer = r['_id']['issuer']
            issuer_totals[issuer] = issuer_totals.get(issuer, 0) + r['count']
        
        # Get top issuers
        top_issuers = sorted(issuer_totals.items(), key=lambda x: x[1], reverse=True)[:limit]
        top_issuer_names = {issuer for issuer, _ in top_issuers}
        
        # Build matrix data
        matrix = []
        for r in results:
            issuer = r['_id']['issuer']
            if issuer in top_issuer_names:
                matrix.append({
                    'issuer': issuer,
                    'validationLevel': r['_id']['validationLevel'],
                    'count': r['count']
                })
        
        return matrix

    # ==================== SAN ANALYTICS METHODS ====================
    
    @classmethod
    def get_san_stats(cls) -> Dict[str, Any]:
        """
        Get SAN (Subject Alternative Name) statistics for metric cards.
        
        Returns:
            Dict with total_sans, avg_sans_per_cert, wildcard_certs, multi_domain_certs
        """
        pipeline = [
                {
                    '$project': {
                        # Ensure we are looking at the specific SAN DNS array
                        # We use $ifNull to handle missing fields and $filter to handle nulls
                        'names': {
                            '$filter': {
                                'input': {'$ifNull': ['$parsed.extensions.subject_alt_name.dns_names', []]},
                                'as': 'n',
                                'cond': {'$ne': ['$$n', None]}
                            }
                        }
                    }
                },
                {
                    '$addFields': {
                        'sanCount': {'$size': '$names'},
                        'hasWildcard': {
                            '$gt': [
                                {'$size': {
                                    '$filter': {
                                        'input': '$names',
                                        'as': 'name',
                                        'cond': {
                                            '$and': [
                                                {'$eq': [{'$type': '$$name'}, 'string']},
                                                {'$regexMatch': {'input': '$$name', 'regex': '^\\*\\.'}}
                                            ]
                                        }
                                    }
                                }},
                                0
                            ]
                        }
                    }
                },
                {
                    '$addFields': {
                        'isMultiDomain': {'$gte': ['$sanCount', 5]}
                    }
                },
                {
                    '$group': {
                        '_id': None,
                        'totalSans': {'$sum': '$sanCount'},
                        'totalCerts': {'$sum': 1},
                        'wildcardCerts': {'$sum': {'$cond': ['$hasWildcard', 1, 0]}},
                        'multiDomainCerts': {'$sum': {'$cond': ['$isMultiDomain', 1, 0]}}
                    }
                }
            ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        if results:
            data = results[0]
            total_certs = data.get('totalCerts', 1) or 1
            return {
                'total_sans': data.get('totalSans', 0),
                'avg_sans_per_cert': round(data.get('totalSans', 0) / total_certs, 2),
                'wildcard_certs': data.get('wildcardCerts', 0),
                'multi_domain_certs': data.get('multiDomainCerts', 0),
                'total_certs': total_certs
            }
        
        return {
            'total_sans': 0,
            'avg_sans_per_cert': 0,
            'wildcard_certs': 0,
            'multi_domain_certs': 0,
            'total_certs': 0
        }
    
    @classmethod
    def get_san_distribution(cls) -> List[Dict[str, Any]]:
        """
        Get SAN count distribution (histogram buckets).
        
        Returns:
            List of dicts with bucket name and count
        """
        pipeline = [
            {'$project': {
                'sanCount': {'$size': {'$ifNull': ['$parsed.names', []]}}
            }},
            {'$bucket': {
                'groupBy': '$sanCount',
                'boundaries': [0, 1, 2, 4, 6, 11, 21, 51],
                'default': '50+',
                'output': {'count': {'$sum': 1}}
            }}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        # Map bucket IDs to readable labels
        bucket_labels = {
            0: '0',
            1: '1',
            2: '2-3',
            4: '4-5',
            6: '6-10',
            11: '11-20',
            21: '21-50',
            '50+': '50+'
        }
        
        distribution = []
        for r in results:
            bucket_id = r['_id']
            label = bucket_labels.get(bucket_id, str(bucket_id))
            distribution.append({
                'bucket': label,
                'count': r['count']
            })
        
        return distribution
    
    @classmethod
    def get_san_tld_breakdown(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get top TLDs from SAN entries (using dns_names from subject_alt_name).
        
        Args:
            limit: Number of top TLDs to return
            
        Returns:
            List of dicts with tld and count
        """
        pipeline = [
            # Filter documents that have dns_names
            {'$match': {
                'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
            }},
            # Unwind the dns_names array
            {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
            # Project and extract TLD from each dns name
            {'$project': {
                'dnsName': '$parsed.extensions.subject_alt_name.dns_names',
                # Extract TLD - get last part after last dot
                'tld': {
                    '$let': {
                        'vars': {
                            'parts': {'$split': ['$parsed.extensions.subject_alt_name.dns_names', '.']}
                        },
                        'in': {'$arrayElemAt': ['$$parts', -1]}
                    }
                }
            }},
            # Filter out wildcards and empty TLDs
            {'$match': {
                'tld': {'$exists': True, '$ne': None, '$ne': ''},
                'dnsName': {'$not': {'$regex': '^\\*'}}
            }},
            # Group by TLD
            {'$group': {
                '_id': {'$toLower': '$tld'},
                'count': {'$sum': 1}
            }},
            # Sort by count
            {'$sort': {'count': -1}},
            # Limit to top N
            {'$limit': limit}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        return [{'tld': f".{r['_id']}", 'count': r['count']} for r in results]
    
    @classmethod
    def get_san_wildcard_breakdown(cls) -> Dict[str, int]:
        """
        Get breakdown of wildcard vs standard SAN entries (using dns_names).
        
        Returns:
            Dict with wildcard and standard counts
        """
        pipeline = [
            # Filter documents that have dns_names
            {'$match': {
                'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
            }},
            # Unwind the dns_names array
            {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
            # Project to check if wildcard
            {'$project': {
                'isWildcard': {'$regexMatch': {'input': '$parsed.extensions.subject_alt_name.dns_names', 'regex': '^\\*\\.'}}
            }},
            # Group by wildcard status
            {'$group': {
                '_id': '$isWildcard',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        breakdown = {'wildcard': 0, 'standard': 0}
        for r in results:
            if r['_id'] is True:
                breakdown['wildcard'] = r['count']
            else:
                breakdown['standard'] = r['count']
        
        return breakdown
    
    # ========== TRENDS ANALYTICS METHODS ==========
    
    @classmethod
    def get_trends_stats(cls) -> Dict[str, Any]:
        """
        Get trend statistics for metric cards.
        
        Returns:
            Dict with:
            - velocity_30d: Certificates issued in last 30 days
            - velocity_change: % change vs previous 30 days
            - expiring_30d: Certificates expiring in next 30 days
            - expiring_change: % change vs previous month
            - modern_algo_percent: % using SHA256 or newer
            - strong_key_percent: % with strong keys
        """
        # Use same approach as get_dashboard_metrics for consistency
        now = cls.get_current_time_iso()
        now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
        sixty_days_ago = (datetime.now(timezone.utc) - timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # Velocity: Certificates issued in last 30 days (using same logic as filters)
        velocity_30d = cls.collection.count_documents({
            'parsed.validity.start': {'$gte': thirty_days_ago, '$lte': now}
        })
        
        # Previous 30 days for change calculation
        velocity_prev_30d = cls.collection.count_documents({
            'parsed.validity.start': {'$gte': sixty_days_ago, '$lt': thirty_days_ago}
        })
        
        velocity_change = 0
        if velocity_prev_30d > 0:
            velocity_change = round(((velocity_30d - velocity_prev_30d) / velocity_prev_30d) * 100, 1)
        
        # Expiring in next 30 days - SAME logic as get_dashboard_metrics
        expiring_30d = cls.collection.count_documents({
            'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}
        })
        
        # Modern algorithm % (exclude legacy: SHA1, MD5, MD2)
        total_certs = cls.collection.count_documents({})
        legacy_algos = ['SHA1-RSA', 'SHA1WithRSAEncryption', 'MD5-RSA', 'MD5WithRSAEncryption', 'MD2-RSA', 'SHA1-ECDSA']
        legacy_count = cls.collection.count_documents({
            'parsed.signature_algorithm.name': {'$in': legacy_algos}
        })
        modern_algo_count = total_certs - legacy_count
        modern_algo_percent = round((modern_algo_count / max(total_certs, 1)) * 100, 1)
        
        # Strong key % (RSA >= 2048 bits or ECDSA >= 256 bits)
        strong_key_count = cls.collection.count_documents({
            '$or': [
                # RSA keys >= 2048 bits
                {
                    'parsed.subject_key_info.key_algorithm.name': 'RSA',
                    'parsed.subject_key_info.rsa_public_key.length': {'$gte': 2048}
                },
                # ECDSA keys >= 256 bits (P-256, P-384, P-521)
                {
                    'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
                    'parsed.subject_key_info.ecdsa_public_key.length': {'$gte': 256}
                },
                # Ed25519/Ed448 always strong
                {
                    'parsed.subject_key_info.key_algorithm.name': {'$in': ['Ed25519', 'Ed448']}
                }
            ]
        })
        strong_key_percent = round((strong_key_count / max(total_certs, 1)) * 100, 1)
        
        return {
            'velocity_30d': velocity_30d,
            'velocity_change': velocity_change,
            'expiring_30d': expiring_30d,
            'modern_algo_percent': modern_algo_percent,
            'strong_key_percent': strong_key_percent,
            'total_certs': total_certs
        }
    
    @classmethod
    def get_key_size_timeline(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get key size distribution over time for animation.
        
        Returns monthly breakdown of key sizes for RSA and ECDSA certificates.
        Used for animated visualization of key strength evolution.
        """
        from dateutil.relativedelta import relativedelta
        
        now = datetime.now(timezone.utc)
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                       'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        timeline = []
        
        # Go back 'months' months from current
        for i in range(months - 1, -1, -1):
            target_date = now - relativedelta(months=i)
            start_of_month = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(seconds=1)
            
            start_str = start_of_month.strftime('%Y-%m-%dT%H:%M:%SZ')
            end_str = end_of_month.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Count certificates issued in this month by key size
            base_match = {
                'parsed.validity.start': {'$gte': start_str, '$lte': end_str}
            }
            
            # RSA 2048
            rsa_2048 = cls.collection.count_documents({
                **base_match,
                'parsed.subject_key_info.key_algorithm.name': 'RSA',
                'parsed.subject_key_info.rsa_public_key.length': 2048
            })
            
            # RSA 4096
            rsa_4096 = cls.collection.count_documents({
                **base_match,
                'parsed.subject_key_info.key_algorithm.name': 'RSA',
                'parsed.subject_key_info.rsa_public_key.length': 4096
            })
            
            # RSA other (smaller or larger)
            rsa_other = cls.collection.count_documents({
                **base_match,
                'parsed.subject_key_info.key_algorithm.name': 'RSA',
                'parsed.subject_key_info.rsa_public_key.length': {'$nin': [2048, 4096]}
            })
            
            # ECDSA 256
            ecdsa_256 = cls.collection.count_documents({
                **base_match,
                'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
                'parsed.subject_key_info.ecdsa_public_key.length': 256
            })
            
            # ECDSA 384
            ecdsa_384 = cls.collection.count_documents({
                **base_match,
                'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
                'parsed.subject_key_info.ecdsa_public_key.length': 384
            })
            
            month_label = f"{month_names[target_date.month - 1]} '{str(target_date.year)[2:]}"
            
            timeline.append({
                'month': month_label,
                'year': target_date.year,
                'monthNum': target_date.month,
                'rsa_2048': rsa_2048,
                'rsa_4096': rsa_4096,
                'rsa_other': rsa_other,
                'ecdsa_256': ecdsa_256,
                'ecdsa_384': ecdsa_384,
                'total': rsa_2048 + rsa_4096 + rsa_other + ecdsa_256 + ecdsa_384
            })
        
        return timeline
    
    @classmethod
    def get_expiration_forecast(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get certificate expiration count by month for upcoming months.
        
        Args:
            months: Number of months to forecast
            
        Returns:
            List of {month: 'Jan 2025', count: 123, year: 2025, monthNum: 1}
        """
        now = datetime.now(timezone.utc)
        now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = now + timedelta(days=months * 30)
        end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        pipeline = [
            {'$match': {
                'parsed.validity.end': {'$gte': now_str, '$lte': end_str}
            }},
            {'$project': {
                'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.end', 'onError': None}}},
                'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.end', 'onError': None}}}
            }},
            {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
            {'$group': {
                '_id': {'year': '$year', 'month': '$month'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        forecast = []
        for r in results:
            year = r['_id']['year']
            month = r['_id']['month']
            forecast.append({
                'month': f"{month_names[month]} {year}",
                'monthNum': month,
                'year': year,
                'count': r['count']
            })
        
        return forecast
    
    @classmethod
    def get_algorithm_adoption(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get signature algorithm distribution over time by issuance month.
        
        Args:
            months: Number of months to include
            
        Returns:
            List of {month: 'Jan 2025', sha256_rsa: 100, sha384_rsa: 20, ecdsa: 10, sha1_rsa: 5, other: 2}
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=months * 30)
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        pipeline = [
            {'$match': {
                'parsed.validity.start': {'$gte': start_str}
            }},
            {'$project': {
                'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
                'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
                'algo': '$parsed.signature_algorithm.name'
            }},
            {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
            {'$group': {
                '_id': {'year': '$year', 'month': '$month', 'algo': '$algo'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        # Group by month
        month_data = {}
        for r in results:
            key = (r['_id']['year'], r['_id']['month'])
            if key not in month_data:
                month_data[key] = {'sha256_rsa': 0, 'sha384_rsa': 0, 'ecdsa': 0, 'sha1_rsa': 0, 'other': 0}
            
            algo = (r['_id']['algo'] or '').upper()
            count = r['count']
            
            if 'SHA256' in algo and 'RSA' in algo:
                month_data[key]['sha256_rsa'] += count
            elif 'SHA384' in algo and 'RSA' in algo:
                month_data[key]['sha384_rsa'] += count
            elif 'ECDSA' in algo or 'EC' in algo:
                month_data[key]['ecdsa'] += count
            elif 'SHA1' in algo or 'SHA-1' in algo:
                month_data[key]['sha1_rsa'] += count
            else:
                month_data[key]['other'] += count
        
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        adoption = []
        for (year, month), data in sorted(month_data.items()):
            adoption.append({
                'month': f"{month_names[month]} {year}",
                'monthNum': month,
                'year': year,
                **data
            })
        
        return adoption
    
    @classmethod
    def get_validation_level_trends(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get validation level (DV/OV/EV) distribution over time by issuance month.
        
        Args:
            months: Number of months to include
            
        Returns:
            List of {month: 'Jan 2025', dv: 100, ov: 20, ev: 5, unknown: 2}
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=months * 30)
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        pipeline = [
            {'$match': {
                'parsed.validity.start': {'$gte': start_str}
            }},
            {'$project': {
                'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
                'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
                'level': {'$ifNull': ['$parsed.validation_level', 'Unknown']}
            }},
            {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
            {'$group': {
                '_id': {'year': '$year', 'month': '$month', 'level': '$level'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        # Group by month
        month_data = {}
        for r in results:
            key = (r['_id']['year'], r['_id']['month'])
            if key not in month_data:
                month_data[key] = {'dv': 0, 'ov': 0, 'ev': 0, 'unknown': 0}
            
            level = (r['_id']['level'] or 'Unknown').upper()
            count = r['count']
            
            if level == 'DV':
                month_data[key]['dv'] += count
            elif level == 'OV':
                month_data[key]['ov'] += count
            elif level == 'EV':
                month_data[key]['ev'] += count
            else:
                month_data[key]['unknown'] += count
        
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        trends = []
        for (year, month), data in sorted(month_data.items()):
            trends.append({
                'month': f"{month_names[month]} {year}",
                'monthNum': month,
                'year': year,
                **data
            })
        
        return trends

