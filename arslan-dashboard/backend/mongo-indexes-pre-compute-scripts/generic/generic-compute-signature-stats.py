#!/usr/bin/env python3
"""
Generic signature and hash pre-compute script.

Writes:
- <results_db>.signature-and-hash

This replaces the old split outputs:
- signature-stats
- hash-trends
- issuer-algorithm-matrix
"""

import argparse
import json
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
from scope_utils import add_scope_match, create_index_if_missing, get_scope_filter, get_scopes_for_entry, normalize_db_entries, scoped_doc_id


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_default_config_path():
    script_dir = os.path.dirname(__file__)
    local = os.path.join(script_dir, "databases.json")
    if os.path.exists(local):
        return local
    parent = os.path.abspath(os.path.join(script_dir, "..", "databases.json"))
    return parent


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


def compute_signature_stats(client, main_db, results_db, months=36, granularity="quarterly", matrix_limit=50, verify=False, scope="all"):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    results_collection = results_db_ref["signature-and-hash"]

    log(f"Signature stats: {main_db} -> {results_db} scope={scope}")

    start_time = datetime.now(timezone.utc)
    scope_filter = get_scope_filter(scope)
    total = source_collection.count_documents(scope_filter)

    # Legacy split collections are cleared so stale data is not mistaken for
    # the current materialized view.
    for collection_name in ["signature-stats", "hash-trends", "issuer-algorithm-matrix"]:
        results_db_ref[collection_name].drop()

    if total == 0:
        empty_doc = {
            "_id": scoped_doc_id("signature_and_hash", scope),
            "scope": scope,
            "algorithmDistribution": [],
            "hashDistribution": [],
            "keySizeDistribution": [],
            "weakHashCount": 0,
            "hashComplianceRate": 0,
            "strengthScore": 0,
            "selfSignedCount": 0,
            "maxEncryptionType": None,
            "totalCertificates": 0,
            "computed_at": datetime.now(timezone.utc),
            "computedAt": datetime.now(timezone.utc).isoformat(),
            "computation_duration_seconds": 0,
            "sourceCollection": f"{main_db}.certificates",
            "documentCount": 0,
            "hash-trends": [],
            "hash_trends_granularity": granularity,
            "hash_trends_months": months,
            "issuer-algo-matrix": [],
            "matrix_limit": matrix_limit,
        }
        results_collection.replace_one({"scope": scope}, empty_doc, upsert=True)
        return

    log("Step 1/7: Computing signature algorithm distribution")
    algo_pipeline = [
        {"$group": {
            "_id": "$parsed.signature_algorithm.name",
            "count": {"$sum": 1}
        }},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    algo_results = list(source_collection.aggregate(add_scope_match(algo_pipeline, scope), allowDiskUse=True))

    algo_colors = {
        "SHA256-RSA": "#3b82f6",
        "SHA384-RSA": "#60a5fa",
        "SHA512-RSA": "#1d4ed8",
        "SHA256-ECDSA": "#10b981",
        "SHA384-ECDSA": "#34d399",
        "SHA512-ECDSA": "#059669",
        "SHA1-RSA": "#f59e0b",
        "MD5-RSA": "#ef4444",
    }

    algorithm_distribution = []
    for item in algo_results:
        name = item.get("_id") or "Unknown"
        count = item["count"]
        algorithm_distribution.append({
            "name": name,
            "count": count,
            "percentage": round((count / total) * 100, 2),
            "color": algo_colors.get(name, "#6b7280"),
        })

    log("Step 2/7: Computing hash algorithm distribution")
    hash_pipeline = [
        {"$project": {"sigAlgo": "$parsed.signature_algorithm.name"}},
        {"$addFields": {
            "hash": {
                "$switch": {
                    "branches": [
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA512|SHA-512", "options": "i"}}, "then": "SHA-512"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA384|SHA-384", "options": "i"}}, "then": "SHA-384"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA256|SHA-256", "options": "i"}}, "then": "SHA-256"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA224|SHA-224", "options": "i"}}, "then": "SHA-224"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA1|SHA-1|withSHA1", "options": "i"}}, "then": "SHA-1"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "MD5", "options": "i"}}, "then": "MD5"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "MD2", "options": "i"}}, "then": "MD2"},
                    ],
                    "default": "$sigAlgo",
                }
            }
        }},
        {"$match": {"hash": {"$ne": None, "$ne": ""}}},
        {"$group": {"_id": "$hash", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]
    hash_results = list(source_collection.aggregate(add_scope_match(hash_pipeline, scope), allowDiskUse=True))

    hash_colors = {
        "SHA-512": "#1d4ed8",
        "SHA-384": "#3b82f6",
        "SHA-256": "#10b981",
        "SHA-224": "#34d399",
        "SHA-1": "#f59e0b",
        "MD5": "#ef4444",
        "MD2": "#dc2626",
    }

    hash_security = {
        "SHA-512": "secure",
        "SHA-384": "secure",
        "SHA-256": "secure",
        "SHA-224": "secure",
        "SHA-1": "deprecated",
        "MD5": "critical",
        "MD2": "critical",
    }

    hash_distribution = []
    weak_hash_count = 0
    compliant_count = 0

    for item in hash_results:
        name = item.get("_id")
        count = item["count"]
        hash_distribution.append({
            "name": name,
            "count": count,
            "percentage": round((count / total) * 100, 2),
            "color": hash_colors.get(name, "#6b7280"),
            "security": hash_security.get(name, "unknown"),
        })

        if name in ["SHA-1", "MD5"]:
            weak_hash_count += count
        if name in ["SHA-256", "SHA-384", "SHA-512"]:
            compliant_count += count

    log("Step 3/7: Computing key size distribution")
    keysize_pipeline = [
        {"$project": {
            "algo": "$parsed.subject_key_info.key_algorithm.name",
            "rsaLen": "$parsed.subject_key_info.rsa_public_key.length",
            "ecLen": "$parsed.subject_key_info.ecdsa_public_key.length",
        }},
        {"$addFields": {"keySize": {"$ifNull": ["$rsaLen", "$ecLen"]}}},
        {"$group": {
            "_id": {"algo": "$algo", "size": "$keySize"},
            "count": {"$sum": 1},
        }},
        {"$match": {"_id.size": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": 10},
    ]
    keysize_results = list(source_collection.aggregate(add_scope_match(keysize_pipeline, scope), allowDiskUse=True))

    keysize_distribution = []
    key_score = 0
    for item in keysize_results:
        algo = item["_id"].get("algo", "Unknown")
        size = item["_id"].get("size", 0)
        count = item["count"]
        name = f"{algo} {size}" if size else algo
        percentage = round((count / total) * 100, 2)

        keysize_distribution.append({
            "name": name,
            "algorithm": algo,
            "size": size,
            "count": count,
            "percentage": percentage,
            "color": "#3b82f6" if algo == "RSA" else "#10b981",
        })

        pct = percentage / 100
        if size >= 4096:
            key_score += 100 * pct
        elif size >= 2048:
            key_score += 80 * pct
        elif size >= 1024:
            key_score += 40 * pct
        elif size >= 256:
            key_score += 90 * pct

    log("Step 4/7: Counting self-signed certificates")
    self_signed_count = source_collection.count_documents(
        {"$and": [{"parsed.signature.self_signed": True}, scope_filter]} if scope_filter else {"parsed.signature.self_signed": True}
    )

    hash_compliance_rate = round((compliant_count / total) * 100, 1) if total > 0 else 0

    hash_score = hash_compliance_rate
    algo_score = 85
    for item in algorithm_distribution:
        if "ECDSA" in item.get("name", ""):
            algo_score += item.get("percentage", 0) * 0.15
    algo_score = min(100, algo_score)

    strength_score = int((key_score * 0.4) + (hash_score * 0.4) + (algo_score * 0.2))
    strength_score = max(0, min(100, strength_score))

    log("Step 5/7: Computing max encryption type")
    enc_type_pipeline = [
        {"$group": {
            "_id": "$parsed.subject_key_info.key_algorithm.name",
            "count": {"$sum": 1},
        }},
        {"$match": {"_id": {"$ne": None}}},
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]
    enc_type_result = list(source_collection.aggregate(add_scope_match(enc_type_pipeline, scope), allowDiskUse=True))

    max_encryption_type = None
    if enc_type_result:
        enc_name = enc_type_result[0]["_id"]
        enc_count = enc_type_result[0]["count"]
        max_encryption_type = {
            "name": enc_name,
            "count": enc_count,
            "percentage": round((enc_count / total) * 100, 2),
        }

    log("Step 6/7: Computing hash trends")
    now = datetime.now(timezone.utc)
    start_date = now - relativedelta(months=months)
    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    if granularity == "yearly":
        period_expr = {"year": {"$year": "$issuedDate"}}
    else:
        period_expr = {
            "year": {"$year": "$issuedDate"},
            "quarter": {"$ceil": {"$divide": [{"$month": "$issuedDate"}, 3]}},
        }

    trends_pipeline = [
        {"$match": {"parsed.validity.start": {"$gte": start_str}}},
        {"$project": {
            "sigAlgo": "$parsed.signature_algorithm.name",
            "issuedDate": {"$dateFromString": {"dateString": "$parsed.validity.start", "onError": None}},
        }},
        {"$match": {"issuedDate": {"$ne": None}}},
        {"$addFields": {
            "hash": {
                "$switch": {
                    "branches": [
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA512|SHA-512", "options": "i"}}, "then": "SHA-512"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA384|SHA-384", "options": "i"}}, "then": "SHA-384"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA256|SHA-256", "options": "i"}}, "then": "SHA-256"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA224|SHA-224", "options": "i"}}, "then": "SHA-224"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "SHA1|SHA-1|withSHA1", "options": "i"}}, "then": "SHA-1"},
                        {"case": {"$regexMatch": {"input": {"$ifNull": ["$sigAlgo", ""]}, "regex": "MD5", "options": "i"}}, "then": "MD5"},
                    ],
                    "default": "Other",
                }
            },
            "period": period_expr,
        }},
        {"$group": {"_id": {"period": "$period", "hash": "$hash"}, "count": {"$sum": 1}}},
        {"$group": {"_id": "$_id.period", "hashes": {"$push": {"hash": "$_id.hash", "count": "$count"}}, "total": {"$sum": "$count"}}},
        {"$sort": {"_id.year": 1, "_id.quarter": 1}},
    ]
    trend_results = list(source_collection.aggregate(add_scope_match(trends_pipeline, scope), allowDiskUse=True))

    hash_trends = []
    for item in trend_results:
        period = item["_id"]
        period_total = item["total"]

        if granularity == "yearly":
            period_label = str(period.get("year", "Unknown"))
        else:
            year = period.get("year", 0)
            quarter = period.get("quarter", 0)
            period_label = f"Q{quarter} {year}"

        hash_pcts = {}
        for h in item.get("hashes", []):
            hash_name = h["hash"]
            hash_pcts[hash_name] = round((h["count"] / period_total) * 100, 1) if period_total else 0

        hash_trends.append({
            "period": period_label,
            "year": period.get("year", 0),
            "quarter": period.get("quarter", 0) if granularity == "quarterly" else None,
            "total": period_total,
            "SHA-256": hash_pcts.get("SHA-256", 0),
            "SHA-384": hash_pcts.get("SHA-384", 0),
            "SHA-512": hash_pcts.get("SHA-512", 0),
            "SHA-1": hash_pcts.get("SHA-1", 0),
            "MD5": hash_pcts.get("MD5", 0),
            "Other": hash_pcts.get("Other", 0),
        })

    log("Step 7/7: Computing issuer algorithm matrix")
    issuer_algo_pipeline = [
        {
            "$project": {
                "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                "algo": "$parsed.subject_key_info.key_algorithm.name",
                "rsaLen": "$parsed.subject_key_info.rsa_public_key.length",
                "ecLen": "$parsed.subject_key_info.ecdsa_public_key.length",
            }
        },
        {"$addFields": {"keySize": {"$ifNull": ["$rsaLen", "$ecLen"]}}},
        {"$match": {"issuer": {"$ne": None}, "algo": {"$ne": None}}},
        {
            "$group": {
                "_id": {"issuer": "$issuer", "algo": "$algo", "keySize": "$keySize"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": matrix_limit},
    ]
    issuer_algo_results = list(source_collection.aggregate(add_scope_match(issuer_algo_pipeline, scope), allowDiskUse=True))

    issuer_matrix_map = {}
    for item in issuer_algo_results:
        issuer = item["_id"].get("issuer", "Unknown")
        algo = item["_id"].get("algo", "Unknown")
        key_size = item["_id"].get("keySize", 0)
        count = item["count"]
        algo_str = f"{algo}-{key_size}" if key_size else algo

        issuer_entry = issuer_matrix_map.setdefault(issuer, {
            "issuer": issuer,
            "algorithm_list": [],
            "issuer_total": 0,
        })
        issuer_entry["issuer_total"] += count
        issuer_entry["algorithm_list"].append({
            "algorithm": algo_str,
            "algorithmType": algo,
            "keySize": key_size,
            "count": count,
            "percentage": round((count / total) * 100, 2) if total > 0 else 0,
        })

    issuer_algo_matrix = sorted(
        issuer_matrix_map.values(),
        key=lambda item: item["issuer_total"],
        reverse=True,
    )
    for issuer_entry in issuer_algo_matrix:
        issuer_entry["algorithm_list"] = sorted(
            issuer_entry["algorithm_list"],
            key=lambda item: item["count"],
            reverse=True,
        )

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    result_doc = {
        "_id": scoped_doc_id("signature_and_hash", scope),
        "scope": scope,
        "algorithmDistribution": algorithm_distribution,
        "hashDistribution": hash_distribution,
        "keySizeDistribution": keysize_distribution,
        "weakHashCount": weak_hash_count,
        "hashComplianceRate": hash_compliance_rate,
        "strengthScore": strength_score,
        "selfSignedCount": self_signed_count,
        "totalCertificates": total,
        "maxEncryptionType": max_encryption_type,
        # "computed_at": datetime.now(timezone.utc),
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "computation_duration_seconds": duration,
        "sourceCollection": f"{main_db}.certificates",
        # "documentCount": total,
        "hash-trends": hash_trends,
        "hash_trends_granularity": granularity,
        "hash_trends_months": months,
        "issuer-algo-matrix": issuer_algo_matrix,
        "matrix_limit": matrix_limit,
    }

    results_collection.replace_one({"scope": scope}, result_doc, upsert=True)
    create_index_if_missing(results_collection, "scope", name="idx_signature_hash_scope", background=True)
    create_index_if_missing(results_collection, "computed_at", name="idx_signature_hash_computed_at", background=True)
    create_index_if_missing(results_collection, "computedAt", name="idx_signature_hash_computedAt", background=True)
    create_index_if_missing(results_collection, "hash_trends_granularity", name="idx_signature_hash_trend_granularity", background=True)
    create_index_if_missing(results_collection, "hash_trends_months", name="idx_signature_hash_trend_months", background=True)
    create_index_if_missing(results_collection, "issuer-algo-matrix.issuer", name="idx_signature_hash_issuer", background=True)

    if verify:
        stored_doc = results_collection.find_one({"scope": scope})
        if not stored_doc:
            raise RuntimeError("Verification failed: missing signature-and-hash document")
        if stored_doc and stored_doc.get("totalCertificates") != total:
            raise RuntimeError("Verification failed: totalCertificates mismatch")
        if stored_doc.get("hash_trends_granularity") != granularity:
            raise RuntimeError("Verification failed: hash trend granularity mismatch")
        flattened_matrix_count = sum(len(item.get("algorithm_list", [])) for item in stored_doc.get("issuer-algo-matrix", []))
        if flattened_matrix_count != len(issuer_algo_results):
            raise RuntimeError("Verification failed: issuer algorithm matrix mismatch")

    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic signature stats pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--months", type=int, default=36, help="Number of months to look back for hash trends")
    parser.add_argument("--granularity", choices=["quarterly", "yearly", "both"], default="quarterly")
    parser.add_argument("--limit", type=int, default=50, help="Max issuer/algorithm combinations to store")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        granularity = "quarterly" if args.granularity == "both" else args.granularity
        for scope, _country in get_scopes_for_entry(target):
            compute_signature_stats(
                client,
                target["main"],
                target["results"],
                months=args.months,
                granularity=granularity,
                matrix_limit=args.limit,
                verify=args.verify,
                scope=scope,
            )
    client.close()


if __name__ == "__main__":
    main()
