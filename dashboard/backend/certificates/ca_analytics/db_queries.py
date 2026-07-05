# backend/certificates/ca_models.py
# CA (Certificate Authority) analytics model utilities extracted from CertificateModel for page separation.

from datetime import datetime, timezone
#from tkinter.font import names
from math import log2
from typing import List, Dict, Any, Optional
from ..db import db, MongoDBClient

try:
    import numpy as np
except ImportError:
    np = None


class CAModel:
    """Model class for CA analytics operations."""

    # Use the same certificates collection reference as CertificateModel
    collection = db['certificates']
    _ranking_colors = [
        '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444',
        '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
    ]
    _critical_lints = {
        'e_ext_san_missing',
        'e_subject_common_name_not_from_san',
        'e_ext_san_not_critical_without_subject',
        'e_ext_authority_key_identifier_missing',
        'e_ext_policy_constraints_empty',
        'e_ext_policy_constraints_not_critical',
        'e_ext_name_constraints_not_in_ca',
        'e_ext_name_constraints_not_critical',
        'e_ext_policy_map_any_policy',
        'e_ext_key_usage_cert_sign_without_ca',
        'e_sub_cert_key_usage_cert_sign_bit_set',
        'e_sub_cert_key_usage_crl_sign_bit_set',
        'e_serial_number_longer_than_20_octets',
        'e_sub_cert_valid_time_too_long',
        'e_rsa_mod_less_than_2048_bits',
        'e_sub_cert_or_sub_ca_using_sha1',
        'e_signature_algorithm_not_supported',
        'e_sub_cert_aia_missing',
        'e_sub_cert_aia_does_not_contain_ocsp_url',
        'e_dnsname_bad_character_in_label',
        'e_dnsname_empty_label',
        'e_dnsname_label_too_long',
        'e_ext_san_dns_name_too_long',
    }
    _dv_oids = {'2.23.140.1.2.1'}
    _ov_oids = {'2.23.140.1.2.2'}
    _ev_oids = {'2.23.140.1.1'}

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

    @staticmethod
    def _mean(values) -> float:
        values = list(values)
        return sum(values) / len(values) if values else 0.0

    @staticmethod
    def _percentile(values, percent) -> float:
        values = sorted(values)
        if not values:
            return 0.0
        if np is not None:
            return float(np.percentile(values, percent))
        k = (len(values) - 1) * (percent / 100)
        low = int(k)
        high = min(low + 1, len(values) - 1)
        if low == high:
            return float(values[low])
        return float(values[low] + (values[high] - values[low]) * (k - low))

    @staticmethod
    def _get_safe(data, keys, default=None):
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    @classmethod
    def _ca_name_from_cert(cls, cert: Dict[str, Any]) -> str:
        issuer_org = cls._get_safe(cert, ['issuer', 'organization'], [])
        if isinstance(issuer_org, list) and issuer_org:
            return issuer_org[0]
        if isinstance(issuer_org, str):
            return issuer_org
        return cls._get_safe(cert, ['issuer_dn'], 'Unknown') or 'Unknown'

    @staticmethod
    def _parse_iso_date(value):
        if not value:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value).replace('Z', '').replace('z', ''))
        except ValueError:
            return None

    @classmethod
    def _is_leaf_certificate(cls, doc: Dict[str, Any]) -> bool:
        parsed = doc.get('parsed', {}) or {}
        basic_constraints = parsed.get('basic_constraints')
        is_self_subject = parsed.get('subject_dn') and parsed.get('subject_dn') == parsed.get('issuer_dn')
        is_ca = isinstance(basic_constraints, dict) and basic_constraints.get('ca') is True
        return not is_self_subject and not is_ca

    @classmethod
    def _weighted_penalty_from_lints_noncritical(cls, zlint_lints: Dict[str, Any]) -> float:
        penalty = 0.0
        for name, entry in (zlint_lints or {}).items():
            if name in cls._critical_lints:
                continue
            result = (entry.get('result') or '').lower() if isinstance(entry, dict) else ''
            if result == 'error':
                penalty += 2.0
            elif result == 'warn':
                penalty += 1.0
        return penalty

    @classmethod
    def _compute_zcs_from_lints(cls, zlint_lints: Dict[str, Any], norm_m: float) -> float:
        penalty = min(cls._weighted_penalty_from_lints_noncritical(zlint_lints), norm_m)
        return max(0.0, 1.0 - penalty / norm_m)

    @classmethod
    def _compute_zhfs(cls, zlint_lints: Dict[str, Any]) -> float:
        hits = sum(
            1 for lint_name in cls._critical_lints
            if (zlint_lints.get(lint_name) or {}).get('result') == 'error'
        )
        return 1.0 - (hits / max(1, len(cls._critical_lints)))

    @classmethod
    def _compute_khs(cls, cert: Dict[str, Any]) -> float:
        size = (
            cls._get_safe(cert, ['subject_key_info', 'rsa_public_key', 'length'])
            or cls._get_safe(cert, ['subject_key_info', 'ecdsa_public_key', 'length'])
            or 0
        )
        algo = (cls._get_safe(cert, ['subject_key_info', 'key_algorithm', 'name'], '') or '').upper()
        validity_len = cls._get_safe(cert, ['validity', 'length'], 0) or 0
        age_score = 1.0 - min(validity_len / 825, 1.0)
        bits_ok = 1.0 if size >= 2048 else 0.0
        algo_ok = 1.0 if algo in ['RSA', 'ECDSA'] else 0.0
        return cls._mean([bits_ok, algo_ok, age_score])

    @classmethod
    def _compute_wklp(cls, cert: Dict[str, Any]) -> float:
        rsa_len = cls._get_safe(cert, ['subject_key_info', 'rsa_public_key', 'length'])
        ecdsa_len = cls._get_safe(cert, ['subject_key_info', 'ecdsa_public_key', 'length'])
        length = rsa_len if rsa_len is not None else (ecdsa_len if ecdsa_len is not None else 2048)
        return 1.0 if (length is not None and length < 2048) else 0.0

    @classmethod
    def _compute_kus(cls, cert: Dict[str, Any], seen_keys: set) -> float:
        key_hash = cls._get_safe(cert, ['subject_key_info', 'fingerprint_sha256'])
        if not key_hash:
            return 0.5
        reused = key_hash in seen_keys
        seen_keys.add(key_hash)
        return 0.0 if reused else 1.0

    @staticmethod
    def _compute_cads(ca_names) -> float:
        if not ca_names:
            return 0.0
        counts = {}
        for ca in ca_names:
            counts[ca] = counts.get(ca, 0) + 1
        if len(counts) <= 1:
            return 0.0
        probabilities = [count / len(ca_names) for count in counts.values()]
        entropy = -sum(probability * log2(probability) for probability in probabilities if probability > 0)
        return min(1.0, entropy / log2(len(counts)))

    @classmethod
    def _compute_tsi(cls, certs) -> float:
        timestamps = []
        for cert in certs:
            parsed = cls._parse_iso_date(cls._get_safe(cert, ['validity', 'start']))
            if parsed:
                try:
                    timestamps.append(parsed.timestamp())
                except (OSError, OverflowError, ValueError):
                    continue
        if len(timestamps) < 2:
            return 0.5
        if np is not None:
            std = float(np.std(timestamps))
        else:
            avg = cls._mean(timestamps)
            std = cls._mean([(timestamp - avg) ** 2 for timestamp in timestamps]) ** 0.5
        return max(0.0, 1.0 - (std / (730 * 24 * 3600)))

    @staticmethod
    def _compute_iops(issuer_list) -> float:
        if len(issuer_list) <= 1:
            return 1.0
        same_adjacent = sum(1 for index in range(1, len(issuer_list)) if issuer_list[index] == issuer_list[index - 1])
        return 1.0 - (same_adjacent / (len(issuer_list) - 1))

    @classmethod
    def _compute_ekuvs(cls, cert: Dict[str, Any]) -> float:
        eku = cls._get_safe(cert, ['extensions', 'extended_key_usage'], {}) or {}
        if not eku:
            return 0.0
        if eku.get('server_auth') or eku.get('client_auth'):
            return 1.0 if len(eku) <= 2 else 0.5
        return 0.0

    @classmethod
    def _compute_pics(cls, cert: Dict[str, Any]) -> float:
        policies = cls._get_safe(cert, ['extensions', 'certificate_policies'], []) or []
        if not isinstance(policies, list):
            return 0.0
        oids = {policy.get('id') for policy in policies if isinstance(policy, dict) and policy.get('id')}
        return 1.0 if (oids & cls._dv_oids or oids & cls._ov_oids or oids & cls._ev_oids) else 0.0

    @staticmethod
    def _score_dvas_one(cert: Dict[str, Any]) -> float:
        validation = (cert.get('validation_type') or cert.get('validation_level') or '').upper()
        if validation == 'EV':
            return 1.0
        if validation == 'OV':
            return 0.75
        if validation == 'DV':
            return 0.5
        return 0.0

    @classmethod
    def _compute_ncvs(cls, cert: Dict[str, Any]) -> float:
        return 1.0 if cls._get_safe(cert, ['extensions', 'name_constraints']) else 0.0

    @classmethod
    def _compute_gns(cls, cert: Dict[str, Any]) -> float:
        country = cls._get_safe(cert, ['issuer', 'country', 0])
        return 0.0 if country in {'IR', 'KP', 'SY', 'CU', 'RU'} else 1.0

    @staticmethod
    def _compute_accs() -> float:
        return 0.5

    @classmethod
    def _compute_revps(cls, cert: Dict[str, Any]) -> float:
        ocsp = cls._get_safe(cert, ['extensions', 'authority_info_access', 'ocsp_urls'], []) or []
        crl = cls._get_safe(cert, ['extensions', 'crl_distribution_points'], []) or []
        return 1.0 if (ocsp and crl) else (0.5 if (ocsp or crl) else 0.0)

    @classmethod
    def _score_certificate_with_notebook_formula(cls, doc: Dict[str, Any], norm_m: float, seen_keys: set) -> Dict[str, float]:
        cert = doc.get('parsed', {}) or {}
        zlint_lints = (doc.get('zlint') or {}).get('lints') or {}

        core_hygiene = cls._mean([
            cls._compute_zcs_from_lints(zlint_lints, norm_m),
            cls._compute_zhfs(zlint_lints),
        ])
        crypto_health = cls._mean([
            cls._compute_khs(cert),
            cls._compute_kus(cert, seen_keys),
            cls._compute_wklp(cert),
        ])
        issuer_name = cls._get_safe(cert, ['issuer_dn'])
        operational_stability = cls._mean([
            cls._compute_cads([issuer_name]),
            cls._compute_tsi([cert]),
            cls._compute_iops([issuer_name]),
        ])
        policy_compliance = cls._mean([
            cls._compute_ekuvs(cert),
            cls._compute_pics(cert),
            cls._score_dvas_one(cert),
            cls._compute_ncvs(cert),
        ])
        risk_factors = cls._mean([
            cls._compute_gns(cert),
            cls._compute_accs(),
            cls._compute_revps(cert),
        ])
        final_score = cls._mean([
            core_hygiene,
            crypto_health,
            operational_stability,
            policy_compliance,
            risk_factors,
        ]) * 100
        return {
            'score': round(final_score, 2),
            'coreHygiene': round(core_hygiene * 100, 2),
            'cryptoHealth': round(crypto_health * 100, 2),
            'operationalStability': round(operational_stability * 100, 2),
            'policyCompliance': round(policy_compliance * 100, 2),
            'riskFactors': round(risk_factors * 100, 2),
        }

    @classmethod
    def _empty_ranking_response(cls, group_by: str, mode: str) -> Dict[str, Any]:
        return {
            'groupBy': group_by,
            'metricLabel': cls._ranking_group_config(group_by)['label'],
            'mode': mode,
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

    @classmethod
    def _format_ranking_items(cls, ca_list: List[Dict[str, Any]], total_certs: int, limit: int, mode: str, formula: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ca_list = [
            item for item in ca_list
            if item.get('scoreSampleCount', 0) > 0
        ]
        if not ca_list:
            empty = cls._empty_ranking_response('ca', mode)
            empty['summary']['totalCertificates'] = total_certs
            return empty

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
            'mode': mode,
            'items': limited,
            'summary': {
                'rankedCount': len(items),
                'topName': top.get('name') if top else None,
                'topScore': top.get('score', 0) if top else 0,
                'averageScore': round(sum(entry.get('score', 0) for entry in items) / len(items), 2) if items else 0,
                'totalCertificates': total_certs,
                'bestHygieneName': best_hygiene.get('name') if best_hygiene else None,
            },
            'formula': formula or cls._notebook_ranking_formula(),
        }

    @classmethod
    def get_ranking_fast(cls, limit: int = 20, group_by: str = 'ca') -> Dict[str, Any]:
        group_by = group_by if group_by in cls._ranking_groups else 'ca'
        limit = max(1, min(int(limit or 20), 5000))

        if group_by != 'ca':
            return cls._empty_ranking_response(group_by, 'precomputed')

        analysis_doc = cls._get_ca_analysis_doc()
        if not analysis_doc:
            return cls.get_ranking(limit=limit, group_by=group_by)

        ca_list = analysis_doc.get('ca-list', [])
        if not any(item.get('scoreSampleCount', 0) > 0 for item in ca_list):
            return cls.get_ranking(limit=limit, group_by=group_by)

        return cls._format_ranking_items(
            ca_list=ca_list,
            total_certs=analysis_doc.get('total_certs', 0),
            limit=limit,
            mode='precomputed',
            formula=analysis_doc.get('ranking_formula') or cls._notebook_ranking_formula(),
        )

    @classmethod
    def get_ranking(cls, limit: int = 20, group_by: str = 'ca') -> Dict[str, Any]:
        group_by = group_by if group_by in cls._ranking_groups else 'ca'
        limit = max(1, min(int(limit or 20), 5000))
        if group_by != 'ca':
            return cls._empty_ranking_response(group_by, 'live')

        total_certs = cls.collection.estimated_document_count()
        ca_validation_pipeline = [
            {
                '$group': {
                    '_id': {
                        'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
                        'validationLevel': {'$ifNull': ['$parsed.validation_level', 'Unknown']},
                    },
                    'count': {'$sum': 1},
                }
            },
            {'$sort': {'count': -1}},
        ]
        validation_results = list(cls.collection.aggregate(ca_validation_pipeline, allowDiskUse=True))

        issuer_map = {}
        for record in validation_results:
            issuer = record['_id']['issuer']
            if not issuer:
                continue
            issuer_entry = issuer_map.setdefault(issuer, {
                'name': issuer,
                'count': 0,
                'validationLevel': [],
            })
            issuer_entry['count'] += record['count']
            issuer_entry['validationLevel'].append({
                'validationlevel_type': record['_id'].get('validationLevel') or 'Unknown',
                'count': record['count'],
            })

        ca_records = sorted(issuer_map.values(), key=lambda item: item['count'], reverse=True)
        total_with_issuer = sum(record['count'] for record in ca_records)
        ca_score_map = cls._compute_live_ca_scores()

        colors = [
            '#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444',
            '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
            '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#d946ef',
            '#eab308', '#6b7280',
        ]
        ca_list = []
        for index, record in enumerate(ca_records):
            score_data = ca_score_map.get(record['name'], {})
            ca_list.append({
                'ca_id': f'ca-{index}',
                'name': record['name'],
                'count': record['count'],
                'percentage': round((record['count'] / total_with_issuer) * 100, 1) if total_with_issuer else 0,
                'color': colors[index % len(colors)],
                'rank': index + 1,
                'score': score_data.get('score', 0),
                'scoreRank': None,
                'scoreSampleCount': score_data.get('scoreSampleCount', 0),
                'coreHygiene': score_data.get('coreHygiene', 0),
                'cryptoHealth': score_data.get('cryptoHealth', 0),
                'operationalStability': score_data.get('operationalStability', 0),
                'policyCompliance': score_data.get('policyCompliance', 0),
                'riskFactors': score_data.get('riskFactors', 0),
                'validationLevel': sorted(record['validationLevel'], key=lambda item: item['count'], reverse=True),
            })

        scored_cas = sorted(
            [item for item in ca_list if item.get('scoreSampleCount', 0) > 0],
            key=lambda item: item.get('score', 0),
            reverse=True,
        )
        for score_index, item in enumerate(scored_cas, start=1):
            item['scoreRank'] = score_index

        return cls._format_ranking_items(
            ca_list=ca_list,
            total_certs=total_certs,
            limit=limit,
            mode='live',
            formula=cls._notebook_ranking_formula(),
        )

    @classmethod
    def _compute_live_ca_scores(cls) -> Dict[str, Dict[str, Any]]:
        pass1_projection = {
            'parsed.subject_dn': 1,
            'parsed.issuer_dn': 1,
            'parsed.basic_constraints.ca': 1,
            'zlint.lints': 1,
        }
        pass2_projection = {
            'parsed.issuer.organization': 1,
            'parsed.issuer_dn': 1,
            'parsed.subject_dn': 1,
            'parsed.basic_constraints.ca': 1,
            'parsed.validity': 1,
            'parsed.subject_key_info': 1,
            'parsed.extensions.extended_key_usage': 1,
            'parsed.extensions.certificate_policies': 1,
            'parsed.extensions.name_constraints': 1,
            'parsed.extensions.authority_info_access.ocsp_urls': 1,
            'parsed.extensions.authority_info_access.issuer_urls': 1,
            'parsed.extensions.crl_distribution_points': 1,
            'parsed.validation_level': 1,
            'parsed.validation_type': 1,
            'parsed.issuer.country': 1,
            'zlint.lints': 1,
        }

        penalty_values = []
        for doc in cls.collection.find({}, pass1_projection).batch_size(2000):
            if not cls._is_leaf_certificate(doc):
                continue
            zlint_lints = (doc.get('zlint') or {}).get('lints') or {}
            penalty_values.append(cls._weighted_penalty_from_lints_noncritical(zlint_lints))
        norm_m = max(cls._percentile(penalty_values, 95), 1.0) if penalty_values else 10.0

        seen_keys = set()
        ca_scores = {}
        for doc in cls.collection.find({}, pass2_projection).batch_size(2000):
            if not cls._is_leaf_certificate(doc):
                continue
            cert = doc.get('parsed', {}) or {}
            ca_name = cls._ca_name_from_cert(cert)
            if not ca_name or ca_name == 'Unknown':
                continue
            score = cls._score_certificate_with_notebook_formula(doc, norm_m, seen_keys)
            entry = ca_scores.setdefault(ca_name, {
                'count': 0,
                'score': 0.0,
                'coreHygiene': 0.0,
                'cryptoHealth': 0.0,
                'operationalStability': 0.0,
                'policyCompliance': 0.0,
                'riskFactors': 0.0,
            })
            entry['count'] += 1
            entry['score'] += score['score']
            entry['coreHygiene'] += score['coreHygiene']
            entry['cryptoHealth'] += score['cryptoHealth']
            entry['operationalStability'] += score['operationalStability']
            entry['policyCompliance'] += score['policyCompliance']
            entry['riskFactors'] += score['riskFactors']

        formatted = {}
        for ca_name, data in ca_scores.items():
            count = data['count']
            formatted[ca_name] = {
                'score': round(data['score'] / count, 2),
                'scoreSampleCount': count,
                'coreHygiene': round(data['coreHygiene'] / count, 2),
                'cryptoHealth': round(data['cryptoHealth'] / count, 2),
                'operationalStability': round(data['operationalStability'] / count, 2),
                'policyCompliance': round(data['policyCompliance'] / count, 2),
                'riskFactors': round(data['riskFactors'] / count, 2),
            }
        return formatted

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
