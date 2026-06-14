# backend/certificates/san_models.py
# SAN analytics model utilities extracted from CertificateModel for better page separation.

from typing import List, Dict, Any
from bson import ObjectId
from ..db import db, MongoDBClient


class SANModel:
    """Model class for SAN analytics operations."""

    collection = db['certificates']

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
                'boundaries': [0, 1, 2, 4, 6, 11, 31, 51],
                'default': '50+',
                'output': {'count': {'$sum': 1}}
            }}
        ]
        
        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))
        
        bucket_labels = {
            0: '0',
            1: '1',
            2: '2-3',
            4: '4-5',
            6: '6-10',
            11: '11-30',
            31: '31-50',
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
            {'$match': {
                'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
            }},
            {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
            {'$project': {
                'dnsName': '$parsed.extensions.subject_alt_name.dns_names',
                'tld': {
                    '$let': {
                        'vars': {
                            'parts': {'$split': ['$parsed.extensions.subject_alt_name.dns_names', '.']}
                        },
                        'in': {'$arrayElemAt': ['$$parts', -1]}
                    }
                }
            }},
            {'$match': {
                'tld': {'$exists': True, '$ne': None, '$ne': ''},
                'dnsName': {'$not': {'$regex': '^\\*'}}
            }},
            {'$group': {
                '_id': {'$toLower': '$tld'},
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}},
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
            {'$match': {
                'parsed.extensions.subject_alt_name.dns_names': {'$exists': True, '$ne': []}
            }},
            {'$unwind': '$parsed.extensions.subject_alt_name.dns_names'},
            {'$project': {
                'isWildcard': {'$regexMatch': {'input': '$parsed.extensions.subject_alt_name.dns_names', 'regex': '^\\*\\.'}}
            }},
            {'$group': {
                '_id': '$isWildcard',
                'count': {'$sum': 1}
            }}
        ]
        
        results = list(cls.collection.aggregate(
            pipeline,
            hint='idx_san_dns_names',
            allowDiskUse=True
        ))
        
        breakdown = {'wildcard': 0, 'standard': 0}
        for r in results:
            if r['_id'] is True:
                breakdown['wildcard'] = r['count']
            else:
                breakdown['standard'] = r['count']
        
        return breakdown

    # @classmethod
    # def get_san_stats_fast(cls) -> Dict[str, Any]:
    #     """
    #     ⚡ OPTIMIZED: Get SAN statistics from pre-computed materialized view.
        
    #     Returns:
    #         Dict containing:
    #             - total_sans: Total number of SAN entries across all certs
    #             - avg_sans_per_cert: Average SANs per certificate
    #             - wildcard_certs: Number of certs with wildcard SANs
    #             - multi_domain_certs: Number of certs with 5+ SANs
    #     """
    #     stats_collection = MongoDBClient.get_results_db()['san-stats']
    #     print("I am in get_san_stats_fast ")
        
    #     doc = stats_collection.find_one({'_id': 'san_stats'})
        
    #     if not doc:
    #         raise ValueError("SAN stats not computed. Run compute_san_stats.py first.")
        
    #     return {
    #         'total_sans': doc.get('total_sans', 0),
    #         'avg_sans_per_cert': doc.get('avg_sans_per_cert', 0.0),
    #         'wildcard_certs': doc.get('wildcard_certs', 0),
    #         'multi_domain_certs': doc.get('multi_domain_certs', 0)
    #     }

    # @classmethod
    # def get_san_distribution_fast(cls) -> List[Dict[str, Any]]:
    #     """
    #     ⚡ OPTIMIZED: Get SAN distribution from pre-computed materialized view.
        
    #     Returns:
    #         List of dicts with bucket and count
    #     """
    #     print("I am in get_san_distribution_fast ")
    #     distribution_collection = MongoDBClient.get_results_db()['san-distribution']
        
    #     results = list(distribution_collection.find(
    #         {'_id': {'$ne': 'metadata'}},
    #         {'_id': 0, 'bucket': 1, 'count': 1}
    #     ).sort('bucket_id', 1))
        
    #     if not results:
    #         raise ValueError("SAN distribution not computed. Run compute_san_distribution.py first.")
        
    #     return results

    # @classmethod
    # def get_san_tld_breakdown_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
    #     """
    #     ⚡ OPTIMIZED: Get TLD breakdown from pre-computed materialized view.
        
    #     Args:
    #         limit: Maximum number of TLDs to return (default 10)
        
    #     Returns:
    #         List of dicts with tld and count
    #     """
    #     print("I am in get_san_tld_breakdown_fast ")

    #     tld_collection = MongoDBClient.get_results_db()['san-tld-certs']
        
    #     results = list(tld_collection.find(
    #         {},
    #         {'_id': 1, 'certificate_count': 1}
    #     ).sort('certificate_count', -1).limit(limit))
        
    #     if not results:
    #         raise ValueError("SAN TLD data not computed. Run compute-san-filtered-lists.py first.")
        
    #     return [{
    #         'tld': doc['_id'],
    #         'count': doc['certificate_count']
    #     } for doc in results]

    # @classmethod
    # def get_san_wildcard_breakdown_fast(cls) -> Dict[str, int]:
    #     """
    #     ⚡ OPTIMIZED: Get wildcard breakdown from pre-computed stats.
        
    #     Returns:
    #         Dict with wildcard and standard counts
    #     """
    #     print("I am in get_san_wildcard_breakdown_fast ")

    #     stats_collection = MongoDBClient.get_results_db()['san-stats']
        
    #     doc = stats_collection.find_one({'_id': 'san_stats'})
        
    #     if not doc:
    #         raise ValueError("SAN stats not computed. Run compute-san-filtered-lists.py first.")
        
    #     wildcard = doc.get('wildcard_certs', 0)
    #     total = doc.get('total_certs', 0)
    #     standard = max(0, total - wildcard)
        
    #     return {
    #         'wildcard': wildcard,
    #         'standard': standard
    #     }

    # @classmethod
    # def get_san_filtered_certs_fast(cls, filter_type: str, filter_value: str = None,
    #                                  page: int = 1, page_size: int = 50) -> Dict[str, Any]:
    #     """
    #     ⚡ OPTIMIZED: Get filtered certificates from pre-computed collections.
        
    #     Args:
    #         filter_type: Type of filter - 'wildcard', 'multi-domain', 'san-count', 'tld'
    #         filter_value: Value for filter (e.g., '50+' for san-count, '.com' for tld)
    #         page: Page number (1-indexed)
    #         page_size: Number of results per page
        
    #     Returns:
    #         Dict with:
    #         - certificates: List of certificate references
    #         - total: Total count
    #         - page: Current page
    #         - page_size: Page size
    #         - has_more: Whether more pages exist
    #     """
    #     if filter_type == 'wildcard':
    #         collection = MongoDBClient.get_results_db()['san-wildcard-certs']
    #         query = {}
    #     elif filter_type == 'standard':
    #         collection = MongoDBClient.get_results_db()['san-standard-certs']
    #         query = {}
    #     elif filter_type == 'multi-domain':
    #         collection = MongoDBClient.get_results_db()['san-multi-domain-certs']
    #         query = {}
    #     elif filter_type == 'san-count':
    #         print("I am in san-count filter of get_san_filtered_certs_fast ")
    #         if not filter_value:
    #             raise ValueError("filter_value required for san-count filter")
    #         collection = MongoDBClient.get_results_db()['san-count-groups']
    #         try:
    #             doc = collection.find_one({'_id': filter_value})
    #             if not doc:
    #                 return {
    #                     'certificates': [],
    #                     'total': 0,
    #                     'page': page,
    #                     'page_size': page_size,
    #                     'has_more': False
    #                 }
    #             total = doc.get('total_count', doc.get('certificate_count', 0))
    #             certificates = doc.get('certificates', [])
    #             skip = (page - 1) * page_size
    #             paginated_certs = certificates[skip:skip + page_size]
                
    #             from bson import ObjectId
    #             for cert in paginated_certs:
    #                 if 'cert_id' in cert and isinstance(cert['cert_id'], ObjectId):
    #                     cert['cert_id'] = str(cert['cert_id'])
    #                 if '_id' in cert and isinstance(cert['_id'], ObjectId):
    #                     cert['_id'] = str(cert['_id'])
                
    #             return {
    #                 'certificates': paginated_certs,
    #                 'total': total,
    #                 'page': page,
    #                 'page_size': page_size,
    #                 'has_more': skip + len(paginated_certs) < total
    #             }
    #         except Exception as e:
    #             print(f"Error in SAN count filter: {str(e)}")
    #             import traceback
    #             traceback.print_exc()
    #             raise
    #     elif filter_type == 'tld':
    #         if not filter_value:
    #             raise ValueError("filter_value required for tld filter")
    #         collection = MongoDBClient.get_results_db()['san-tld-certs']
    #         try:
    #             doc = collection.find_one({'_id': filter_value})
    #             if not doc:
    #                 return {
    #                     'certificates': [],
    #                     'total': 0,
    #                     'page': page,
    #                     'page_size': page_size,
    #                     'has_more': False
    #                 }
    #             total = doc.get('total_count', doc.get('certificate_count', 0))
    #             certificates = doc.get('certificates', [])
    #             skip = (page - 1) * page_size
    #             paginated_certs = certificates[skip:skip + page_size]
                
    #             from bson import ObjectId
    #             for cert in paginated_certs:
    #                 if 'cert_id' in cert and isinstance(cert['cert_id'], ObjectId):
    #                     cert['cert_id'] = str(cert['cert_id'])
    #                 if '_id' in cert and isinstance(cert['_id'], ObjectId):
    #                     cert['_id'] = str(cert['_id'])
                
    #             return {
    #                 'certificates': paginated_certs,
    #                 'total': total,
    #                 'page': page,
    #                 'page_size': page_size,
    #                 'has_more': skip + len(paginated_certs) < total
    #             }
    #         except Exception as e:
    #             print(f"Error in TLD filter: {str(e)}")
    #             import traceback
    #             traceback.print_exc()
    #             raise
    #     else:
    #         raise ValueError(f"Invalid filter_type: {filter_type}")
        
    #     skip = (page - 1) * page_size
    #     total = collection.count_documents(query)
        
    #     certificates = list(collection.find(query)
    #                       .sort('san_count', -1)
    #                       .skip(skip)
    #                       .limit(page_size))
        
    #     for cert in certificates:
    #         if '_id' in cert:
    #             cert['_id'] = str(cert['_id'])
    #         if 'cert_id' in cert:
    #             cert['cert_id'] = str(cert['cert_id'])
        
    #     return {
    #         'certificates': certificates,
    #         'total': total,
    #         'page': page,
    #         'page_size': page_size,
    #         'has_more': skip + len(certificates) < total
    #     }

    # =========================================================================
    # NEW SAN-ANALYSIS IMPLEMENTATION
    # -------------------------------------------------------------------------
    # The methods below intentionally keep the same names as the legacy fast
    # methods above. Python uses the later definition, so these methods now read
    # from one collection/document:
    #
    #   <results_db>.san-analysis / {"_id": "san_analysis"}
    #
    # The old code above is left in place for comparison and easy rollback.
    # =========================================================================

    @classmethod
    def _get_san_analysis_doc(cls) -> Dict[str, Any]:
        collection = MongoDBClient.get_results_db()['san-analysis']
        doc = collection.find_one({'_id': 'san_analysis'})
        if not doc:
            raise ValueError("SAN analytics not computed. Run generic-compute-san-analytics.py first.")
        return doc

    @staticmethod
    def _find_san_bucket(doc: Dict[str, Any], bucket: str) -> Dict[str, Any]:
        for item in doc.get('bucket_groups', []):
            if item.get('bucket') == bucket:
                return item
        return {'bucket': bucket, 'count': 0, 'certificate_ids': [], 'has_more': False}

    @staticmethod
    def _find_san_tld(doc: Dict[str, Any], tld: str) -> Dict[str, Any]:
        normalized = tld if tld.startswith('.') else f'.{tld}'
        for item in doc.get('tlds', []):
            if item.get('tld') == normalized:
                return item
        return {'tld': normalized, 'count': 0, 'certificate_ids': [], 'has_more': False}

    @staticmethod
    def _get_sans_from_cert(cert: Dict[str, Any]) -> List[str]:
        sans = (
            cert.get('parsed', {})
            .get('extensions', {})
            .get('subject_alt_name', {})
            .get('dns_names', [])
        )
        if not isinstance(sans, list):
            return []
        return [san for san in sans if san and isinstance(san, str)]

    @staticmethod
    def _count_zlint_vulnerabilities(zlint_data: Dict[str, Any]) -> Dict[str, int]:
        if not zlint_data or 'lints' not in zlint_data:
            return {'errors': 0, 'warnings': 0}

        lints = zlint_data.get('lints', {})
        return {
            'errors': sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'error'),
            'warnings': sum(1 for v in lints.values() if isinstance(v, dict) and v.get('result') == 'warn'),
        }

    @classmethod
    def _format_zlint_vulnerabilities(cls, zlint_data: Dict[str, Any]) -> str:
        counts = cls._count_zlint_vulnerabilities(zlint_data)
        if counts['errors'] > 0:
            return f"{counts['errors']} Critical"
        if counts['warnings'] > 0:
            return f"{counts['warnings']} Warning"
        return "0 Found"

    @staticmethod
    def _pick_cert_country(cert: Dict[str, Any]) -> str:
        countries = cert.get('parsed', {}).get('issuer', {}).get('country', [])
        if not countries:
            countries = cert.get('parsed', {}).get('subject', {}).get('country', [])
        if isinstance(countries, list):
            return countries[0] if countries else 'Unknown'
        if isinstance(countries, str):
            return countries
        return 'Unknown'

    @classmethod
    def _serialize_san_cert_reference(cls, cert: Dict[str, Any]) -> Dict[str, Any]:
        parsed = cert.get('parsed', {})
        sans = cls._get_sans_from_cert(cert)
        sig_alg = parsed.get('signature_algorithm', {})

        return {
            'cert_id': str(cert.get('_id', '')),
            'domain': cert.get('domain', ''),
            'san_count': len(sans),
            'sample_sans': sans[:5],
            'issuer': parsed.get('issuer', {}).get('common_name', 'N/A'),
            'expiry': parsed.get('validity', {}).get('end'),
            'encryption': sig_alg.get('name', 'Unknown') if sig_alg else 'Unknown',
            'country': cls._pick_cert_country(cert),
            'vulnerabilities': cls._format_zlint_vulnerabilities(cert.get('zlint', {})),
        }

    @classmethod
    def _hydrate_san_certificate_ids(
        cls,
        certificate_ids: List[Any],
        page: int,
        page_size: int
    ) -> List[Dict[str, Any]]:
        skip = (page - 1) * page_size
        page_ids = certificate_ids[skip:skip + page_size]
        if not page_ids:
            return []

        object_ids = []
        for cert_id in page_ids:
            if isinstance(cert_id, ObjectId):
                object_ids.append(cert_id)
                continue
            try:
                object_ids.append(ObjectId(str(cert_id)))
            except Exception:
                pass

        docs_by_id = {
            doc['_id']: doc
            for doc in cls.collection.find(
                {'_id': {'$in': object_ids}},
                {
                    'domain': 1,
                    'parsed.extensions.subject_alt_name.dns_names': 1,
                    'parsed.issuer.common_name': 1,
                    'parsed.issuer.country': 1,
                    'parsed.subject.country': 1,
                    'parsed.validity.end': 1,
                    'parsed.signature_algorithm.name': 1,
                    'zlint': 1,
                },
            )
        }

        certificates = []
        for cert_id in object_ids:
            doc = docs_by_id.get(cert_id)
            if doc:
                certificates.append(cls._serialize_san_cert_reference(doc))
        return certificates

    @classmethod
    def get_san_stats_fast(cls) -> Dict[str, Any]:
        doc = cls._get_san_analysis_doc()
        return {
            'total_sans': doc.get('total_san_count', 0),
            'avg_sans_per_cert': doc.get('avg_san_count', 0.0),
            'wildcard_certs': doc.get('wildcard_san_count', 0),
            'multi_domain_certs': doc.get('multi_domain_count', 0),
            'standard_certs': doc.get('standard_san_count', 0),
            'total_certs': doc.get('total_certificates', 0),
        }

    @classmethod
    def get_san_distribution_fast(cls) -> List[Dict[str, Any]]:
        doc = cls._get_san_analysis_doc()
        return [
            {
                'bucket': item.get('bucket'),
                'count': item.get('count', 0),
            }
            for item in doc.get('bucket_groups', [])
        ]

    @classmethod
    def get_san_tld_breakdown_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        doc = cls._get_san_analysis_doc()
        tlds = sorted(
            doc.get('tlds', []),
            key=lambda item: item.get('count', 0),
            reverse=True,
        )[:limit]
        return [
            {
                'tld': item.get('tld'),
                'count': item.get('count', 0),
            }
            for item in tlds
        ]

    @classmethod
    def get_san_wildcard_breakdown_fast(cls) -> Dict[str, int]:
        doc = cls._get_san_analysis_doc()
        return {
            'wildcard': doc.get('wildcard_san_count', 0),
            'standard': doc.get('standard_san_count', 0),
        }

    @classmethod
    def get_san_filtered_certs_fast(
        cls,
        filter_type: str,
        filter_value: str = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        doc = cls._get_san_analysis_doc()

        if filter_type == 'wildcard':
            total = doc.get('wildcard_san_count', 0)
            certificate_ids = doc.get('wildcard_certificate_ids', [])
        elif filter_type == 'standard':
            total = doc.get('standard_san_count', 0)
            certificate_ids = doc.get('standard_san_certificate_ids', [])
        elif filter_type == 'multi-domain':
            total = doc.get('multi_domain_count', 0)
            certificate_ids = doc.get('multi_domain_certificate_ids', [])
        elif filter_type == 'san-count':
            if not filter_value:
                raise ValueError("filter_value required for san-count filter")
            group = cls._find_san_bucket(doc, filter_value)
            total = group.get('count', 0)
            certificate_ids = group.get('certificate_ids', [])
        elif filter_type == 'tld':
            if not filter_value:
                raise ValueError("filter_value required for tld filter")
            group = cls._find_san_tld(doc, filter_value)
            total = group.get('count', 0)
            certificate_ids = group.get('certificate_ids', [])
        else:
            raise ValueError(f"Invalid filter_type: {filter_type}")

        certificates = cls._hydrate_san_certificate_ids(certificate_ids, page, page_size)
        skip = (page - 1) * page_size

        return {
            'certificates': certificates,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': skip + len(certificates) < min(total, len(certificate_ids)),
        }
