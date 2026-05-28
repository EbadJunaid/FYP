# backend/certificates/signature_hash_models.py
# Signature and Hash analytics model utilities extracted from CertificateModel.

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from ..db import db, MongoDBClient


class SignatureHashModel:
    """Model class for Signature & Hash analytics operations."""

    collection = db['certificates']

    @classmethod
    def get_signature_stats_fast(cls) -> Dict:
        from datetime import datetime, timezone
        collection = MongoDBClient.get_results_db()['signature-stats']

        result = collection.find_one({})
        if not result:
            import logging
            logging.warning("No pre-computed signature stats found. Run compute_signature_stats.py")
            return cls.get_signature_stats()

        computed_at_str = result.get('computedAt')
        if computed_at_str:
            computed_at = datetime.fromisoformat(computed_at_str.replace('Z', '+00:00'))
            age_hours = (datetime.now(timezone.utc) - computed_at).total_seconds() / 3600
            if age_hours > 24:
                import logging
                logging.warning(f"Pre-computed signature stats is {age_hours:.1f} hours old. Consider running compute_signature_stats.py")

        result.pop('_id', None)
        result.pop('sourceCollection', None)
        result.pop('documentCount', None)

        return result

    @classmethod
    def get_hash_trends_fast(cls, months: int = 36, granularity: str = 'quarterly') -> List[Dict]:
        from datetime import datetime, timezone
        collection = MongoDBClient.get_results_db()['hash-trends']

        query = {'granularity': granularity, 'months': months}
        trends = list(collection.find(query).sort([('year', 1), ('quarter', 1)]))

        if not trends:
            import logging
            logging.warning(f"No pre-computed hash trends found for {granularity}/{months}. Run compute_hash_trends.py")
            return cls.get_hash_trends(months=months, granularity=granularity)

        if trends:
            computed_at_str = trends[0].get('computedAt')
            if computed_at_str:
                computed_at = datetime.fromisoformat(computed_at_str.replace('Z', '+00:00'))
                age_hours = (datetime.now(timezone.utc) - computed_at).total_seconds() / 3600
                if age_hours > 24:
                    import logging
                    logging.warning(f"Pre-computed hash trends is {age_hours:.1f} hours old. Consider running compute_hash_trends.py")

        for trend in trends:
            trend.pop('_id', None)
            trend.pop('computedAt', None)
            trend.pop('sourceCollection', None)
            trend.pop('granularity', None)
            trend.pop('months', None)

        return trends

    @classmethod
    def get_issuer_algorithm_matrix_fast(cls, limit: int = 10) -> List[Dict]:
        from datetime import datetime, timezone
        collection = MongoDBClient.get_results_db()['issuer-algorithm-matrix']

        matrix = list(collection.find({}).sort('count', -1).limit(limit))

        if not matrix:
            import logging
            logging.warning("No pre-computed issuer algorithm matrix found. Run compute_issuer_algorithm_matrix.py")
            return cls.get_issuer_algorithm_matrix(limit=limit)

        if matrix:
            computed_at_str = matrix[0].get('computedAt')
            if computed_at_str:
                computed_at = datetime.fromisoformat(computed_at_str.replace('Z', '+00:00'))
                age_hours = (datetime.now(timezone.utc) - computed_at).total_seconds() / 3600
                if age_hours > 24:
                    import logging
                    logging.warning(f"Pre-computed issuer algorithm matrix is {age_hours:.1f} hours old. Consider running compute_issuer_algorithm_matrix.py")

        for item in matrix:
            item.pop('_id', None)
            item.pop('computedAt', None)
            item.pop('sourceCollection', None)
            item.pop('percentage', None)

        return matrix

    @classmethod
    def get_signature_stats(cls) -> Dict:
        # Using the implementation moved from CertificateModel
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

        algo_pipeline = [
            {'$group': {
                '_id': '$parsed.signature_algorithm.name',
                'count': {'$sum': 1}
            }},
            {'$match': {'_id': {'$ne': None}}},
            {'$sort': {'count': -1}},
            {'$limit': 10}
        ]

        algo_results = list(cls.collection.aggregate(
            algo_pipeline,
            hint='idx_signature_algo',
            allowDiskUse=True
        ))

        algorithm_distribution = []
        algo_colors = {
            'SHA256-RSA': '#3b82f6',
            'SHA384-RSA': '#60a5fa', 
            'SHA512-RSA': '#1d4ed8',
            'SHA256-ECDSA': '#10b981',
            'SHA384-ECDSA': '#34d399',
            'SHA512-ECDSA': '#059669',
            'SHA1-RSA': '#f59e0b',
            'MD5-RSA': '#ef4444',
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

        hash_pipeline = [
            {'$project': {
                'sigAlgo': '$parsed.signature_algorithm.name'
            }},
            {'$addFields': {
                'hash': {
                    '$switch': {
                        'branches': [
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA512|SHA-512', 'options': 'i'}}, 'then': 'SHA-512'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA384|SHA-384', 'options': 'i'}}, 'then': 'SHA-384'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA256|SHA-256', 'options': 'i'}}, 'then': 'SHA-256'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA224|SHA-224', 'options': 'i'}}, 'then': 'SHA-224'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'SHA1|SHA-1|withSHA1', 'options': 'i'}}, 'then': 'SHA-1'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD5', 'options': 'i'}}, 'then': 'MD5'},
                            {'case': {'$regexMatch': {'input': {'$ifNull': ['$sigAlgo', '']}, 'regex': 'MD2', 'options': 'i'}}, 'then': 'MD2'},
                        ],
                        'default': '$sigAlgo'
                    }
                }
            }},
            {'$match': {'hash': {'$ne': None, '$ne': ''}}},
            {'$group': {
                '_id': '$hash',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]
        hash_results = list(cls.collection.aggregate(hash_pipeline, allowDiskUse=True))

        hash_colors = {
            'SHA-512': '#1d4ed8',
            'SHA-384': '#3b82f6',
            'SHA-256': '#10b981',
            'SHA-224': '#34d399',
            'SHA-1': '#f59e0b',
            'MD5': '#ef4444',
            'MD2': '#dc2626',
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

            if name in ['SHA-1', 'MD5']:
                weak_hash_count += count

            if name in ['SHA-256', 'SHA-384', 'SHA-512']:
                compliant_count += count

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

        keysize_results = list(cls.collection.aggregate(
            keysize_pipeline,
            allowDiskUse=True
        ))

        keysize_distribution = []
        for item in keysize_results:
            algo = item['_id'].get('algo', 'Unknown')
            size = item['_id'].get('size', 0)
            count = item['count']
            name = f"{algo} {size}" if size else algo
            keysize_distribution.append({
                'name': name,
                'algorithm': algo,
                'size': size,
                'count': count,
                'percentage': round((count / total) * 100, 2),
                'color': '#3b82f6' if algo == 'RSA' else '#10b981'
            })

        self_signed_count = cls.collection.count_documents(
            {'parsed.signature.self_signed': True},
            hint='idx_self_signed'
        )

        hash_compliance_rate = round((compliant_count / total) * 100, 1) if total > 0 else 0

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
            elif size >= 256:
                key_score += 90 * pct

        hash_score = hash_compliance_rate

        algo_score = 85
        for item in algorithm_distribution:
            if 'ECDSA' in item.get('name', ''):
                algo_score += item.get('percentage', 0) * 0.15
        algo_score = min(100, algo_score)

        strength_score = int((key_score * 0.4) + (hash_score * 0.4) + (algo_score * 0.2))
        strength_score = max(0, min(100, strength_score))

        enc_type_pipeline = [
            {'$group': {
                '_id': '$parsed.subject_key_info.key_algorithm.name',
                'count': {'$sum': 1}
            }},
            {'$match': {'_id': {'$ne': None}}},
            {'$sort': {'count': -1}},
            {'$limit': 1}
        ]
        # Execute aggregation for encryption type
        enc_type_result = list(cls.collection.aggregate(
            enc_type_pipeline,
            hint='idx_key_algo',
            allowDiskUse=True
        ))

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
        """
        from dateutil.relativedelta import relativedelta

        now = datetime.now(timezone.utc)
        start_date = now - relativedelta(months=months)
        start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

        if granularity == 'yearly':
            period_expr = {'year': {'$year': '$issuedDate'}}
        else:
            period_expr = {
                'year': {'$year': '$issuedDate'},
                'quarter': {'$ceil': {'$divide': [{'$month': '$issuedDate'}, 3]}}
            }

        pipeline = [
            {'$match': {'parsed.validity.start': {'$gte': start_str}}},
            {'$project': {
                'sigAlgo': '$parsed.signature_algorithm.name',
                'issuedDate': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}
            }},
            {'$match': {'issuedDate': {'$ne': None}}},
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
            {'$group': {'_id': {'period': '$period', 'hash': '$hash'}, 'count': {'$sum': 1}}},
            {'$group': {'_id': '$_id.period', 'hashes': {'$push': {'hash': '$_id.hash', 'count': '$count'}}, 'total': {'$sum': '$count'}}},
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
        pipeline = [
            {'$project': {
                'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
                'algo': '$parsed.subject_key_info.key_algorithm.name',
                'rsaLen': '$parsed.subject_key_info.rsa_public_key.length',
                'ecLen': '$parsed.subject_key_info.ecdsa_public_key.length'
            }},
            {'$addFields': {'keySize': {'$ifNull': ['$rsaLen', '$ecLen']}}},
            {'$match': {'issuer': {'$ne': None}, 'algo': {'$ne': None}}},
            {'$group': {'_id': {'issuer': '$issuer', 'algo': '$algo', 'keySize': '$keySize'}, 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 50}
        ]

        results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))

        matrix = []
        for item in results:
            issuer = item['_id'].get('issuer', 'Unknown')
            algo = item['_id'].get('algo', 'Unknown')
            key_size = item['_id'].get('keySize', 0)
            count = item['count']
            algo_str = f"{algo}-{key_size}" if key_size else algo
            matrix.append({
                'issuer': issuer,
                'algorithm': algo_str,
                'algorithmType': algo,
                'keySize': key_size,
                'count': count
            })

        return matrix