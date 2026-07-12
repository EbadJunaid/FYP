#!/usr/bin/env python3
"""
Generic CA analysis pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.ca-analysis.
This replaces the old split outputs:
- ca-stats
- ca-analytics
- issuer-validation-matrix
"""

import argparse
import json
import os
from datetime import datetime, timezone
from math import log2
from pymongo import MongoClient
from scope_utils import add_scope_match, create_index_if_missing, get_scope_filter, get_scopes_for_entry, normalize_db_entries, scoped_doc_id

try:
    import numpy as np
except ImportError:
    np = None


CRITICAL_LINTS = {
    "e_ext_san_missing",
    "e_subject_common_name_not_from_san",
    "e_ext_san_not_critical_without_subject",
    "e_ext_authority_key_identifier_missing",
    "e_ext_policy_constraints_empty",
    "e_ext_policy_constraints_not_critical",
    "e_ext_name_constraints_not_in_ca",
    "e_ext_name_constraints_not_critical",
    "e_ext_policy_map_any_policy",
    "e_ext_key_usage_cert_sign_without_ca",
    "e_sub_cert_key_usage_cert_sign_bit_set",
    "e_sub_cert_key_usage_crl_sign_bit_set",
    "e_serial_number_longer_than_20_octets",
    "e_sub_cert_valid_time_too_long",
    "e_rsa_mod_less_than_2048_bits",
    "e_sub_cert_or_sub_ca_using_sha1",
    "e_signature_algorithm_not_supported",
    "e_sub_cert_aia_missing",
    "e_sub_cert_aia_does_not_contain_ocsp_url",
    "e_dnsname_bad_character_in_label",
    "e_dnsname_empty_label",
    "e_dnsname_label_too_long",
    "e_ext_san_dns_name_too_long",
}

W_ERR, W_WARN = 2.0, 1.0
MAX_VALIDITY_DAYS = 825
T_MAX = 730
DV_OIDS = {"2.23.140.1.2.1"}
OV_OIDS = {"2.23.140.1.2.2"}
EV_OIDS = {"2.23.140.1.1"}
INCLUDE_ACCS = False


def get_default_config_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(script_dir, "..", "..", ".."))
    return os.path.join(project_root, "project-config.json")


def load_db_entries(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return _normalize_db_entries(data)

    if isinstance(data, dict) and "databases" in data:
        return _normalize_db_entries(data["databases"])

    raise ValueError("Unsupported databases.json format")


def _normalize_db_entries(items):
    return normalize_db_entries(items)


def resolve_targets(db_names, entries):
    if not db_names:
        return entries

    lookup = {entry["main"]: entry for entry in entries}
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            targets.append({"main": name, "results": f"{name}-results", "countries": []})
    return targets


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def percentile(values, percent):
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


def get_safe(d, keys, default=None):
    cur = d
    for key in keys:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        else:
            return default
    return cur


def weighted_penalty_from_lints_noncritical(zlint_lints, critical_set):
    pen = 0.0
    for name, entry in (zlint_lints or {}).items():
        if name in critical_set:
            continue
        result = (entry.get("result") or "").lower() if isinstance(entry, dict) else ""
        if result == "error":
            pen += W_ERR
        elif result == "warn":
            pen += W_WARN
    return pen


def compute_penalty_p95_from_docs(docs, critical_set):
    vals = []
    for doc in docs:
        lints = (doc.get("zlint") or {}).get("lints") or {}
        vals.append(weighted_penalty_from_lints_noncritical(lints, critical_set))
    if not vals:
        return 10.0
    return max(percentile(vals, 95), 1.0)


def compute_zcs_from_lints(zlint_lints, norm_m, critical_set):
    pen = weighted_penalty_from_lints_noncritical(zlint_lints, critical_set)
    pen = min(pen, norm_m)
    return max(0.0, 1.0 - pen / norm_m)


def compute_zhfs(zlint_lints, critical_set):
    hits = sum(
        1 for lint_name in critical_set
        if (zlint_lints.get(lint_name) or {}).get("result") == "error"
    )
    return 1.0 - (hits / max(1, len(critical_set)))


def compute_khs(cert):
    size = (
        get_safe(cert, ["subject_key_info", "rsa_public_key", "length"])
        or get_safe(cert, ["subject_key_info", "ecdsa_public_key", "length"])
        or 0
    )
    algo = (get_safe(cert, ["subject_key_info", "key_algorithm", "name"], "") or "").upper()
    validity_len = get_safe(cert, ["validity", "length"], 0) or 0
    validity_ratio = min(validity_len / MAX_VALIDITY_DAYS, 1.0)
    age_score = 1.0 - validity_ratio
    bits_ok = 1.0 if size >= 2048 else 0.0
    algo_ok = 1.0 if algo in ["RSA", "ECDSA"] else 0.0
    return mean([bits_ok, algo_ok, age_score])


def compute_wklp(cert):
    rsa_len = get_safe(cert, ["subject_key_info", "rsa_public_key", "length"])
    ecdsa_len = get_safe(cert, ["subject_key_info", "ecdsa_public_key", "length"])
    length = rsa_len if rsa_len is not None else (ecdsa_len if ecdsa_len is not None else 2048)
    return 1.0 if (length is not None and length < 2048) else 0.0


def compute_kus(cert, seen_keys):
    key_hash = get_safe(cert, ["subject_key_info", "fingerprint_sha256"])
    if not key_hash:
        return 0.5
    reused = key_hash in seen_keys
    seen_keys.add(key_hash)
    return 0.0 if reused else 1.0


def compute_cads(ca_names):
    if not ca_names:
        return 0.0
    counts = {}
    for ca in ca_names:
        counts[ca] = counts.get(ca, 0) + 1
    m = len(counts)
    if m <= 1:
        return 0.0
    probabilities = [count / len(ca_names) for count in counts.values()]
    entropy = -sum(p * log2(p) for p in probabilities if p > 0)
    return min(1.0, entropy / log2(m))


def parse_iso_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "").replace("z", ""))
    except ValueError:
        return None


def compute_tsi(certs):
    timestamps = []
    for cert in certs:
        parsed = parse_iso_date(get_safe(cert, ["validity", "start"]))
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
        avg = mean(timestamps)
        std = mean([(ts - avg) ** 2 for ts in timestamps]) ** 0.5
    return max(0.0, 1.0 - (std / (T_MAX * 24 * 3600)))


def compute_iops(issuer_list):
    if len(issuer_list) <= 1:
        return 1.0
    same_adjacent = sum(1 for idx in range(1, len(issuer_list)) if issuer_list[idx] == issuer_list[idx - 1])
    return 1.0 - (same_adjacent / (len(issuer_list) - 1))


def compute_ekuvs(cert):
    eku = get_safe(cert, ["extensions", "extended_key_usage"], {}) or {}
    if not eku:
        return 0.0
    if eku.get("server_auth") or eku.get("client_auth"):
        return 1.0 if len(eku) <= 2 else 0.5
    return 0.0


def compute_pics(cert):
    policies = get_safe(cert, ["extensions", "certificate_policies"], []) or []
    if not isinstance(policies, list):
        return 0.0
    oids = {policy.get("id") for policy in policies if isinstance(policy, dict) and policy.get("id")}
    return 1.0 if (oids & DV_OIDS or oids & OV_OIDS or oids & EV_OIDS) else 0.0


def score_dvas_one(cert):
    val = (cert.get("validation_type") or cert.get("validation_level") or "").upper()
    if val == "EV":
        return 1.0
    if val == "OV":
        return 0.75
    if val == "DV":
        return 0.5
    return 0.0


def compute_ncvs(cert):
    return 1.0 if get_safe(cert, ["extensions", "name_constraints"]) else 0.0


def compute_gns(cert):
    risky = {"IR", "KP", "SY", "CU", "RU"}
    country = get_safe(cert, ["issuer", "country", 0])
    return 0.0 if country in risky else 1.0


def compute_accs(cert):
    if not INCLUDE_ACCS:
        return 0.5
    urls = get_safe(cert, ["extensions", "authority_info_access", "issuer_urls"], []) or []
    return 1.0 if urls else 0.0


def compute_revps(cert):
    ocsp = get_safe(cert, ["extensions", "authority_info_access", "ocsp_urls"], []) or []
    crl = get_safe(cert, ["extensions", "crl_distribution_points"], []) or []
    return 1.0 if (ocsp and crl) else (0.5 if (ocsp or crl) else 0.0)


def ca_name_from_cert(cert):
    issuer_org = get_safe(cert, ["issuer", "organization"], [])
    if isinstance(issuer_org, list) and issuer_org:
        return issuer_org[0]
    if isinstance(issuer_org, str):
        return issuer_org
    return get_safe(cert, ["issuer_dn"], "Unknown") or "Unknown"


def score_certificate_with_notebook_formula(doc, norm_m, seen_keys):
    cert = doc.get("parsed", {}) or {}
    zlint_lints = (doc.get("zlint") or {}).get("lints") or {}

    zcs = compute_zcs_from_lints(zlint_lints, norm_m, CRITICAL_LINTS)
    zhfs = compute_zhfs(zlint_lints, CRITICAL_LINTS)
    core_hygiene = mean([zcs, zhfs])

    khs = compute_khs(cert)
    wklp = compute_wklp(cert)
    kus = compute_kus(cert, seen_keys)
    crypto_health = mean([khs, kus, wklp])

    issuer_name = get_safe(cert, ["issuer_dn"])
    cads = compute_cads([issuer_name])
    tsi = compute_tsi([cert])
    iops = compute_iops([issuer_name])
    operational_stability = mean([cads, tsi, iops])

    ekuvs = compute_ekuvs(cert)
    pics = compute_pics(cert)
    dvas = score_dvas_one(cert)
    ncvs = compute_ncvs(cert)
    policy_compliance = mean([ekuvs, pics, dvas, ncvs])

    gns = compute_gns(cert)
    accs = compute_accs(cert)
    revps = compute_revps(cert)
    risk_factors = mean([gns, accs, revps])

    final_score = mean([
        core_hygiene,
        crypto_health,
        operational_stability,
        policy_compliance,
        risk_factors,
    ]) * 100.0

    return {
        "score": round(final_score, 2),
        "coreHygiene": round(core_hygiene * 100, 2),
        "cryptoHealth": round(crypto_health * 100, 2),
        "operationalStability": round(operational_stability * 100, 2),
        "policyCompliance": round(policy_compliance * 100, 2),
        "riskFactors": round(risk_factors * 100, 2),
    }


def notebook_formula_description():
    return {
        "coreHygiene": "mean(ZCS, ZHFS), where ZCS uses non-critical zlint error/warn penalties normalized by P95 and ZHFS penalizes curated critical zlint errors",
        "cryptoHealth": "mean(KHS, KUS, WKLP) using the notebook functions exactly",
        "operationalStability": "mean(CADS, TSI, IOPS)",
        "policyCompliance": "mean(EKUVS, PICS, DVAS, NCVS)",
        "riskFactors": "mean(GNS, ACCS, REVPS)",
        "finalScore": "mean(core_hygiene, crypto_health, operational_stability, policy_compliance, risk_factors) * 100",
    }


def log(message):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {message}", flush=True)


def compute_ca_notebook_scores(source_collection, scope, limit=None):
    base_query = get_scope_filter(scope)
    pass1_projection = {
        "parsed.subject_dn": 1,
        "parsed.issuer_dn": 1,
        "parsed.basic_constraints.ca": 1,
        "zlint.lints": 1,
    }
    pass2_projection = {
        "parsed.issuer.organization": 1,
        "parsed.issuer_dn": 1,
        "parsed.subject_dn": 1,
        "parsed.basic_constraints.ca": 1,
        "parsed.validity": 1,
        "parsed.subject_key_info": 1,
        "parsed.extensions.extended_key_usage": 1,
        "parsed.extensions.certificate_policies": 1,
        "parsed.extensions.name_constraints": 1,
        "parsed.extensions.authority_info_access.ocsp_urls": 1,
        "parsed.extensions.authority_info_access.issuer_urls": 1,
        "parsed.extensions.crl_distribution_points": 1,
        "parsed.validation_level": 1,
        "parsed.validation_type": 1,
        "parsed.issuer.country": 1,
        "zlint.lints": 1,
    }

    def is_leaf_certificate(doc):
        parsed = doc.get("parsed", {}) or {}
        basic_constraints = parsed.get("basic_constraints")
        is_self_subject = parsed.get("subject_dn") and parsed.get("subject_dn") == parsed.get("issuer_dn")
        is_ca = isinstance(basic_constraints, dict) and basic_constraints.get("ca") is True
        return not is_self_subject and not is_ca

    def scoped_cursor(projection):
        cursor = source_collection.find(base_query, projection).batch_size(2000)
        if limit:
            cursor = cursor.limit(limit)
        return cursor

    log(f"CA ranking pass 1/2: scanning leaf certificates for zlint normalization (scope={scope})")
    penalty_values = []
    scored_leaf_count = 0
    cursor = scoped_cursor(pass1_projection)
    try:
        for doc in cursor:
            if not is_leaf_certificate(doc):
                continue
            scored_leaf_count += 1
            zlint_lints = (doc.get("zlint") or {}).get("lints") or {}
            penalty_values.append(weighted_penalty_from_lints_noncritical(zlint_lints, CRITICAL_LINTS))
            if scored_leaf_count % 50000 == 0:
                log(f"  pass 1/2 processed {scored_leaf_count:,} leaf certificates")
    finally:
        cursor.close()

    norm_m = max(percentile(penalty_values, 95), 1.0) if penalty_values else 10.0
    log(f"CA ranking pass 1/2 done: {scored_leaf_count:,} leaf certificates, zlint P95={norm_m:.2f}")
    seen_keys = set()
    ca_scores = {}

    log(f"CA ranking pass 2/2: scoring certificates and aggregating by CA (scope={scope})")
    processed_scores = 0
    cursor = scoped_cursor(pass2_projection)
    try:
        for doc in cursor:
            if not is_leaf_certificate(doc):
                continue
            cert = doc.get("parsed", {}) or {}
            ca_name = ca_name_from_cert(cert)
            if not ca_name or ca_name == "Unknown":
                continue
            score = score_certificate_with_notebook_formula(doc, norm_m, seen_keys)
            entry = ca_scores.setdefault(ca_name, {
                "count": 0,
                "score": 0.0,
                "coreHygiene": 0.0,
                "cryptoHealth": 0.0,
                "operationalStability": 0.0,
                "policyCompliance": 0.0,
                "riskFactors": 0.0,
            })
            entry["count"] += 1
            entry["score"] += score["score"]
            entry["coreHygiene"] += score["coreHygiene"]
            entry["cryptoHealth"] += score["cryptoHealth"]
            entry["operationalStability"] += score["operationalStability"]
            entry["policyCompliance"] += score["policyCompliance"]
            entry["riskFactors"] += score["riskFactors"]
            processed_scores += 1
            if processed_scores % 50000 == 0:
                log(f"  pass 2/2 scored {processed_scores:,} certificates across {len(ca_scores):,} CAs")
    finally:
        cursor.close()
    log(f"CA ranking pass 2/2 done: scored {processed_scores:,} certificates across {len(ca_scores):,} CAs")

    formatted = {}
    for ca_name, data in ca_scores.items():
        count = data["count"]
        formatted[ca_name] = {
            "score": round(data["score"] / count, 2),
            "scoreSampleCount": count,
            "coreHygiene": round(data["coreHygiene"] / count, 2),
            "cryptoHealth": round(data["cryptoHealth"] / count, 2),
            "operationalStability": round(data["operationalStability"] / count, 2),
            "policyCompliance": round(data["policyCompliance"] / count, 2),
            "riskFactors": round(data["riskFactors"] / count, 2),
        }
    return formatted, norm_m, scored_leaf_count


def compute_ca_stats(client, main_db, results_db, top_limit=50, verify=False, scope="all", limit=None):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    target_collection = results_db_ref["ca-analysis"]

    start_time = datetime.now(timezone.utc)
    log(f"CA analysis started: {main_db} -> {results_db} scope={scope}")

    # Legacy split collections are cleared so stale data is not mistaken for
    # the current materialized view.
    for collection_name in ["ca-stats", "ca-analytics", "issuer-validation-matrix"]:
        results_db_ref[collection_name].drop()

    scope_filter = get_scope_filter(scope)
    scoped = bool(scope_filter)
    if scope_filter:
        try:
            total_certs = source_collection.count_documents(scope_filter, hint="idx_scope")
        except Exception:
            total_certs = source_collection.count_documents(scope_filter)
    else:
        total_certs = source_collection.estimated_document_count()
    if limit:
        total_certs = min(total_certs, limit)
    log(f"Total certificates for scope={scope}: {total_certs:,}")

    colors = [
        "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444",
        "#06b6d4", "#14b8a6", "#6366f1", "#ec4899", "#84cc16",
        "#f97316", "#a855f7", "#22c55e", "#0ea5e9", "#d946ef",
        "#eab308", "#6b7280",
    ]

    ca_validation_pipeline = ([{"$limit": limit}] if limit else []) + [
        {
            "$group": {
                "_id": {
                    "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                    "validationLevel": {"$ifNull": ["$parsed.validation_level", "Unknown"]},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    try:
        log("Computing CA counts and validation-level matrix")
        validation_results = list(source_collection.aggregate(
            add_scope_match(ca_validation_pipeline, scope),
            hint="idx_scope_issuer_validation" if scoped else "idx_issuer_org_validation_level",
            allowDiskUse=True,
        ))
    except Exception:
        log("CA validation aggregation hint failed; retrying without hint")
        validation_results = list(source_collection.aggregate(
            add_scope_match(ca_validation_pipeline, scope),
            allowDiskUse=True,
        ))

    issuer_map = {}
    for record in validation_results:
        issuer = record["_id"]["issuer"]
        if not issuer:
            continue
        validation_level = record["_id"].get("validationLevel") or "Unknown"
        count = record["count"]

        issuer_entry = issuer_map.setdefault(issuer, {
            "name": issuer,
            "count": 0,
            "validationLevel": [],
        })
        issuer_entry["count"] += count
        issuer_entry["validationLevel"].append({
            "validationlevel_type": validation_level,
            "count": count,
        })

    ca_records = sorted(
        issuer_map.values(),
        key=lambda item: item["count"],
        reverse=True,
    )
    total_with_issuer = sum(record["count"] for record in ca_records)
    max_count = ca_records[0]["count"] if ca_records else 0
    log(f"CA counts done: {len(ca_records):,} issuers with organization values")
    ca_score_map, zlint_norm_m, scored_leaf_count = compute_ca_notebook_scores(
        source_collection,
        scope,
        limit=limit,
    )
    log(f"CA ranking scores done: {len(ca_score_map):,} scored CAs")

    ca_list = []
    for index, record in enumerate(ca_records):
        score_data = ca_score_map.get(record["name"], {})
        ca_list.append({
            "ca_id": f"ca-{index}",
            "name": record["name"],
            "count": record["count"],
            "percentage": round((record["count"] / total_with_issuer) * 100, 1) if total_with_issuer else 0,
            "color": colors[index % len(colors)],
            "rank": index + 1,
            "score": score_data.get("score", 0),
            "scoreRank": None,
            "scoreSampleCount": score_data.get("scoreSampleCount", 0),
            "coreHygiene": score_data.get("coreHygiene", 0),
            "cryptoHealth": score_data.get("cryptoHealth", 0),
            "operationalStability": score_data.get("operationalStability", 0),
            "policyCompliance": score_data.get("policyCompliance", 0),
            "riskFactors": score_data.get("riskFactors", 0),
            "validationLevel": sorted(
                record["validationLevel"],
                key=lambda item: item["count"],
                reverse=True,
            ),
        })

    scored_cas = sorted(
        [item for item in ca_list if item.get("scoreSampleCount", 0) > 0],
        key=lambda item: item.get("score", 0),
        reverse=True,
    )
    for score_index, item in enumerate(scored_cas, start=1):
        item["scoreRank"] = score_index

    try:
        log("Counting self-signed certificates")
        self_signed_count = source_collection.count_documents(
            {"$and": [{"parsed.signature.self_signed": True}, scope_filter]} if scope_filter else {"parsed.signature.self_signed": True},
            hint="idx_scope_self_signed" if scoped else "idx_self_signed",
        )
    except Exception:
        self_signed_count = source_collection.count_documents(
            {"$and": [{"parsed.signature.self_signed": True}, scope_filter]} if scope_filter else {"parsed.signature.self_signed": True}
        )

    country_pipeline = [
        {"$unwind": {"path": "$parsed.issuer.country", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$parsed.issuer.country"}},
        {"$match": {"_id": {"$ne": None}}},
        {"$count": "total"},
    ]
    try:
        log("Computing unique issuer countries")
        country_result = list(source_collection.aggregate(
            add_scope_match(country_pipeline, scope),
            hint="idx_scope_issuer_country" if scoped else "idx_issuer_country",
            allowDiskUse=True,
        ))
    except Exception:
        country_result = list(source_collection.aggregate(add_scope_match(country_pipeline, scope), allowDiskUse=True))
    unique_countries = country_result[0]["total"] if country_result else 0

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    analysis_document = {
        "_id": scoped_doc_id("ca_analysis", scope),
        "scope": scope,
        "total_cas": len(ca_list),
        "total_certs": total_certs,
        "self_signed_count": self_signed_count,
        "unique_countries": unique_countries,
        "max_ca_count": max_count,
        "computed_at": datetime.now(timezone.utc),
        "computation_duration_seconds": duration,
        "source_database": main_db,
        "source_collection": "certificates",
        "ranking_formula": notebook_formula_description(),
        "ranking_zlint_norm_p95": zlint_norm_m,
        "ranking_scored_leaf_count": scored_leaf_count,

        "ca-list": ca_list,
        "top_limit": top_limit,
    }

    target_collection.replace_one({"scope": scope}, analysis_document, upsert=True)
    log("Stored ca-analysis document")
    create_index_if_missing(target_collection, "scope", name="idx_ca_analysis_scope", background=True)
    create_index_if_missing(target_collection, "computed_at", name="idx_ca_analysis_computed_at", background=True)
    create_index_if_missing(target_collection, "ca-list.rank", name="idx_ca_analysis_ca_rank", background=True)
    create_index_if_missing(target_collection, "ca-list.scoreRank", name="idx_ca_analysis_ca_score_rank", background=True)
    create_index_if_missing(target_collection, "ca-list.score", name="idx_ca_analysis_ca_score", background=True)
    create_index_if_missing(target_collection, "ca-list.name", name="idx_ca_analysis_ca_name", background=True)

    if verify:
        stored = target_collection.find_one({"scope": scope})
        if not stored:
            raise RuntimeError("Verification failed: missing ca-analysis document")
        if stored.get("total_cas") != len(ca_list):
            raise RuntimeError("Verification failed: total_cas mismatch")
        if stored.get("total_certs") != total_certs:
            raise RuntimeError("Verification failed: total_certs mismatch")
        if sum(ca["count"] for ca in stored.get("ca-list", [])) != total_with_issuer:
            raise RuntimeError("Verification failed: ca-list total mismatch")
    log(f"CA analysis finished: scope={scope}, duration={duration:.2f}s")



def main():
    parser = argparse.ArgumentParser(description="Generic CA stats pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--limit", type=int, default=50, help="Top issuers expected by old matrix script; full CA list is still stored")
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit source documents for fast testing only")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        for scope, _country in get_scopes_for_entry(target):
            compute_ca_stats(
                client,
                target["main"],
                target["results"],
                top_limit=args.limit,
                verify=args.verify,
                scope=scope,
                limit=args.sample_limit,
            )
    client.close()


if __name__ == "__main__":
    main()
