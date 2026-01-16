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
        
        # Derive validation level from certificate policies
        validation_level = 'DV'  # Default
        policies = extensions.get('certificate_policies', [])
        if policies:
            policy_str = str(policies).lower()
            if 'extended-validation' in policy_str or 'ev-ssl' in policy_str:
                validation_level = 'EV'
            elif 'organization-validation' in policy_str or 'ov-ssl' in policy_str:
                validation_level = 'OV'
        
        # Build zlintDetails - only include error/warn lints if present
        zlint_details = {}
        if zlint.get('errors_present', False) or zlint.get('warnings_present', False):
            lints = zlint.get('lints', {})
            for lint_name, lint_data in lints.items():
                if isinstance(lint_data, dict):
                    result = lint_data.get('result', '')
                    if result in ('error', 'warn'):
                        zlint_details[lint_name] = lint_data
        
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
            'zlintDetails': zlint_details if zlint_details else None,  # Only include if has errors/warnings
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
                base_filter: Optional[Dict] = None) -> Dict:
        """Get paginated list of certificates with optional filters
        
        Args:
            expiring_days: Filter for certs expiring within N days (e.g., 30, 60, 90)
            validity_bucket: Filter by validity period bucket (e.g., "0-90", "90-365", "365-730", "730+")
            issued_month: Filter by issuance month (1-12)
            issued_year: Filter by issuance year (e.g., 2025)
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
        
        # Filter by expiring month/year - get certs that expire/expired in that month
        if expiring_month and expiring_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(expiring_year, expiring_month)
            month_start = f"{expiring_year}-{expiring_month:02d}-01T00:00:00Z"
            month_end = f"{expiring_year}-{expiring_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.end'] = {'$gte': month_start, '$lte': month_end}
        
        # Filter by issued month/year - get certs that were issued (validFrom) in that month
        if issued_month and issued_year:
            from calendar import monthrange
            # Get first and last day of the month
            _, last_day = monthrange(issued_year, issued_month)
            month_start = f"{issued_year}-{issued_month:02d}-01T00:00:00Z"
            month_end = f"{issued_year}-{issued_month:02d}-{last_day:02d}T23:59:59Z"
            query['parsed.validity.start'] = {'$gte': month_start, '$lte': month_end}
        
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
        print("total certificates call before",cls.get_current_time_iso())

        total = cls.collection.count_documents({})
        print("total certificates call after",cls.get_current_time_iso())
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
            {'$match': {'zlint.lints': {'$exists': True, '$ne': {}}}},
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