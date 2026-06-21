# # backend/certificates/trends_models.py
# # Trends analytics model utilities extracted from CertificateModel for page separation.

# from datetime import datetime, timezone, timedelta
# from typing import List, Dict, Any
# from dateutil.relativedelta import relativedelta
# from .db import db, MongoDBClient


# class TrendsModel:
#     """Model class for Trends analytics operations."""

#     # Use the same certificates collection reference as CertificateModel
#     collection = db['certificates']

#     @classmethod
#     def get_trends_stats(cls) -> Dict[str, Any]:
#         now = cls.get_current_time_iso() if hasattr(cls, 'get_current_time_iso') else datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
#         now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
#         thirty_days_ago = (datetime.now(timezone.utc) - timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')
#         sixty_days_ago = (datetime.now(timezone.utc) - timedelta(days=60)).strftime('%Y-%m-%dT%H:%M:%SZ')

#         velocity_30d = cls.collection.count_documents({
#             'parsed.validity.start': {'$gte': thirty_days_ago, '$lte': now}
#         })

#         velocity_prev_30d = cls.collection.count_documents({
#             'parsed.validity.start': {'$gte': sixty_days_ago, '$lt': thirty_days_ago}
#         })

#         velocity_change = 0
#         if velocity_prev_30d > 0:
#             velocity_change = round(((velocity_30d - velocity_prev_30d) / velocity_prev_30d) * 100, 1)

#         expiring_30d = cls.collection.count_documents({
#             'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}
#         })

#         total_certs = cls.collection.count_documents({})
#         legacy_algos = ['SHA1-RSA', 'SHA1WithRSAEncryption', 'MD5-RSA', 'MD5WithRSAEncryption', 'MD2-RSA', 'SHA1-ECDSA']
#         legacy_count = cls.collection.count_documents({
#             'parsed.signature_algorithm.name': {'$in': legacy_algos}
#         })
#         modern_algo_count = total_certs - legacy_count
#         modern_algo_percent = round((modern_algo_count / max(total_certs, 1)) * 100, 1)

#         strong_key_count = cls.collection.count_documents({
#             '$or': [
#                 {
#                     'parsed.subject_key_info.key_algorithm.name': 'RSA',
#                     'parsed.subject_key_info.rsa_public_key.length': {'$gte': 2048}
#                 },
#                 {
#                     'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
#                     'parsed.subject_key_info.ecdsa_public_key.length': {'$gte': 256}
#                 },
#                 {
#                     'parsed.subject_key_info.key_algorithm.name': {'$in': ['Ed25519', 'Ed448']}
#                 }
#             ]
#         })
#         strong_key_percent = round((strong_key_count / max(total_certs, 1)) * 100, 1)

#         return {
#             'velocity_30d': velocity_30d,
#             'velocity_change': velocity_change,
#             'expiring_30d': expiring_30d,
#             'modern_algo_percent': modern_algo_percent,
#             'strong_key_percent': strong_key_percent,
#             'total_certs': total_certs
#         }

#     @classmethod
#     def get_key_size_timeline(cls, months: int = 12) -> List[Dict[str, Any]]:
#         now = datetime.now(timezone.utc)
#         month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
#                        'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

#         timeline = []
#         for i in range(months - 1, -1, -1):
#             target_date = now - relativedelta(months=i)
#             start_of_month = target_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
#             end_of_month = (start_of_month + relativedelta(months=1)) - timedelta(seconds=1)

#             start_str = start_of_month.strftime('%Y-%m-%dT%H:%M:%SZ')
#             end_str = end_of_month.strftime('%Y-%m-%dT%H:%M:%SZ')

#             base_match = {
#                 'parsed.validity.start': {'$gte': start_str, '$lte': end_str}
#             }

#             rsa_2048 = cls.collection.count_documents({
#                 **base_match,
#                 'parsed.subject_key_info.key_algorithm.name': 'RSA',
#                 'parsed.subject_key_info.rsa_public_key.length': 2048
#             })

#             rsa_4096 = cls.collection.count_documents({
#                 **base_match,
#                 'parsed.subject_key_info.key_algorithm.name': 'RSA',
#                 'parsed.subject_key_info.rsa_public_key.length': 4096
#             })

#             rsa_other = cls.collection.count_documents({
#                 **base_match,
#                 'parsed.subject_key_info.key_algorithm.name': 'RSA',
#                 'parsed.subject_key_info.rsa_public_key.length': {'$nin': [2048, 4096]}
#             })

#             ecdsa_256 = cls.collection.count_documents({
#                 **base_match,
#                 'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
#                 'parsed.subject_key_info.ecdsa_public_key.length': 256
#             })

#             ecdsa_384 = cls.collection.count_documents({
#                 **base_match,
#                 'parsed.subject_key_info.key_algorithm.name': {'$in': ['ECDSA', 'EC']},
#                 'parsed.subject_key_info.ecdsa_public_key.length': 384
#             })

#             month_label = f"{month_names[target_date.month - 1]} '{str(target_date.year)[2:]}"

#             timeline.append({
#                 'month': month_label,
#                 'year': target_date.year,
#                 'monthNum': target_date.month,
#                 'rsa_2048': rsa_2048,
#                 'rsa_4096': rsa_4096,
#                 'rsa_other': rsa_other,
#                 'ecdsa_256': ecdsa_256,
#                 'ecdsa_384': ecdsa_384,
#                 'total': rsa_2048 + rsa_4096 + rsa_other + ecdsa_256 + ecdsa_384
#             })

#         return timeline

#     @classmethod
#     def get_expiration_forecast(cls, months: int = 12) -> List[Dict[str, Any]]:
#         now = datetime.now(timezone.utc)
#         now_str = now.strftime('%Y-%m-%dT%H:%M:%SZ')
#         end_date = now + timedelta(days=months * 30)
#         end_str = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

#         pipeline = [
#             {'$match': {
#                 'parsed.validity.end': {'$gte': now_str, '$lte': end_str}
#             }},
#             {'$project': {
#                 'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.end', 'onError': None}}},
#                 'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.end', 'onError': None}}}
#             }},
#             {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
#             {'$group': {
#                 '_id': {'year': '$year', 'month': '$month'},
#                 'count': {'$sum': 1}
#             }},
#             {'$sort': {'_id.year': 1, '_id.month': 1}}
#         ]

#         results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))

#         month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

#         forecast = []
#         for r in results:
#             year = r['_id']['year']
#             month = r['_id']['month']
#             forecast.append({
#                 'month': f"{month_names[month]} {year}",
#                 'monthNum': month,
#                 'year': year,
#                 'count': r['count']
#             })

#         return forecast

#     @classmethod
#     def get_algorithm_adoption(cls, months: int = 12) -> List[Dict[str, Any]]:
#         now = datetime.now(timezone.utc)
#         start_date = now - timedelta(days=months * 30)
#         start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

#         pipeline = [
#             {'$match': {
#                 'parsed.validity.start': {'$gte': start_str}
#             }},
#             {'$project': {
#                 'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
#                 'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
#                 'algo': '$parsed.signature_algorithm.name'
#             }},
#             {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
#             {'$group': {
#                 '_id': {'year': '$year', 'month': '$month', 'algo': '$algo'},
#                 'count': {'$sum': 1}
#             }},
#             {'$sort': {'_id.year': 1, '_id.month': 1}}
#         ]

#         results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))

#         month_data = {}
#         for r in results:
#             key = (r['_id']['year'], r['_id']['month'])
#             if key not in month_data:
#                 month_data[key] = {'sha256_rsa': 0, 'sha384_rsa': 0, 'ecdsa': 0, 'sha1_rsa': 0, 'other': 0}

#             algo = (r['_id']['algo'] or '').upper()
#             count = r['count']

#             if 'SHA256' in algo and 'RSA' in algo:
#                 month_data[key]['sha256_rsa'] += count
#             elif 'SHA384' in algo and 'RSA' in algo:
#                 month_data[key]['sha384_rsa'] += count
#             elif 'ECDSA' in algo or 'EC' in algo:
#                 month_data[key]['ecdsa'] += count
#             elif 'SHA1' in algo or 'SHA-1' in algo:
#                 month_data[key]['sha1_rsa'] += count
#             else:
#                 month_data[key]['other'] += count

#         month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

#         adoption = []
#         for (year, month), data in sorted(month_data.items()):
#             adoption.append({
#                 'month': f"{month_names[month]} {year}",
#                 'monthNum': month,
#                 'year': year,
#                 **data
#             })

#         return adoption

#     @classmethod
#     def get_validation_level_trends(cls, months: int = 12) -> List[Dict[str, Any]]:
#         now = datetime.now(timezone.utc)
#         start_date = now - timedelta(days=months * 30)
#         start_str = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')

#         pipeline = [
#             {'$match': {
#                 'parsed.validity.start': {'$gte': start_str}
#             }},
#             {'$project': {
#                 'year': {'$year': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
#                 'month': {'$month': {'$dateFromString': {'dateString': '$parsed.validity.start', 'onError': None}}},
#                 'level': {'$ifNull': ['$parsed.validation_level', 'Unknown']}
#             }},
#             {'$match': {'year': {'$ne': None}, 'month': {'$ne': None}}},
#             {'$group': {
#                 '_id': {'year': '$year', 'month': '$month', 'level': '$level'},
#                 'count': {'$sum': 1}
#             }},
#             {'$sort': {'_id.year': 1, '_id.month': 1}}
#         ]

#         results = list(cls.collection.aggregate(pipeline, allowDiskUse=True))

#         month_data = {}
#         for r in results:
#             key = (r['_id']['year'], r['_id']['month'])
#             if key not in month_data:
#                 month_data[key] = {'dv': 0, 'ov': 0, 'ev': 0, 'unknown': 0}

#             level = (r['_id']['level'] or 'Unknown').upper()
#             count = r['count']

#             if level == 'DV':
#                 month_data[key]['dv'] += count
#             elif level == 'OV':
#                 month_data[key]['ov'] += count
#             elif level == 'EV':
#                 month_data[key]['ev'] += count
#             else:
#                 month_data[key]['unknown'] += count

#         month_names = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

#         trends = []
#         for (year, month), data in sorted(month_data.items()):
#             trends.append({
#                 'month': f"{month_names[month]} {year}",
#                 'monthNum': month,
#                 'year': year,
#                 **data
#             })

#         return trends

    