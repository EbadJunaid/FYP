# backend/certificates/shared_keys_models.py
# Shared Keys model utilities extracted from CertificateModel for better page separation.

from typing import List, Dict, Any
from ..db import MongoDBClient


class SharedKeyModel:
    """Model class for shared key analytics operations."""

    @staticmethod
    def _metadata_query() -> Dict[str, Any]:
        return {'scope': MongoDBClient.get_precomputed_scope(), 'doc_type': 'metadata'}

    @staticmethod
    def _group_scope_query() -> Dict[str, Any]:
        scope_filter = MongoDBClient.get_precomputed_scope_filter()
        return {
            '$and': [
                scope_filter,
                {
                    '$or': [
                        {'doc_type': 'shared_key_group'},
                        {
                            'doc_type': {'$exists': False},
                            '_id': {'$ne': 'metadata'}
                        }
                    ]
                }
            ]
        }

    @staticmethod
    def _group_detail_query(public_key_hash: str) -> Dict[str, Any]:
        query = SharedKeyModel._group_scope_query()
        query['$and'].append({'public_key_hash': public_key_hash})
        return query

    
    @classmethod
    def get_shared_key_stats(cls) -> Dict[str, Any]:
        """
        Get statistics for shared public keys.
        Groups certificates by public key fingerprint and finds groups with multiple distinct certs.
        
        Returns:
            - unique_keys: Total distinct public key fingerprints
            - shared_key_groups: Count of public keys shared by truly different certificates
            - certificates_at_risk: Total certificates in shared key groups
            - most_affected_domain: Domain with most certs sharing a single key
        """
        pipeline_groups = [
            {'$match': {
                'parsed.subject_key_info.fingerprint_sha256': {'$exists': True, '$ne': None},
                'parsed.fingerprint_sha256': {'$exists': True, '$ne': None}
            }},
            # Group by public key fingerprint, collect unique cert fingerprints
            {'$group': {
                '_id': '$parsed.subject_key_info.fingerprint_sha256',
                'cert_fingerprints': {'$addToSet': '$parsed.fingerprint_sha256'},
                'cert_count': {'$sum': 1},
                'domains': {'$addToSet': {'$arrayElemAt': ['$parsed.names', 0]}}
            }},
            # Add field for count of distinct certs
            {'$addFields': {
                'distinct_certs': {'$size': '$cert_fingerprints'}
            }},
            {'$facet': {
                'all_keys': [{'$count': 'total'}],
                'shared_keys': [
                    # Only keys with 2+ distinct certificates
                    {'$match': {'distinct_certs': {'$gt': 1}}},
                    {'$group': {
                        '_id': None,
                        'group_count': {'$sum': 1},
                        'cert_count': {'$sum': '$cert_count'}
                    }}
                ],
                'top_domain': [
                    {'$match': {'distinct_certs': {'$gt': 1}}},
                    {'$unwind': '$domains'},
                    {'$group': {
                        '_id': '$domains',
                        'key_fingerprint': {'$first': '$_id'},
                        'count': {'$max': '$distinct_certs'}
                    }},
                    {'$sort': {'count': -1}},
                    {'$limit': 1}
                ]
            }}
        ]
        
        result = list(cls.collection.aggregate(pipeline_groups, allowDiskUse=True))
        
        if not result:
            return {
                'unique_keys': 0,
                'shared_key_groups': 0,
                'certificates_at_risk': 0,
                'most_affected_domain': {'name': 'N/A', 'count': 0}
            }
        
        data = result[0]
        unique_keys = data['all_keys'][0]['total'] if data['all_keys'] else 0
        shared_info = data['shared_keys'][0] if data['shared_keys'] else {'group_count': 0, 'cert_count': 0}
        top_domain = data['top_domain'][0] if data['top_domain'] else {'_id': 'N/A', 'count': 0}
        
        return {
            'unique_keys': unique_keys,
            'shared_key_groups': shared_info.get('group_count', 0),
            'certificates_at_risk': shared_info.get('cert_count', 0),
            'most_affected_domain': {
                'name': top_domain.get('_id', 'N/A'),
                'count': top_domain.get('count', 0)
            }
        }

    @classmethod
    def get_shared_key_distribution(cls) -> List[Dict[str, Any]]:
        """
        Get distribution of shared key group sizes for histogram.
        Only counts groups where multiple distinct certificates share a key.
        
        Returns list of buckets: "2", "3-5", "6-10", "10+"
        """
        pipeline = [
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
            {'$match': {'distinct_certs': {'$gt': 1}}},  # Only truly shared keys
            {'$bucket': {
                'groupBy': '$distinct_certs',
                'boundaries': [2, 3, 6, 11, 1000000],
                'default': 'overflow',
                'output': {'groups': {'$sum': 1}}
            }}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        # Map to readable labels
        bucket_labels = {2: '2', 3: '3-5', 6: '6-10', 11: '10+'}
        distribution = []
        
        for r in results:
            bucket_id = r['_id']
            label = bucket_labels.get(bucket_id, str(bucket_id))
            distribution.append({
                'bucket': label,
                'count': r['groups']
            })
        
        # Ensure all buckets exist
        all_labels = ['2', '3-5', '6-10', '10+']
        existing = {d['bucket'] for d in distribution}
        for label in all_labels:
            if label not in existing:
                distribution.append({'bucket': label, 'count': 0})
        
        # Sort by bucket order
        order = {'2': 0, '3-5': 1, '6-10': 2, '10+': 3}
        distribution.sort(key=lambda x: order.get(x['bucket'], 99))
        
        return distribution

    @classmethod
    def get_shared_keys_by_issuer(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get count of shared-key certificates by issuer.
        Only counts certificates that share a public key with truly different certificates.
        
        Returns list of issuers with their count of certificates involved in key reuse.
        """
        # First find all public key fingerprints that have 2+ distinct cert fingerprints
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
        
        if not shared_fingerprints:
            return []
        
        # Now count by issuer for certs with these fingerprints
        issuer_pipeline = [
            {'$match': {
                'parsed.subject_key_info.fingerprint_sha256': {'$in': shared_fingerprints}
            }},
            {'$group': {
                '_id': {'$ifNull': [{'$arrayElemAt': ['$parsed.issuer.organization', 0]}, 'Unknown']},
                'shared_certs': {'$sum': 1}
            }},
            {'$sort': {'shared_certs': -1}},
            {'$limit': limit}
        ]
        
        results = list(cls.collection.aggregate(issuer_pipeline, allowDiskUse=True))
        
        return [{'issuer': r['_id'], 'shared_certs': r['shared_certs']} for r in results]

    @classmethod
    def get_shared_key_timeline(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        Get timeline of certificates joining shared key groups by issuance month.
        Only includes certificates that share keys with truly different certificates.
        
        Shows new certs issued per month that are part of a shared key group.
        """
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=months * 30)
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        # First find truly shared key fingerprints
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
        
        if not shared_fingerprints:
            return []
        
        # Get timeline of shared-key certs by issuance month
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
        
        results = list(cls.collection.aggregate(timeline_pipeline, allowDiskUse=True))
        
        month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        timeline = []
        for r in results:
            year = r['_id']['year']
            month = r['_id']['month']
            timeline.append({
                'month': f"{month_names[month]} {year}",
                'monthNum': month,
                'year': year,
                'count': r['count']
            })
        
        return timeline

    @classmethod
    def get_shared_key_heatmap(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get issuer x key-type matrix for heatmap.
        Only includes certificates with truly shared keys.
        
        Returns list of {issuer, key_type, count} for certificates in shared key groups.
        """
        # First find truly shared key fingerprints
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
        
        if not shared_fingerprints:
            return []
        
        # Get heatmap data
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
        
        results = list(cls.collection.aggregate(heatmap_pipeline, allowDiskUse=True))
        
        # Get top issuers
        issuer_totals = {}
        for r in results:
            issuer = r['_id']['issuer']
            issuer_totals[issuer] = issuer_totals.get(issuer, 0) + r['count']
        
        top_issuers = sorted(issuer_totals.keys(), key=lambda x: issuer_totals[x], reverse=True)[:limit]
        
        # Filter results to top issuers
        heatmap = []
        for r in results:
            if r['_id']['issuer'] in top_issuers:
                heatmap.append({
                    'issuer': r['_id']['issuer'],
                    'key_type': r['_id']['key_type'],
                    'count': r['count']
                })
        
        return heatmap


    @classmethod
    def get_shared_key_stats_fast(cls) -> Dict[str, Any]:
        """
        ⚡ OPTIMIZED: Get shared key statistics from shared-keys-detailed collection.
        
        Returns:
            Dict containing:
                - total_public_keys: Total distinct public keys (including shared ones)
                - unique_public_keys: Keys used by only one certificate (non-shared)
                - shared_key_groups: Count of public keys shared by different certificates
                - certificates_at_risk: Total certificates in shared key groups
                - most_affected_domain: Domain with most certs sharing a key
        """
        shared_keys_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        certs_collection = MongoDBClient.get_results_db()['certificates']
        
        metadata = shared_keys_collection.find_one(cls._metadata_query())
        if not metadata and MongoDBClient.get_precomputed_scope() == 'all':
            metadata = shared_keys_collection.find_one({'_id': 'metadata'})
        if not metadata:
            raise ValueError("Shared keys data not computed. Run compute_shared_keys.py first.")
        
        total_public_keys = metadata.get('total_public_keys', 0)
        unique_public_keys = metadata.get('unique_public_keys', 0)
        
        group_query = cls._group_scope_query()
        shared_key_groups = shared_keys_collection.count_documents(group_query)
        
        pipeline = [
            {'$match': group_query},
            {'$group': {'_id': None, 'total': {'$sum': '$certificate_count'}}}
        ]
        result = list(shared_keys_collection.aggregate(pipeline))
        certificates_at_risk = result[0]['total'] if result else 0
        
        most_affected = shared_keys_collection.find_one(
            group_query,
            sort=[('most_affected_domain.sans_count', -1)]
        )
        
        most_affected_domain = {
            'name': most_affected['most_affected_domain']['domain'] if most_affected and 'most_affected_domain' in most_affected else 'N/A',
            'count': most_affected['most_affected_domain']['sans_count'] if most_affected and 'most_affected_domain' in most_affected else 0
        }
        
        return {
            'total_public_keys': total_public_keys,
            'unique_public_keys': unique_public_keys,
            'shared_key_groups': shared_key_groups,
            'certificates_at_risk': certificates_at_risk,
            'most_affected_domain': most_affected_domain
        }

    @classmethod
    def get_shared_key_distribution_fast(cls) -> List[Dict[str, Any]]:
        """
        ⚡ OPTIMIZED: Get shared key distribution from shared-keys-detailed collection.
        
        Returns:
            List of distribution buckets (e.g., "2 certs", "3-5 certs", etc.)
        """
        shared_keys_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        group_query = cls._group_scope_query()
        
        buckets = [
            {'id': 1, 'label': '2 certs', 'min': 2, 'max': 2},
            {'id': 2, 'label': '3-5 certs', 'min': 3, 'max': 5},
            {'id': 3, 'label': '6-10 certs', 'min': 6, 'max': 10},
            {'id': 4, 'label': '11-20 certs', 'min': 11, 'max': 20},
            {'id': 5, 'label': '21-50 certs', 'min': 21, 'max': 50},
            {'id': 6, 'label': '51-100 certs', 'min': 51, 'max': 100},
            {'id': 7, 'label': '101+ certs', 'min': 101, 'max': 999999}
        ]
        
        results = []
        for bucket in buckets:
            count = shared_keys_collection.count_documents({
                '$and': [
                    group_query,
                    {'certificate_count': {'$gte': bucket['min'], '$lte': bucket['max']}}
                ]
            })
            if count > 0:
                results.append({
                    'bucket': bucket['label'],
                    'count': count
                })
        
        return results

    @classmethod
    def get_shared_keys_by_issuer_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ⚡ OPTIMIZED: Get shared keys by issuer from shared-keys-detailed collection.
        """
        shared_keys_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        
        pipeline = [
            {'$match': cls._group_scope_query()},
            {'$unwind': '$issuers'},
            {'$group': {
                '_id': '$issuers.organization',
                'shared_certs': {'$sum': '$issuers.certificate_count'}
            }},
            {'$sort': {'shared_certs': -1}},
            {'$limit': limit},
            {'$project': {
                '_id': 0,
                'issuer': '$_id',
                'shared_certs': 1
            }}
        ]
        
        results = list(shared_keys_collection.aggregate(pipeline))
        return results

    @classmethod
    def get_shared_key_timeline_fast(cls, months: int = 12) -> List[Dict[str, Any]]:
        """
        ⚡ Get shared key timeline from certificates collection.
        """
        from datetime import datetime, timedelta
        certs_collection = MongoDBClient.get_results_db()['certificates']
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        shared_keys_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        shared_hashes = shared_keys_collection.distinct(
            'public_key_hash',
            cls._group_scope_query()
        )
        
        if not shared_hashes:
            return []
        
        pipeline = [
            {
                '$match': {
                    'public_key_hash_sha256': {'$in': shared_hashes},
                    'scanned_at': {'$gte': start_date, '$lte': end_date}
                }
            },
            {
                '$group': {
                    '_id': {
                        'year': {'$year': '$scanned_at'},
                        'month': {'$month': '$scanned_at'}
                    },
                    'count': {'$sum': 1}
                }
            },
            {'$sort': {'_id.year': 1, '_id.month': 1}}
        ]
        
        results = list(certs_collection.aggregate(pipeline))
        
        month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        formatted = []
        for r in results:
            month_num = r['_id']['month']
            year = r['_id']['year']
            formatted.append({
                'month': f"{month_names[month_num - 1]} {year}",
                'monthNum': month_num,
                'year': year,
                'count': r['count']
            })
        
        return formatted[-months:] if len(formatted) > months else formatted

    @classmethod
    def get_shared_key_heatmap_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ⚡ Get shared key heatmap (issuer x key_type) from shared-keys-detailed collection.
        """
        shared_keys_collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        
        pipeline = [
            {'$match': cls._group_scope_query()},
            {'$unwind': '$issuers'},
            {'$group': {
                '_id': {
                    'issuer': '$issuers.organization',
                    'key_type': '$key_type'
                },
                'count': {'$sum': '$issuers.certificate_count'}
            }},
            {'$project': {
                '_id': 0,
                'issuer': '$_id.issuer',
                'key_type': '$_id.key_type',
                'count': 1
            }}
        ]
        
        all_results = list(shared_keys_collection.aggregate(pipeline))
        
        if not all_results:
            return []
        
        issuer_totals = {}
        for r in all_results:
            issuer = r['issuer']
            issuer_totals[issuer] = issuer_totals.get(issuer, 0) + r['count']
        
        top_issuers = sorted(issuer_totals.keys(), key=lambda x: issuer_totals[x], reverse=True)[:limit]
        filtered = [r for r in all_results if r['issuer'] in top_issuers]
        
        return filtered

    @classmethod
    def get_shared_keys_list(cls, page: int = 1, page_size: int = 10,
                             sort_by: str = 'certificate_count', sort_order: str = 'desc',
                             risk_level: str = None, key_type: str = None,
                             min_cert_count: int = None, issuer: str = None) -> Dict[str, Any]:
        """
        Get paginated list of shared key groups for table view.
        """
        collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        
        query = cls._group_scope_query()
        if risk_level:
            query['$and'].append({'risk_level': risk_level})
        if key_type:
            query['$and'].append({'key_type': key_type})
        if min_cert_count:
            query['$and'].append({'certificate_count': {'$gte': min_cert_count}})
        if issuer:
            query['$and'].append({'issuers.organization': issuer})
        
        total = collection.count_documents(query)
        skip = (page - 1) * page_size
        total_pages = (total + page_size - 1) // page_size
        sort_direction = -1 if sort_order == 'desc' else 1
        
        results = list(collection.find(
            query,
            {
                '_id': 1,
                'public_key_hash': 1,
                'public_key_hash_short': 1,
                'certificate_count': 1,
                'total_domains': 1,
                'sample_domains': 1,
                'total_sans': 1,
                'sample_sans': 1,
                'key_type': 1,
                'issuers': 1,
                'issuer_count': 1,
                'risk_level': 1,
                'most_affected_domain': 1,
                'computed_at': 1
            }
        ).sort(sort_by, sort_direction).skip(skip).limit(page_size))
        
        formatted_results = []
        for doc in results:
            formatted_results.append({
                'public_key_hash': doc.get('public_key_hash', ''),
                'public_key_hash_short': doc.get('public_key_hash_short', ''),
                'certificate_count': doc.get('certificate_count', 0),
                'total_domains': doc.get('total_domains', 0),
                'sample_domains': doc.get('sample_domains', []),
                'total_sans': doc.get('total_sans', 0),
                'sample_sans': doc.get('sample_sans', []),
                'key_type': doc.get('key_type', 'Unknown'),
                'issuers': doc.get('issuers', []),
                'issuer_count': doc.get('issuer_count', 0),
                'risk_level': doc.get('risk_level', 'UNKNOWN'),
                'most_affected_domain': doc.get('most_affected_domain', {}),
                'computed_at': doc.get('computed_at').isoformat() if doc.get('computed_at') else None
            })
        
        return {
            'results': formatted_results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': total,
                'total_pages': total_pages,
                'has_next': page < total_pages,
                'has_prev': page > 1
            }
        }

    @classmethod
    def get_shared_key_detail(cls, public_key_hash: str) -> Dict[str, Any]:
        """
        Get full details for a specific shared key group.
        """
        collection = MongoDBClient.get_results_db()['shared-keys-detailed']
        
        doc = collection.find_one(cls._group_detail_query(public_key_hash))
        if not doc and MongoDBClient.get_precomputed_scope() == 'all':
            doc = collection.find_one({'_id': public_key_hash})
        if not doc or doc.get('doc_type') == 'metadata' or doc.get('_id') == 'metadata':
            raise ValueError(f"Shared key group not found: {public_key_hash}")
        
        return {
            'public_key_hash': doc.get('public_key_hash', ''),
            'public_key_hash_short': doc.get('public_key_hash_short', ''),
            'certificate_count': doc.get('certificate_count', 0),
            'total_domains': doc.get('total_domains', 0),
            'sample_domains': doc.get('sample_domains', []),
            'total_sans': doc.get('total_sans', 0),
            'sample_sans': doc.get('sample_sans', []),
            'unique_sans': doc.get('unique_sans', []),
            'key_algorithm': doc.get('key_algorithm', 'Unknown'),
            'key_size': doc.get('key_size', 0),
            'key_type': doc.get('key_type', 'Unknown'),
            'issuers': doc.get('issuers', []),
            'issuer_count': doc.get('issuer_count', 0),
            'risk_level': doc.get('risk_level', 'UNKNOWN'),
            'risk_factors': doc.get('risk_factors', []),
            'most_affected_domain': doc.get('most_affected_domain', {}),
            'certificates': doc.get('certificates', []),
            'computed_at': doc.get('computed_at').isoformat() if doc.get('computed_at') else None,
            'last_updated': doc.get('last_updated').isoformat() if doc.get('last_updated') else None
        }
