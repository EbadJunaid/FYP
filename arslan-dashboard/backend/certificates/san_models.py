# backend/certificates/san_models.py
# SAN analytics model utilities extracted from CertificateModel for better page separation.

from typing import List, Dict, Any
from .db import MongoDBClient


class SANModel:
    """Model class for SAN analytics operations."""

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

    @classmethod
    def get_san_stats_fast(cls) -> Dict[str, Any]:
        """
        ⚡ OPTIMIZED: Get SAN statistics from pre-computed materialized view.
        
        Returns:
            Dict containing:
                - total_sans: Total number of SAN entries across all certs
                - avg_sans_per_cert: Average SANs per certificate
                - wildcard_certs: Number of certs with wildcard SANs
                - multi_domain_certs: Number of certs with 5+ SANs
        """
        stats_collection = MongoDBClient.get_results_db()['san-stats']
        print("I am in get_san_stats_fast ")
        
        doc = stats_collection.find_one({'_id': 'san_stats'})
        
        if not doc:
            raise ValueError("SAN stats not computed. Run compute_san_stats.py first.")
        
        return {
            'total_sans': doc.get('total_sans', 0),
            'avg_sans_per_cert': doc.get('avg_sans_per_cert', 0.0),
            'wildcard_certs': doc.get('wildcard_certs', 0),
            'multi_domain_certs': doc.get('multi_domain_certs', 0)
        }

    @classmethod
    def get_san_distribution_fast(cls) -> List[Dict[str, Any]]:
        """
        ⚡ OPTIMIZED: Get SAN distribution from pre-computed materialized view.
        
        Returns:
            List of dicts with bucket and count
        """
        print("I am in get_san_distribution_fast ")
        distribution_collection = MongoDBClient.get_results_db()['san-distribution']
        
        results = list(distribution_collection.find(
            {'_id': {'$ne': 'metadata'}},
            {'_id': 0, 'bucket': 1, 'count': 1}
        ).sort('bucket_id', 1))
        
        if not results:
            raise ValueError("SAN distribution not computed. Run compute_san_distribution.py first.")
        
        return results

    @classmethod
    def get_san_tld_breakdown_fast(cls, limit: int = 10) -> List[Dict[str, Any]]:
        """
        ⚡ OPTIMIZED: Get TLD breakdown from pre-computed materialized view.
        
        Args:
            limit: Maximum number of TLDs to return (default 10)
        
        Returns:
            List of dicts with tld and count
        """
        print("I am in get_san_tld_breakdown_fast ")

        tld_collection = MongoDBClient.get_results_db()['san-tld-certs']
        
        results = list(tld_collection.find(
            {},
            {'_id': 1, 'certificate_count': 1}
        ).sort('certificate_count', -1).limit(limit))
        
        if not results:
            raise ValueError("SAN TLD data not computed. Run compute-san-filtered-lists.py first.")
        
        return [{
            'tld': doc['_id'],
            'count': doc['certificate_count']
        } for doc in results]

    @classmethod
    def get_san_wildcard_breakdown_fast(cls) -> Dict[str, int]:
        """
        ⚡ OPTIMIZED: Get wildcard breakdown from pre-computed stats.
        
        Returns:
            Dict with wildcard and standard counts
        """
        print("I am in get_san_wildcard_breakdown_fast ")

        stats_collection = MongoDBClient.get_results_db()['san-stats']
        
        doc = stats_collection.find_one({'_id': 'san_stats'})
        
        if not doc:
            raise ValueError("SAN stats not computed. Run compute-san-filtered-lists.py first.")
        
        wildcard = doc.get('wildcard_certs', 0)
        total = doc.get('total_certs', 0)
        standard = max(0, total - wildcard)
        
        return {
            'wildcard': wildcard,
            'standard': standard
        }

    @classmethod
    def get_san_filtered_certs_fast(cls, filter_type: str, filter_value: str = None,
                                     page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """
        ⚡ OPTIMIZED: Get filtered certificates from pre-computed collections.
        
        Args:
            filter_type: Type of filter - 'wildcard', 'multi-domain', 'san-count', 'tld'
            filter_value: Value for filter (e.g., '50+' for san-count, '.com' for tld)
            page: Page number (1-indexed)
            page_size: Number of results per page
        
        Returns:
            Dict with:
            - certificates: List of certificate references
            - total: Total count
            - page: Current page
            - page_size: Page size
            - has_more: Whether more pages exist
        """
        if filter_type == 'wildcard':
            collection = MongoDBClient.get_results_db()['san-wildcard-certs']
            query = {}
        elif filter_type == 'standard':
            collection = MongoDBClient.get_results_db()['san-standard-certs']
            query = {}
        elif filter_type == 'multi-domain':
            collection = MongoDBClient.get_results_db()['san-multi-domain-certs']
            query = {}
        elif filter_type == 'san-count':
            print("I am in san-count filter of get_san_filtered_certs_fast ")
            if not filter_value:
                raise ValueError("filter_value required for san-count filter")
            collection = MongoDBClient.get_results_db()['san-count-groups']
            try:
                doc = collection.find_one({'_id': filter_value})
                if not doc:
                    return {
                        'certificates': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size,
                        'has_more': False
                    }
                total = doc.get('total_count', doc.get('certificate_count', 0))
                certificates = doc.get('certificates', [])
                skip = (page - 1) * page_size
                paginated_certs = certificates[skip:skip + page_size]
                
                from bson import ObjectId
                for cert in paginated_certs:
                    if 'cert_id' in cert and isinstance(cert['cert_id'], ObjectId):
                        cert['cert_id'] = str(cert['cert_id'])
                    if '_id' in cert and isinstance(cert['_id'], ObjectId):
                        cert['_id'] = str(cert['_id'])
                
                return {
                    'certificates': paginated_certs,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'has_more': skip + len(paginated_certs) < total
                }
            except Exception as e:
                print(f"Error in SAN count filter: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        elif filter_type == 'tld':
            if not filter_value:
                raise ValueError("filter_value required for tld filter")
            collection = MongoDBClient.get_results_db()['san-tld-certs']
            try:
                doc = collection.find_one({'_id': filter_value})
                if not doc:
                    return {
                        'certificates': [],
                        'total': 0,
                        'page': page,
                        'page_size': page_size,
                        'has_more': False
                    }
                total = doc.get('total_count', doc.get('certificate_count', 0))
                certificates = doc.get('certificates', [])
                skip = (page - 1) * page_size
                paginated_certs = certificates[skip:skip + page_size]
                
                from bson import ObjectId
                for cert in paginated_certs:
                    if 'cert_id' in cert and isinstance(cert['cert_id'], ObjectId):
                        cert['cert_id'] = str(cert['cert_id'])
                    if '_id' in cert and isinstance(cert['_id'], ObjectId):
                        cert['_id'] = str(cert['_id'])
                
                return {
                    'certificates': paginated_certs,
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'has_more': skip + len(paginated_certs) < total
                }
            except Exception as e:
                print(f"Error in TLD filter: {str(e)}")
                import traceback
                traceback.print_exc()
                raise
        else:
            raise ValueError(f"Invalid filter_type: {filter_type}")
        
        skip = (page - 1) * page_size
        total = collection.count_documents(query)
        
        certificates = list(collection.find(query)
                          .sort('san_count', -1)
                          .skip(skip)
                          .limit(page_size))
        
        for cert in certificates:
            if '_id' in cert:
                cert['_id'] = str(cert['_id'])
            if 'cert_id' in cert:
                cert['cert_id'] = str(cert['cert_id'])
        
        return {
            'certificates': certificates,
            'total': total,
            'page': page,
            'page_size': page_size,
            'has_more': skip + len(certificates) < total
        }
