from datetime import datetime, timezone
import time
from typing import List, Dict, Any, Optional
# from ./shared_apis/db_queries import SharedModels
from ..db import db, MongoDBClient


class OverviewModels:
    """Overview analytics methods for the frontend overview page."""

    collection = db['certificates']
    _vulnerability_score_cache: Dict[str, Dict[str, Any]] = {}
    _vulnerability_score_cache_seconds = 300

    @staticmethod
    def get_tld_country(domain: str) -> str:
        try:
            from certificates.shared_apis.db_queries import TLD_TO_COUNTRY
        except Exception:
            TLD_TO_COUNTRY = {}

        if not domain or not isinstance(domain, str):
            return 'Unknown'

        parts = domain.lower().strip('.').split('.')
        if len(parts) >= 2:
            two_part = '.'.join(parts[-2:])
            if two_part in TLD_TO_COUNTRY:
                return TLD_TO_COUNTRY[two_part]
            tld = parts[-1]
            return TLD_TO_COUNTRY.get(tld, 'Unknown')
        return 'Unknown'

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
        scoped_encryption = MongoDBClient.get_current_scope() not in ('', 'all', 'global')
        
        # Define all algorithm + key length combinations we want to count
        # Each has its specific compound index for MAXIMUM speed!
        algorithms_to_count = [
            # RSA variants - use idx_algo_rsa_length
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 2048, 'display': 'RSA 2048', 'hint': 'idx_scope_algo_rsa_length' if scoped_encryption else 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 4096, 'display': 'RSA 4096', 'hint': 'idx_scope_algo_rsa_length' if scoped_encryption else 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 3072, 'display': 'RSA 3072', 'hint': 'idx_scope_algo_rsa_length' if scoped_encryption else 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 1024, 'display': 'RSA 1024', 'hint': 'idx_scope_algo_rsa_length' if scoped_encryption else 'idx_algo_rsa_length'},
            {'algo': 'RSA', 'field': 'rsa_public_key.length', 'length': 8192, 'display': 'RSA 8192', 'hint': 'idx_scope_algo_rsa_length' if scoped_encryption else 'idx_algo_rsa_length'},
            
            # ECDSA variants - use idx_algo_ecdsa_length
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 256, 'display': 'ECDSA 256', 'hint': 'idx_scope_algo_ecdsa_length' if scoped_encryption else 'idx_algo_ecdsa_length'},
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 384, 'display': 'ECDSA 384', 'hint': 'idx_scope_algo_ecdsa_length' if scoped_encryption else 'idx_algo_ecdsa_length'},
            {'algo': 'ECDSA', 'field': 'ecdsa_public_key.length', 'length': 521, 'display': 'ECDSA 521', 'hint': 'idx_scope_algo_ecdsa_length' if scoped_encryption else 'idx_algo_ecdsa_length'},
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
                hint=config['hint']
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
        # ASCII only: when stdout is redirected to a log file on Windows it uses the
        # legacy charmap codec, and printing emoji raises UnicodeEncodeError -> API 500.
        print(f"[ENCRYPTION] OK - Completed ALL exact counts in {elapsed:.2f}s")
        
        return encryption_data

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
            {'$group': {'_id': '$domain'}},
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
    
    @staticmethod
    def _safe_list(value):
        return value if isinstance(value, list) else []

    @staticmethod
    def _count_zlint(zlint_data: Dict) -> Dict[str, int]:
        lints = zlint_data.get('lints', {}) if isinstance(zlint_data, dict) else {}
        errors = sum(1 for lint in lints.values() if isinstance(lint, dict) and lint.get('result') == 'error')
        warnings = sum(1 for lint in lints.values() if isinstance(lint, dict) and lint.get('result') == 'warn')
        return {'errors': errors, 'warnings': warnings}

    @staticmethod
    def _risk_level(score: int) -> str:
        if score >= 85:
            return 'Critical'
        if score >= 70:
            return 'High'
        if score >= 40:
            return 'Medium'
        return 'Low'

    @staticmethod
    def _get_shared_key_fingerprints() -> set:
        try:
            collection = MongoDBClient.get_results_db()['shared-keys-detailed']
            scope_filter = MongoDBClient.get_precomputed_scope_filter()
            query = {
                '$and': [
                    scope_filter,
                    {
                        '$or': [
                            {'doc_type': 'shared_key_group'},
                            {'doc_type': {'$exists': False}, '_id': {'$ne': 'metadata'}},
                        ]
                    }
                ]
            }
            return set(collection.distinct('public_key_hash', query))
        except Exception as exc:
            print(f"[VULNERABILITIES] Shared-key lookup unavailable: {exc}")
            return set()

    @staticmethod
    def _get_shared_key_context(public_key_hashes: List[str]) -> Dict[str, Dict[str, Any]]:
        hashes = [item for item in public_key_hashes if item]
        if not hashes:
            return {}
        try:
            collection = MongoDBClient.get_results_db()['shared-keys-detailed']
            query = {
                '$and': [
                    MongoDBClient.get_precomputed_scope_filter(),
                    {'public_key_hash': {'$in': hashes}},
                    {
                        '$or': [
                            {'doc_type': 'shared_key_group'},
                            {'doc_type': {'$exists': False}, '_id': {'$ne': 'metadata'}},
                        ]
                    }
                ]
            }
            docs = collection.find(query, {
                'public_key_hash': 1,
                'public_key_hash_short': 1,
                'certificate_count': 1,
                'sample_domains': 1,
                'key_type': 1,
                'issuers': 1,
                'risk_level': 1,
            })
            return {
                doc.get('public_key_hash'): {
                    'publicKeyHash': doc.get('public_key_hash', ''),
                    'publicKeyHashShort': doc.get('public_key_hash_short', ''),
                    'certificateCount': doc.get('certificate_count', 0),
                    'sampleDomains': doc.get('sample_domains', []),
                    'keyType': doc.get('key_type', 'Unknown'),
                    'issuers': doc.get('issuers', []),
                    'riskLevel': doc.get('risk_level', 'UNKNOWN'),
                }
                for doc in docs
                if doc.get('public_key_hash')
            }
        except Exception as exc:
            print(f"[VULNERABILITIES] Shared-key context unavailable: {exc}")
            return {}

    @staticmethod
    def _vulnerability_projection() -> Dict[str, int]:
        return {
            'domain': 1,
            'parsed.validity': 1,
            'parsed.subject_key_info': 1,
            'zlint': 1,
            'scope': 1,
        }

    @classmethod
    def _collect_indexed_vulnerability_candidates(
        cls,
        shared_fingerprints: set,
        per_signal_limit: int = 500,
    ) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        scoped = MongoDBClient.get_current_scope() not in ('', 'all', 'global')
        projection = cls._vulnerability_projection()
        docs_by_id: Dict[Any, Dict[str, Any]] = {}

        signal_queries = [
            (
                {'parsed.validity.end': {'$lt': now}},
                'idx_scope_validity_end' if scoped else 'idx_validity_end',
            ),
            (
                {'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}},
                'idx_scope_rsa_public_key_length' if scoped else 'idx_rsa_public_key_length',
            ),
            (
                {'parsed.validity.length': {'$gt': 398 * 86400}},
                'idx_scope_validity_length' if scoped else 'idx_validity_length',
            ),
            (
                {'zlint.errors_present': True},
                'idx_scope_zlint_errors' if scoped else 'idx_zlint_errors',
            ),
            (
                {'zlint.warnings_present': True},
                'idx_scope_zlint_warnings' if scoped else 'idx_zlint_warnings',
            ),
        ]

        if shared_fingerprints:
            signal_queries.append((
                {'parsed.subject_key_info.fingerprint_sha256': {'$in': list(shared_fingerprints)[:10000]}},
                'idx_scope_public_key_fingerprint' if scoped else 'idx_public_key_fingerprint',
            ))

        for query, hint in signal_queries:
            try:
                cursor = cls.collection.find(query, projection).hint(hint).limit(per_signal_limit)
            except Exception:
                cursor = cls.collection.find(query, projection).limit(per_signal_limit)
            for doc in cursor:
                docs_by_id[doc['_id']] = doc

        return list(docs_by_id.values())

    @classmethod
    def _risk_details(cls, doc: Dict, shared_fingerprints: set) -> Dict[str, Any]:
        from certificates.shared_apis.db_queries import SharedModels

        parsed = doc.get('parsed', {}) if isinstance(doc.get('parsed'), dict) else {}
        validity = parsed.get('validity', {}) if isinstance(parsed.get('validity'), dict) else {}
        key_info = parsed.get('subject_key_info', {}) if isinstance(parsed.get('subject_key_info'), dict) else {}
        key_algo = (key_info.get('key_algorithm', {}) or {}).get('name', 'Unknown')
        rsa_length = (key_info.get('rsa_public_key', {}) or {}).get('length')
        ecdsa_length = (key_info.get('ecdsa_public_key', {}) or {}).get('length')
        key_length = rsa_length or ecdsa_length or 0
        public_key_hash = key_info.get('fingerprint_sha256')
        validity_days = int((validity.get('length') or 0) / 86400) if validity.get('length') else 0
        status = SharedModels.get_status(validity.get('end', ''))
        zlint_counts = cls._count_zlint(doc.get('zlint', {}))

        score = 0
        factors = []
        positive_signals = []

        if status == 'EXPIRED':
            score += 30
            factors.append({'label': 'Expired certificate', 'points': 30})
        elif status == 'VALID':
            score -= 5
            positive_signals.append({'label': 'Certificate is currently valid', 'points': -5})

        if public_key_hash and public_key_hash in shared_fingerprints:
            score += 30
            factors.append({'label': 'Shared public key', 'points': 30})

        weak_encryption = (
            str(key_algo).upper() == 'RSA' and isinstance(rsa_length, int) and rsa_length < 2048
        )
        if weak_encryption:
            score += 20
            factors.append({'label': f'Weak encryption ({key_algo} {key_length})', 'points': 20})
        elif key_length >= 2048 or str(key_algo).upper() in ('ECDSA', 'EC'):
            score -= 5
            positive_signals.append({'label': f'Strong key ({key_algo} {key_length})', 'points': -5})

        if validity_days > 398:
            score += 10
            factors.append({'label': f'Long validity ({validity_days} days)', 'points': 10})
        elif 0 < validity_days <= 398:
            score -= 5
            positive_signals.append({'label': 'Modern validity period', 'points': -5})

        zlint_penalty = 0
        if zlint_counts['errors'] or zlint_counts['warnings']:
            zlint_penalty = min(
                10,
                zlint_counts['errors'] + ((zlint_counts['warnings'] + 1) // 2)
            )
        if zlint_penalty:
            score += zlint_penalty
            factors.append({
                'label': f"ZLint issues ({zlint_counts['errors']} errors, {zlint_counts['warnings']} warnings)",
                'points': zlint_penalty
            })
        else:
            score -= 5
            positive_signals.append({'label': 'No ZLint errors or warnings', 'points': -5})

        score = max(0, min(100, score))
        return {
            '_id': doc.get('_id'),
            'riskScore': score,
            'riskLevel': cls._risk_level(score),
            'riskFactors': factors,
            'positiveSignals': positive_signals,
            'validityDays': validity_days,
            'publicKeyHash': public_key_hash,
            'sharedPublicKey': bool(public_key_hash and public_key_hash in shared_fingerprints),
        }

    @classmethod
    def _score_certificate(cls, doc: Dict, shared_fingerprints: set) -> Dict[str, Any]:
        from certificates.shared_apis.db_queries import SharedModels

        serialized = SharedModels.serialize_certificate(doc)
        risk_details = cls._risk_details(doc, shared_fingerprints)
        risk_details.pop('_id', None)
        serialized.update(risk_details)
        return serialized

    @classmethod
    def _vulnerability_cache_key(cls) -> str:
        return f"{MongoDBClient.get_current_scope()}:{id(cls.collection)}"

    @staticmethod
    def _risk_summary(scored: List[Dict[str, Any]]) -> Dict[str, int]:
        return {
            'critical': sum(1 for item in scored if item.get('riskScore', 0) >= 85),
            'high': sum(1 for item in scored if 70 <= item.get('riskScore', 0) < 85),
            'medium': sum(1 for item in scored if 40 <= item.get('riskScore', 0) < 70),
            'low': sum(1 for item in scored if 0 < item.get('riskScore', 0) < 40),
            'warning': sum(1 for item in scored if any('zlint' in factor.get('label', '').lower() for factor in item.get('riskFactors', []))),
            'total': len(scored),
        }

    @classmethod
    def _get_ranked_vulnerability_scores(cls) -> Dict[str, Any]:
        cache_key = cls._vulnerability_cache_key()
        now_ts = time.time()
        cached = cls._vulnerability_score_cache.get(cache_key)
        if cached and now_ts - cached.get('created_at', 0) < cls._vulnerability_score_cache_seconds:
            return cached['data']

        shared_fingerprints = cls._get_shared_key_fingerprints()
        cursor = cls._collect_indexed_vulnerability_candidates(shared_fingerprints)
        scored = [
            risk for risk in (cls._risk_details(doc, shared_fingerprints) for doc in cursor)
            if risk.get('riskScore', 0) > 0
        ]
        scored.sort(key=lambda item: item.get('riskScore', 0), reverse=True)

        data = {
            'scored': scored,
            'summary': cls._risk_summary(scored),
            'shared_fingerprints': shared_fingerprints,
        }
        cls._vulnerability_score_cache[cache_key] = {
            'created_at': now_ts,
            'data': data,
        }
        return data

    @classmethod
    def get_vulnerabilities(
        cls,
        page: int = 1,
        page_size: int = 10,
        risk_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        ranked_data = cls._get_ranked_vulnerability_scores()
        shared_fingerprints = ranked_data['shared_fingerprints']
        all_scored = ranked_data['scored']
        scored = all_scored
        if risk_level:
            normalized_level = risk_level.strip().lower()
            scored = [
                item for item in scored
                if str(item.get('riskLevel', '')).lower() == normalized_level
            ]

        total = len(scored)
        start = max(0, (page - 1) * page_size)
        end = start + page_size
        page_records = scored[start:end]
        page_ids = [item.get('_id') for item in page_records if item.get('_id')]
        page_risk_by_id = {item.get('_id'): item for item in page_records}
        docs_by_id = {
            doc['_id']: doc
            for doc in cls.collection.find({'_id': {'$in': page_ids}})
        } if page_ids else {}
        page_items = []
        for cert_id in page_ids:
            doc = docs_by_id.get(cert_id)
            if not doc:
                continue
            item = cls._score_certificate(doc, shared_fingerprints)
            risk_details = dict(page_risk_by_id.get(cert_id, {}))
            risk_details.pop('_id', None)
            item.update(risk_details)
            page_items.append(item)

        shared_context = cls._get_shared_key_context([
            item.get('publicKeyHash') for item in page_items if item.get('sharedPublicKey')
        ])
        for item in page_items:
            public_key_hash = item.get('publicKeyHash')
            if public_key_hash and public_key_hash in shared_context:
                item['sharedKeyDetails'] = shared_context[public_key_hash]

        summary = ranked_data['summary']

        return {
            'certificates': page_items,
            'summary': summary,
            'pagination': {
                'page': page,
                'pageSize': page_size,
                'total': total,
                'totalPages': max(1, (total + page_size - 1) // page_size),
            },
            'formula': {
                'expired': 30,
                'sharedPublicKey': 30,
                'weakEncryption': 20,
                'validityOver398Days': 10,
                'zlint': '1 point per error plus 1 point per two warnings, capped at 10 total',
                'positiveSignals': 'Subtracts small points for valid, strong-key, modern-validity, and clean-zlint certificates',
            }
        }

    @classmethod
    def get_vulnearablities(
        cls,
        page: int = 1,
        page_size: int = 10,
        risk_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        return cls.get_vulnerabilities(page=page, page_size=page_size, risk_level=risk_level)

    @classmethod
    def get_future_risk(cls) -> List[Dict]:
        
        metrics = {
            'globalHealth': {
                'score': 82,
                'maxScore': 100,
                'status': 'AT_RISK',
                'lastUpdated': datetime.now(timezone.utc).strftime('%H:%M')
            },
            'activeCertificates': {
                'count': 1860,
                'total': 2000
            },
            'expiringSoon': {
                'count': 12,
                'daysThreshold': 30,
                'actionNeeded': True
            },
            'criticalVulnerabilities': {
                'count': 4,
                'new': 1
            },
            'expiredCertificates': {
                'count': 140
            }
        }

        expiring = metrics['expiringSoon']['count']
        critical = metrics['criticalVulnerabilities']['count']
        
        # Calculate risk level
        if critical > 5 or expiring > 20:
            risk_level = 'High'
            confidence = 92
        elif critical > 2 or expiring > 10:
            risk_level = 'Medium'
            confidence = 78
        else:
            risk_level = 'Low'
            confidence = 65
        
        result = {
            'confidenceLevel': confidence,
            'riskLevel': risk_level,
            'projectedThreats': [
                {
                    'id': '1',
                    'title': 'Weak Key Rotation',
                    'description': f'Predicted in 3 months',
                    'timeframe': '3 months',
                    'icon': 'key'
                },
                {
                    'id': '2',
                    'title': 'Signature Expiry',
                    'description': f'Watch for SHA-1 risk',
                    'timeframe': '6 months',
                    'icon': 'signature'
                }
            ]
        }
        return result

    
