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
from .overview_models import OverviewModels



class CertificateModel:
    """
    Model class for SSL Certificate documents in MongoDB.
    Handles CRUD operations and aggregation queries.
    """
    collection = db['certificates']
    
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
        return SharedModels.get_all(
            page=page,
            page_size=page_size,
            status=status,
            country=country,
            issuer=issuer,
            search=search,
            encryption_type=encryption_type,
            has_vulnerabilities=has_vulnerabilities,
            expiring_month=expiring_month,
            expiring_year=expiring_year,
            expiring_days=expiring_days,
            validity_bucket=validity_bucket,
            issued_month=issued_month,
            issued_year=issued_year,
            issued_within_days=issued_within_days,
            signature_algorithm=signature_algorithm,
            weak_hash=weak_hash,
            self_signed=self_signed,
            key_size=key_size,
            hash_type=hash_type,
            san_tld=san_tld,
            san_type=san_type,
            san_count_min=san_count_min,
            san_count_max=san_count_max,
            expiring_start=expiring_start,
            expiring_end=expiring_end,
            shared_key=shared_key,
            base_filter=base_filter
        )

    @classmethod
    def get_by_id(cls, cert_id: str) -> Optional[Dict]:
        return SharedModels.get_by_id(cert_id=cert_id)
    
    # ==================== Overview page METHODS ====================

    @classmethod
    def get_encryption_strength(cls, base_filter: Optional[Dict] = None) -> List[Dict]:
        return OverviewModels.get_encryption_strength(base_filter=base_filter)
    
    @classmethod
    def get_unique_filters(cls) -> Dict:
        return OverviewModels.get_unique_filters()
    
   

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
