# backend/certificates/ca_models.py
# CA (Certificate Authority) analytics model utilities extracted from CertificateModel for page separation.

from datetime import datetime, timezone
#from tkinter.font import names
from typing import List, Dict, Any, Optional
from ..db import db, MongoDBClient


class CAModel:
    """Model class for CA analytics operations."""

    # Use the same certificates collection reference as CertificateModel
    collection = db['certificates']
    _ranking_colors = [
        '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444',
        '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
    ]

    _ranking_groups = {
        'ca': {
            'label': 'CA',
            'field': 'parsed.issuer.organization',
            'match_key': 'issuer',
        },
        'country': {
            'label': 'Issuer Country',
            'field': 'parsed.issuer.country',
            'match_key': 'country',
        },
        'validation_level': {
            'label': 'Validation Level',
            'field': 'parsed.validation_level',
            'match_key': 'validation_level',
        },
    }

    @classmethod
    def _ranking_group_config(cls, group_by: str) -> Dict[str, str]:
        return cls._ranking_groups.get(group_by, cls._ranking_groups['ca'])

    @staticmethod
    def _notebook_ranking_formula() -> Dict[str, Any]:
        return {
            'coreHygiene': 'mean(ZCS, ZHFS)',
            'cryptoHealth': 'mean(KHS, KUS, WKLP)',
            'operationalStability': 'mean(CADS, TSI, IOPS)',
            'policyCompliance': 'mean(EKUVS, PICS, DVAS, NCVS)',
            'riskFactors': 'mean(GNS, ACCS, REVPS)',
            'finalScore': 'mean(core_hygiene, crypto_health, operational_stability, policy_compliance, risk_factors) * 100',
        }

    @classmethod
    def get_ranking(cls, limit: int = 20, group_by: str = 'ca') -> Dict[str, Any]:
        group_by = group_by if group_by in cls._ranking_groups else 'ca'
        limit = max(1, min(int(limit or 20), 5000))

        empty_response = {
            'groupBy': group_by,
            'metricLabel': cls._ranking_group_config(group_by)['label'],
            'mode': 'precomputed',
            'items': [],
            'summary': {
                'rankedCount': 0,
                'topName': None,
                'topScore': 0,
                'averageScore': 0,
                'totalCertificates': 0,
                'bestHygieneName': None,
            },
            'formula': cls._notebook_ranking_formula(),
        }

        if group_by != 'ca':
            return empty_response

        analysis_doc = cls._get_ca_analysis_doc()
        if not analysis_doc:
            return empty_response

        ca_list = [
            item for item in analysis_doc.get('ca-list', [])
            if item.get('scoreSampleCount', 0) > 0
        ]
        if not ca_list:
            return {**empty_response, 'summary': {**empty_response['summary'], 'totalCertificates': analysis_doc.get('total_certs', 0)}}

        ca_list = sorted(ca_list, key=lambda item: item.get('scoreRank') or 999999)
        items = []
        for index, item in enumerate(ca_list, start=1):
            items.append({
                'id': item.get('ca_id', f'ca-{index}'),
                'name': item.get('name'),
                'rank': item.get('scoreRank') or index,
                'marketRank': item.get('rank'),
                'count': item.get('count', 0),
                'percentage': item.get('percentage', 0),
                'score': item.get('score', 0),
                'scoreSampleCount': item.get('scoreSampleCount', 0),
                'coreHygiene': item.get('coreHygiene', 0),
                'cryptoHealth': item.get('cryptoHealth', 0),
                'operationalStability': item.get('operationalStability', 0),
                'policyCompliance': item.get('policyCompliance', 0),
                'riskFactors': item.get('riskFactors', 0),
                'validationBreakdown': {
                    validation_item.get('validationlevel_type', 'Unknown'): validation_item.get('count', 0)
                    for validation_item in item.get('validationLevel', [])
                },
                'color': item.get('color', cls._ranking_colors[(index - 1) % len(cls._ranking_colors)]),
            })

        limited = items[:limit]
        top = items[0] if items else None
        best_hygiene = max(items, key=lambda entry: entry.get('coreHygiene', 0), default=None)
        return {
            'groupBy': 'ca',
            'metricLabel': 'CA',
            'mode': 'precomputed',
            'items': limited,
            'summary': {
                'rankedCount': len(items),
                'topName': top.get('name') if top else None,
                'topScore': top.get('score', 0) if top else 0,
                'averageScore': round(sum(entry.get('score', 0) for entry in items) / len(items), 2) if items else 0,
                'totalCertificates': analysis_doc.get('total_certs', 0),
                'bestHygieneName': best_hygiene.get('name') if best_hygiene else None,
            },
            'formula': analysis_doc.get('ranking_formula') or cls._notebook_ranking_formula(),
        }

    # @classmethod
    # def get_ca_stats_fast(cls) -> Dict:
    #     """
    #     FAST VERSION: Get CA Analytics stats from pre-computed materialized view.
        
    #     Returns:
    #         Dict with total_cas, total_certs, top_ca, self_signed_count, unique_countries
        
    #     Performance:
    #         - Before: ~6 minutes (multiple aggregations)
    #         - After: ~0.005s (single document read)
    #         - Speedup: ~72,000x
        
    #     Materialized View:
    #         - Database: tranco-latest-8-lakh-results
    #         - Collection: ca-stats
    #         - Document: Single doc with _id='ca_stats'
        
    #     To update pre-computed data:
    #         python compute_ca_stats.py
    #     """
    #     stats_collection = MongoDBClient.get_results_db()['ca-stats']
        
    #     # Read the single pre-computed document
    #     stats_doc = stats_collection.find_one({'_id': 'ca_stats'})
        
    #     if not stats_doc:
    #         # Fallback to slow method if no pre-computed data
    #         return cls.get_ca_stats()
        
    #     return {
    #         'total_cas': stats_doc['total_cas'],
    #         'total_certs': stats_doc['total_certs'],
    #         'top_ca': stats_doc['top_ca'],
    #         'self_signed_count': stats_doc['self_signed_count'],
    #         'unique_countries': stats_doc['unique_countries']
    #     }

    @classmethod
    def get_ca_stats(cls) -> Dict:
        """
        Get CA Analytics stats for metric cards.
        Returns: total CAs, top CA, self-signed count, unique CA countries
        """
        # Previous approch
        # ca_pipeline = [
        #     # {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
        #     {'$group': {'_id': '$parsed.issuer.organization'}},
        #     {'$count': 'total'}
        # ]
        # ca_result = list(cls.collection.aggregate(ca_pipeline))
        # total_cas = ca_result[0]['total'] if ca_result else 0
        
        
        # Get total unique CAs
        ca_result = cls.collection.distinct('parsed.issuer.organization')
        # # print(f"names of cas",ca_result[0:10])
        total_cas = len(ca_result)
        
        # Previous approch
        # total_certs = cls.collection.count_documents({})

        # Get total certificates (fast metadata read)
        total_certs = cls.collection.estimated_document_count()

        # Get top CA
        top_ca_pipeline = [
            # {'$unwind': {'path': '$parsed.issuer.organization', 'preserveNullAndEmptyArrays': True}},
        #    {'$project': {'_id': 0, 'parsed.issuer.organization': 1}},
            {'$group': {'_id': '$parsed.issuer.organization', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
       


        top_ca_result = list(cls.collection.aggregate(top_ca_pipeline))
       

       
        top_ca = None
        top_ca_count = 0
        top_ca_percentage = 0
        if top_ca_result:
            top_ca = top_ca_result[0]['_id'] or 'Unknown'
            top_ca_count = top_ca_result[0]['count']
            # top_ca_percentage = round((top_ca_count / total_certs) * 100, 1) if total_certs > 0 else 0
            top_ca_percentage = round((top_ca_count / 878849) * 100, 1) if 878849 > 0 else 0

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

    # @classmethod
    # def get_issuer_validation_matrix_fast(cls, limit: int = 10) -> List[Dict]:
    #     """
    #     FAST VERSION: Get issuer × validation level matrix from pre-computed materialized view.
        
    #     Args:
    #         limit: Number of top issuers to return (default: 10)
        
    #     Returns:
    #         List of dicts with issuer, validationLevel, and count
        
    #     Performance:
    #         - Before: ~93 seconds (complex aggregation)
    #         - After: ~0.015s (pre-filtered read)
    #         - Speedup: ~6,200x
        
    #     Materialized View:
    #         - Database: tranco-latest-8-lakh-results
    #         - Collection: issuer-validation-matrix
    #         - Documents: 114 records (top 50 issuers × validation levels)
        
    #     To update pre-computed data:
    #         python compute_issuer_validation_matrix.py
    #     """
    #     matrix_collection = MongoDBClient.get_results_db()['issuer-validation-matrix']
        
    #     # Get top issuers by total count
    #     pipeline = [
    #         {'$match': {'record_id': {'$exists': True}}},  # Exclude metadata
    #         {'$sort': {'issuer_total': -1, 'count': -1}},
    #         {'$group': {
    #             '_id': '$issuer',
    #             'combinations': {
    #                 '$push': {
    #                     'validationLevel': '$validationLevel',
    #                     'count': '$count'
    #                 }
    #             },
    #             'total': {'$first': '$issuer_total'}
    #         }},
    #         {'$sort': {'total': -1}},
    #         {'$limit': limit}
    #     ]
        
    #     issuer_groups = list(matrix_collection.aggregate(pipeline))
        
    #     # Flatten to required format
    #     matrix = []
    #     for group in issuer_groups:
    #         issuer = group['_id']
    #         for combo in group['combinations']:
    #             matrix.append({
    #                 'issuer': issuer,
    #                 'validationLevel': combo['validationLevel'],
    #                 'count': combo['count']
    #             })
        
    #     return matrix

    # =========================================================================
    # NEW CA-ANALYSIS IMPLEMENTATION
    # -------------------------------------------------------------------------
    # The methods below intentionally keep the same names as the legacy fast
    # methods above. Python uses the later definition, so these methods now read
    # from one collection/document:
    #
    #   <results_db>.ca-analysis / {"_id": "ca_analysis"}
    #
    # If that document is missing, they fall back to the existing slow methods.
    # =========================================================================

    @classmethod
    def _get_ca_analysis_doc(cls) -> Optional[Dict]:
        return MongoDBClient.find_scoped_result_doc('ca-analysis', fallback_id='ca_analysis')

    @classmethod
    def get_ca_stats_fast(cls) -> Dict:
        doc = cls._get_ca_analysis_doc()
        if not doc:
            return cls.get_ca_stats()

        ca_list = doc.get('ca-list', [])
        top_ca_record = None
        for ca in ca_list:
            if ca.get('rank') == 1:
                top_ca_record = ca
                break
        if not top_ca_record and ca_list:
            top_ca_record = sorted(ca_list, key=lambda item: item.get('rank', 999999))[0]

        return {
            'total_cas': doc.get('total_cas', 0),
            'total_certs': doc.get('total_certs', 0),
            'top_ca': {
                'name': top_ca_record.get('name') if top_ca_record else None,
                'count': top_ca_record.get('count', 0) if top_ca_record else 0,
                'percentage': top_ca_record.get('percentage', 0) if top_ca_record else 0,
            },
            'self_signed_count': doc.get('self_signed_count', 0),
            'unique_countries': doc.get('unique_countries', 0)
        }

    @classmethod
    def get_issuer_validation_matrix_fast(cls, limit: int = 10) -> List[Dict]:
        doc = cls._get_ca_analysis_doc()
        if not doc:
            return cls.get_issuer_validation_matrix(limit=limit)

        ca_list = sorted(
            doc.get('ca-list', []),
            key=lambda item: item.get('rank', 999999),
        )[:limit]

        matrix = []
        for ca in ca_list:
            issuer = ca.get('name')
            for validation_item in ca.get('validationLevel', []):
                matrix.append({
                    'issuer': issuer,
                    'validationLevel': validation_item.get('validationlevel_type', 'Unknown'),
                    'count': validation_item.get('count', 0),
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
