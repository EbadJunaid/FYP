# backend/certificates/ca_models.py
# CA (Certificate Authority) analytics model utilities extracted from CertificateModel for page separation.

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from .db import db, MongoDBClient


class CAModel:
    """Model class for CA analytics operations."""

    # Use the same certificates collection reference as CertificateModel
    collection = db['certificates']

    @classmethod
    def get_ca_stats_fast(cls) -> Dict:
        """
        FAST VERSION: Get CA Analytics stats from pre-computed materialized view.
        
        Returns:
            Dict with total_cas, total_certs, top_ca, self_signed_count, unique_countries
        
        Performance:
            - Before: ~6 minutes (multiple aggregations)
            - After: ~0.005s (single document read)
            - Speedup: ~72,000x
        
        Materialized View:
            - Database: tranco-latest-8-lakh-results
            - Collection: ca-stats
            - Document: Single doc with _id='ca_stats'
        
        To update pre-computed data:
            python compute_ca_stats.py
        """
        stats_collection = MongoDBClient.get_results_db()['ca-stats']
        
        # Read the single pre-computed document
        stats_doc = stats_collection.find_one({'_id': 'ca_stats'})
        
        if not stats_doc:
            # Fallback to slow method if no pre-computed data
            return cls.get_ca_stats()
        
        return {
            'total_cas': stats_doc['total_cas'],
            'total_certs': stats_doc['total_certs'],
            'top_ca': stats_doc['top_ca'],
            'self_signed_count': stats_doc['self_signed_count'],
            'unique_countries': stats_doc['unique_countries']
        }

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
        self_signed_count = cls.collection.count_documents(
            {'parsed.signature.self_signed': True},
            hint='idx_self_signed'
        )
        
        # Get unique CA countries
        country_pipeline = [
            {'$unwind': {'path': '$parsed.issuer.country', 'preserveNullAndEmptyArrays': True}},
            {'$group': {'_id': '$parsed.issuer.country'}},
            {'$match': {'_id': {'$ne': None}}},
            {'$count': 'total'}
        ]

        country_result = list(cls.collection.aggregate(
            country_pipeline,
            hint='idx_issuer_country',
            allowDiskUse=True
        ))
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
    def get_issuer_validation_matrix_fast(cls, limit: int = 10) -> List[Dict]:
        """
        FAST VERSION: Get issuer × validation level matrix from pre-computed materialized view.
        
        Args:
            limit: Number of top issuers to return (default: 10)
        
        Returns:
            List of dicts with issuer, validationLevel, and count
        
        Performance:
            - Before: ~93 seconds (complex aggregation)
            - After: ~0.015s (pre-filtered read)
            - Speedup: ~6,200x
        
        Materialized View:
            - Database: tranco-latest-8-lakh-results
            - Collection: issuer-validation-matrix
            - Documents: 114 records (top 50 issuers × validation levels)
        
        To update pre-computed data:
            python compute_issuer_validation_matrix.py
        """
        matrix_collection = MongoDBClient.get_results_db()['issuer-validation-matrix']
        
        # Get top issuers by total count
        pipeline = [
            {'$match': {'record_id': {'$exists': True}}},  # Exclude metadata
            {'$sort': {'issuer_total': -1, 'count': -1}},
            {'$group': {
                '_id': '$issuer',
                'combinations': {
                    '$push': {
                        'validationLevel': '$validationLevel',
                        'count': '$count'
                    }
                },
                'total': {'$first': '$issuer_total'}
            }},
            {'$sort': {'total': -1}},
            {'$limit': limit}
        ]
        
        issuer_groups = list(matrix_collection.aggregate(pipeline))
        
        # Flatten to required format
        matrix = []
        for group in issuer_groups:
            issuer = group['_id']
            for combo in group['combinations']:
                matrix.append({
                    'issuer': issuer,
                    'validationLevel': combo['validationLevel'],
                    'count': combo['count']
                })
        
        return matrix

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
