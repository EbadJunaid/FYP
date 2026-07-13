#!/usr/bin/env python3
"""
Generic CA analysis pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.ca-analysis.
This replaces the old split outputs:
- ca-stats
- ca-analytics
- issuer-validation-matrix

Optimized: all scopes ("all" + every configured country) are computed together.
The zlint penalty / critical-hit numbers are computed server-side with
aggregation expressions (so the large zlint.lints subdocuments never leave
MongoDB) and the certificate scoring scan runs once, bucketing per scope.
Output documents keep the exact same shape, ids and index names.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from math import log2
from pymongo import MongoClient
from scope_utils import create_index_if_missing, get_scopes_for_entry, normalize_db_entries, scoped_doc_id

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


# --- Server-side aggregation expressions -----------------------------------
# These mirror weighted_penalty_from_lints_noncritical / compute_zhfs exactly,
# so the heavy zlint.lints subdocuments are reduced to two numbers in MongoDB
# instead of being shipped to Python for every certificate.

_CRITICAL_LINT_LIST = sorted(CRITICAL_LINTS)

_LINTS_ARRAY_EXPR = {
    "$cond": [
        {"$eq": [{"$type": "$zlint.lints"}, "object"]},
        {"$objectToArray": "$zlint.lints"},
        [],
    ]
}

_THIS_RESULT_LOWER = {
    "$cond": [
        {"$eq": [{"$type": "$$this.v.result"}, "string"]},
        {"$toLower": "$$this.v.result"},
        "",
    ]
}

# The lints subdocument holds ~250+ entries per certificate but almost all of
# them are pass/NA. Reduce it to just the error/warn entries first (and skip
# the whole array when zlint's own summary flags say there is nothing to
# find), so the penalty / critical-hit expressions below only touch a handful
# of entries per document.
ERR_WARN_LINTS_EXPR = {
    "$cond": [
        {
            "$and": [
                {"$eq": [{"$ifNull": ["$zlint.errors_present", True]}, False]},
                {"$eq": [{"$ifNull": ["$zlint.warnings_present", True]}, False]},
            ]
        },
        [],
        {
            "$filter": {
                "input": _LINTS_ARRAY_EXPR,
                "cond": {"$in": [_THIS_RESULT_LOWER, ["error", "warn"]]},
            }
        },
    ]
}

# Sum of W_ERR / W_WARN over non-critical lints whose (lowercased) result is
# error / warn — identical to weighted_penalty_from_lints_noncritical().
# Every entry of $zlintErrWarn is already error or warn, so the else branch of
# the inner $cond is exactly the warn case.
PENALTY_EXPR = {
    "$reduce": {
        "input": "$zlintErrWarn",
        "initialValue": 0.0,
        "in": {
            "$add": [
                "$$value",
                {
                    "$cond": [
                        {"$in": ["$$this.k", _CRITICAL_LINT_LIST]},
                        0.0,
                        {"$cond": [{"$eq": [_THIS_RESULT_LOWER, "error"]}, W_ERR, W_WARN]},
                    ]
                },
            ]
        },
    }
}

# Count of critical lints whose raw result equals "error" — identical to the
# counting loop inside compute_zhfs() (which does not lowercase). A raw
# "error" always survives the lowercased error/warn filter above, so counting
# inside $zlintErrWarn is exact.
CRIT_HITS_EXPR = {
    "$size": {
        "$filter": {
            "input": "$zlintErrWarn",
            "as": "lint",
            "cond": {
                "$and": [
                    {"$eq": ["$$lint.v.result", "error"]},
                    {"$in": ["$$lint.k", _CRITICAL_LINT_LIST]},
                ]
            },
        }
    }
}

# Leaf certificate = not self-subject (subject_dn truthy and == issuer_dn) and
# not a CA (basic_constraints.ca == true) — identical to is_leaf_certificate().
LEAF_EXPR = {
    "$and": [
        {
            "$not": {
                "$and": [
                    {"$ne": [{"$ifNull": ["$parsed.subject_dn", ""]}, ""]},
                    {"$eq": ["$parsed.subject_dn", "$parsed.issuer_dn"]},
                ]
            }
        },
        {"$not": {"$eq": ["$parsed.basic_constraints.ca", True]}},
    ]
}


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


def _new_score_entry():
    return {
        "count": 0,
        "score": 0.0,
        "coreHygiene": 0.0,
        "cryptoHealth": 0.0,
        "operationalStability": 0.0,
        "policyCompliance": 0.0,
        "riskFactors": 0.0,
    }


def compute_ca_notebook_scores_all_scopes(source_collection, scope_names, country_scopes, limit=None):
    """Return per-scope (ca_score_map, norm_m, scored_leaf_count) in ONE scan.

    The scan stores a slim column per leaf certificate (scope, penalty,
    critical hits, CA name, key hash and the norm-independent score
    components). The per-scope zlint P95 norms need the full penalty
    population, so scoring is replayed from these in-memory columns afterwards
    — this keeps the scan order (and therefore the KUS key-reuse semantics)
    identical to the legacy per-scope implementation.
    """
    from array import array
    from sys import intern

    limit_stage = [{"$limit": limit}] if limit else []

    log("CA ranking pass 1/2: scanning leaf certificates (all scopes, single scan)")
    pipeline = limit_stage + [
        {"$match": {"is_leaf": True}},
        {"$project": {
            "scope": 1,
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
            "zlintErrWarn": ERR_WARN_LINTS_EXPR,
        }},
        {"$addFields": {"penNC": PENALTY_EXPR, "critHits": CRIT_HITS_EXPR}},
        {"$unset": "zlintErrWarn"},
    ]
    cursor = source_collection.aggregate(pipeline, allowDiskUse=True, batchSize=2000)

    # For a single certificate CADS is always 0.0 (one issuer), IOPS is always
    # 1.0 (single-element sequence) and TSI is always 0.5 (fewer than two
    # timestamps), exactly as in score_certificate_with_notebook_formula.
    operational_stability = mean([0.0, 0.5, 1.0])

    scope_col = []
    ca_col = []
    key_col = []
    pen_col = array("d")
    crit_col = array("i")
    khs_col = array("d")
    wklp_col = array("d")
    policy_col = array("d")
    risk_col = array("d")

    scanned = 0
    for doc in cursor:
        cert = doc.get("parsed", {}) or {}

        doc_scope = doc.get("scope")
        scope_col.append(intern(doc_scope) if isinstance(doc_scope, str) else None)
        pen_col.append(doc.get("penNC", 0.0))
        crit_col.append(doc.get("critHits", 0))

        ca_name = ca_name_from_cert(cert)
        if not ca_name or ca_name == "Unknown":
            # Still counts toward the penalty population / leaf counts, but is
            # never scored (same as the legacy pass 2 skip).
            ca_col.append(None)
            key_col.append(None)
            khs_col.append(0.0)
            wklp_col.append(0.0)
            policy_col.append(0.0)
            risk_col.append(0.0)
        else:
            ca_col.append(intern(ca_name) if isinstance(ca_name, str) else ca_name)
            key_col.append(get_safe(cert, ["subject_key_info", "fingerprint_sha256"]))
            khs_col.append(compute_khs(cert))
            wklp_col.append(compute_wklp(cert))

            ekuvs = compute_ekuvs(cert)
            pics = compute_pics(cert)
            dvas = score_dvas_one(cert)
            ncvs = compute_ncvs(cert)
            policy_col.append(mean([ekuvs, pics, dvas, ncvs]))

            gns = compute_gns(cert)
            accs = compute_accs(cert)
            revps = compute_revps(cert)
            risk_col.append(mean([gns, accs, revps]))

        scanned += 1
        if scanned % 100000 == 0:
            log(f"  pass 1/2 scanned {scanned:,} leaf certificates")

    # Per-scope P95 normalization from the collected penalties.
    penalty_values = {s: [] for s in scope_names}
    all_penalties = penalty_values["all"]
    for i, pen in enumerate(pen_col):
        all_penalties.append(pen)
        row_scope = scope_col[i]
        if row_scope in country_scopes:
            penalty_values[row_scope].append(pen)

    norm_m = {}
    scored_leaf_count = {}
    for s in scope_names:
        values = penalty_values[s]
        scored_leaf_count[s] = len(values)
        norm_m[s] = max(percentile(values, 95), 1.0) if values else 10.0
    penalty_values = None

    log(
        f"CA ranking pass 1/2 done: {scored_leaf_count['all']:,} leaf certificates, "
        f"zlint P95(all)={norm_m['all']:.2f}"
    )

    log("CA ranking pass 2/2: scoring certificates and aggregating by CA (in memory)")
    seen_keys = {s: set() for s in scope_names}
    ca_scores = {s: {} for s in scope_names}
    crit_len = max(1, len(CRITICAL_LINTS))

    processed_scores = 0
    for i, ca_name in enumerate(ca_col):
        if ca_name is None:
            continue

        pen = pen_col[i]
        zhfs = 1.0 - (crit_col[i] / crit_len)
        khs = khs_col[i]
        wklp = wklp_col[i]
        policy_compliance = policy_col[i]
        risk_factors = risk_col[i]
        key_hash = key_col[i]

        doc_scope = scope_col[i]
        buckets = ("all", doc_scope) if doc_scope in country_scopes else ("all",)
        for s in buckets:
            bucket_norm = norm_m[s]
            zcs = max(0.0, 1.0 - min(pen, bucket_norm) / bucket_norm)
            core_hygiene = mean([zcs, zhfs])

            if not key_hash:
                kus = 0.5
            else:
                bucket_seen = seen_keys[s]
                if key_hash in bucket_seen:
                    kus = 0.0
                else:
                    bucket_seen.add(key_hash)
                    kus = 1.0
            crypto_health = mean([khs, kus, wklp])

            final_score = mean([
                core_hygiene,
                crypto_health,
                operational_stability,
                policy_compliance,
                risk_factors,
            ]) * 100.0

            entry = ca_scores[s].setdefault(ca_name, _new_score_entry())
            entry["count"] += 1
            entry["score"] += round(final_score, 2)
            entry["coreHygiene"] += round(core_hygiene * 100, 2)
            entry["cryptoHealth"] += round(crypto_health * 100, 2)
            entry["operationalStability"] += round(operational_stability * 100, 2)
            entry["policyCompliance"] += round(policy_compliance * 100, 2)
            entry["riskFactors"] += round(risk_factors * 100, 2)

        processed_scores += 1
        if processed_scores % 100000 == 0:
            log(f"  pass 2/2 scored {processed_scores:,} certificates")

    log(f"CA ranking pass 2/2 done: scored {processed_scores:,} certificates")

    formatted = {}
    for s in scope_names:
        scope_formatted = {}
        for ca_name, data in ca_scores[s].items():
            count = data["count"]
            scope_formatted[ca_name] = {
                "score": round(data["score"] / count, 2),
                "scoreSampleCount": count,
                "coreHygiene": round(data["coreHygiene"] / count, 2),
                "cryptoHealth": round(data["cryptoHealth"] / count, 2),
                "operationalStability": round(data["operationalStability"] / count, 2),
                "policyCompliance": round(data["policyCompliance"] / count, 2),
                "riskFactors": round(data["riskFactors"] / count, 2),
            }
        formatted[s] = scope_formatted
    return formatted, norm_m, scored_leaf_count


def compute_ca_stats(client, main_db, results_db, scopes, top_limit=50, verify=False, limit=None):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    target_collection = results_db_ref["ca-analysis"]

    scope_names = [scope for scope, _country in scopes]
    country_scopes = set(scope_names) - {"all"}

    start_time = datetime.now(timezone.utc)
    log(f"CA analysis started: {main_db} -> {results_db} scopes={len(scope_names)}")

    # Legacy split collections are cleared so stale data is not mistaken for
    # the current materialized view.
    for collection_name in ["ca-stats", "ca-analytics", "issuer-validation-matrix"]:
        results_db_ref[collection_name].drop()

    log("Counting certificates per scope")
    totals = {"all": source_collection.estimated_document_count()}
    for row in source_collection.aggregate(
        [{"$group": {"_id": "$scope", "n": {"$sum": 1}}}], allowDiskUse=True
    ):
        if row["_id"] in country_scopes:
            totals[row["_id"]] = row["n"]
    if limit:
        totals = {s: min(t, limit) for s, t in totals.items()}

    colors = [
        "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444",
        "#06b6d4", "#14b8a6", "#6366f1", "#ec4899", "#84cc16",
        "#f97316", "#a855f7", "#22c55e", "#0ea5e9", "#d946ef",
        "#eab308", "#6b7280",
    ]

    log("Computing CA counts and validation-level matrix (all scopes)")
    limit_stage = [{"$limit": limit}] if limit else []
    validation_rows = list(source_collection.aggregate(limit_stage + [
        {"$group": {
            "_id": {
                "scope": "$scope",
                "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                "validationLevel": {"$ifNull": ["$parsed.validation_level", "Unknown"]},
            },
            "count": {"$sum": 1},
        }},
    ], allowDiskUse=True))

    validation_by_scope = {s: [] for s in scope_names}
    all_totals = {}
    for row in validation_rows:
        issuer = row["_id"].get("issuer")
        validation_level = row["_id"].get("validationLevel")
        key = (issuer, validation_level)
        all_totals[key] = all_totals.get(key, 0) + row["count"]
        row_scope = row["_id"].get("scope")
        if row_scope in country_scopes:
            validation_by_scope[row_scope].append(
                {"issuer": issuer, "validationLevel": validation_level, "count": row["count"]}
            )
    validation_by_scope["all"] = sorted(
        (
            {"issuer": issuer, "validationLevel": validation_level, "count": count}
            for (issuer, validation_level), count in all_totals.items()
        ),
        key=lambda item: item["count"],
        reverse=True,
    )

    ca_score_maps, zlint_norms, scored_leaf_counts = compute_ca_notebook_scores_all_scopes(
        source_collection,
        scope_names,
        country_scopes,
        limit=limit,
    )
    log(f"CA ranking scores done: {len(ca_score_maps['all']):,} scored CAs (all scope)")

    log("Counting self-signed certificates (all scopes)")
    self_signed_by_scope = {s: 0 for s in scope_names}
    for row in source_collection.aggregate(limit_stage + [
        {"$match": {"parsed.signature.self_signed": True}},
        {"$group": {"_id": "$scope", "n": {"$sum": 1}}},
    ], allowDiskUse=True):
        self_signed_by_scope["all"] += row["n"]
        if row["_id"] in country_scopes:
            self_signed_by_scope[row["_id"]] = row["n"]

    log("Computing unique issuer countries (all scopes)")
    country_rows = list(source_collection.aggregate(limit_stage + [
        {"$unwind": {"path": "$parsed.issuer.country", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": {"scope": "$scope", "country": "$parsed.issuer.country"}}},
    ], allowDiskUse=True))

    unique_countries_by_scope = {s: set() for s in scope_names}
    for row in country_rows:
        country = row["_id"].get("country")
        if country is None:
            continue
        unique_countries_by_scope["all"].add(country)
        row_scope = row["_id"].get("scope")
        if row_scope in country_scopes:
            unique_countries_by_scope[row_scope].add(country)

    log("Building and writing ca-analysis documents per scope")
    for scope in scope_names:
        issuer_map = {}
        for record in validation_by_scope[scope]:
            issuer = record["issuer"]
            if not issuer:
                continue
            validation_level = record["validationLevel"] or "Unknown"
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
        ca_score_map = ca_score_maps[scope]

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

        duration = (datetime.now(timezone.utc) - start_time).total_seconds()
        analysis_document = {
            "_id": scoped_doc_id("ca_analysis", scope),
            "scope": scope,
            "total_cas": len(ca_list),
            "total_certs": totals.get(scope, 0),
            "self_signed_count": self_signed_by_scope.get(scope, 0),
            "unique_countries": len(unique_countries_by_scope[scope]),
            "max_ca_count": max_count,
            "computed_at": datetime.now(timezone.utc),
            "computation_duration_seconds": duration,
            "source_database": main_db,
            "source_collection": "certificates",
            "ranking_formula": notebook_formula_description(),
            "ranking_zlint_norm_p95": zlint_norms[scope],
            "ranking_scored_leaf_count": scored_leaf_counts[scope],

            "ca-list": ca_list,
            "top_limit": top_limit,
        }

        target_collection.replace_one({"scope": scope}, analysis_document, upsert=True)

        if verify:
            stored = target_collection.find_one({"scope": scope})
            if not stored:
                raise RuntimeError("Verification failed: missing ca-analysis document")
            if stored.get("total_cas") != len(ca_list):
                raise RuntimeError("Verification failed: total_cas mismatch")
            if stored.get("total_certs") != totals.get(scope, 0):
                raise RuntimeError("Verification failed: total_certs mismatch")
            if sum(ca["count"] for ca in stored.get("ca-list", [])) != total_with_issuer:
                raise RuntimeError("Verification failed: ca-list total mismatch")

    log("Stored ca-analysis documents")
    create_index_if_missing(target_collection, "scope", name="idx_ca_analysis_scope", background=True)
    create_index_if_missing(target_collection, "computed_at", name="idx_ca_analysis_computed_at", background=True)
    create_index_if_missing(target_collection, "ca-list.rank", name="idx_ca_analysis_ca_rank", background=True)
    create_index_if_missing(target_collection, "ca-list.scoreRank", name="idx_ca_analysis_ca_score_rank", background=True)
    create_index_if_missing(target_collection, "ca-list.score", name="idx_ca_analysis_ca_score", background=True)
    create_index_if_missing(target_collection, "ca-list.name", name="idx_ca_analysis_ca_name", background=True)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"CA analysis finished: {len(scope_names)} scopes, duration={duration:.2f}s")


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
        compute_ca_stats(
            client,
            target["main"],
            target["results"],
            get_scopes_for_entry(target),
            top_limit=args.limit,
            verify=args.verify,
            limit=args.sample_limit,
        )
    client.close()


if __name__ == "__main__":
    main()
