#!/usr/bin/env python3
"""
Generic signature and hash pre-compute script.

Writes:
- <results_db>.signature-and-hash

This replaces the old split outputs:
- signature-stats
- hash-trends
- issuer-algorithm-matrix

Optimized: every aggregation groups by the scope field so each metric is
computed for all scopes ("all" + configured countries) in one server pass.
Output documents keep the exact same shape, ids and index names.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
from scope_utils import create_index_if_missing, get_scopes_for_entry, normalize_db_entries, scoped_doc_id


def log(message):
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")


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


def classify_hash_algorithm(signature_algorithm):
    value = signature_algorithm or ""
    normalized = value.upper()
    if "SHA512" in normalized or "SHA-512" in normalized:
        return "SHA-512"
    if "SHA384" in normalized or "SHA-384" in normalized:
        return "SHA-384"
    if "SHA256" in normalized or "SHA-256" in normalized:
        return "SHA-256"
    if "SHA224" in normalized or "SHA-224" in normalized:
        return "SHA-224"
    if "SHA1" in normalized or "SHA-1" in normalized or "WITHSHA1" in normalized:
        return "SHA-1"
    if "MD5" in normalized:
        return "MD5"
    if "MD2" in normalized:
        return "MD2"
    return value or "Unknown"


def run_agg(collection, pipeline, limit=None):
    limited_pipeline = ([{"$limit": limit}] if limit else []) + list(pipeline)
    return list(collection.aggregate(limited_pipeline, allowDiskUse=True))


def split_rows_by_scope(rows, scope_names, country_scopes, merge_key):
    """Split scope-grouped aggregation rows into per-scope row lists.

    ``merge_key`` maps a row's _id (minus scope) to a hashable key used to sum
    rows across scopes for the synthetic "all" scope. Row order within a scope
    preserves the aggregation's sort order (count descending).
    """
    per_scope = {s: [] for s in scope_names}
    all_totals = {}
    all_ids = {}
    for row in rows:
        row_scope = row["_id"].get("scope")
        sub_id = {k: v for k, v in row["_id"].items() if k != "scope"}
        key = merge_key(sub_id)
        if key not in all_totals:
            all_totals[key] = 0
            all_ids[key] = sub_id
        all_totals[key] += row["count"]
        if row_scope in country_scopes:
            per_scope[row_scope].append({"_id": sub_id, "count": row["count"]})

    all_rows = [
        {"_id": all_ids[key], "count": count}
        for key, count in all_totals.items()
    ]
    all_rows.sort(key=lambda item: item["count"], reverse=True)
    per_scope["all"] = all_rows
    return per_scope


def compute_signature_stats(client, main_db, results_db, scopes, months=36, granularity="quarterly", matrix_limit=50, verify=False, limit=None):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    results_collection = results_db_ref["signature-and-hash"]

    scope_names = [scope for scope, _country in scopes]
    country_scopes = set(scope_names) - {"all"}

    log(f"Signature stats: {main_db} -> {results_db} scopes={len(scope_names)}")

    start_time = datetime.now(timezone.utc)

    # Legacy split collections are cleared so stale data is not mistaken for
    # the current materialized view.
    for collection_name in ["signature-stats", "hash-trends", "issuer-algorithm-matrix"]:
        results_db_ref[collection_name].drop()

    log("Step 0/7: Counting certificates per scope")
    totals = {"all": source_collection.estimated_document_count()}
    for row in run_agg(source_collection, [{"$group": {"_id": "$scope", "n": {"$sum": 1}}}], limit=limit):
        if row["_id"] in country_scopes:
            totals[row["_id"]] = row["n"]
    if limit:
        totals = {s: min(t, limit) for s, t in totals.items()}

    log("Step 1/7: Computing signature algorithm distribution (all scopes)")
    algo_rows = run_agg(source_collection, [
        {"$group": {
            "_id": {"scope": "$scope", "name": "$parsed.signature_algorithm.name"},
            "count": {"$sum": 1},
        }},
    ], limit=limit)
    algo_by_scope = split_rows_by_scope(
        algo_rows, scope_names, country_scopes, lambda sub: sub.get("name")
    )

    log("Step 3/7: Computing key size distribution (all scopes)")
    keysize_rows = run_agg(source_collection, [
        {"$group": {
            "_id": {
                "scope": "$scope",
                "algo": "$parsed.subject_key_info.key_algorithm.name",
                "size": {
                    "$ifNull": [
                        "$parsed.subject_key_info.rsa_public_key.length",
                        "$parsed.subject_key_info.ecdsa_public_key.length",
                    ]
                },
            },
            "count": {"$sum": 1},
        }},
    ], limit=limit)
    keysize_by_scope = split_rows_by_scope(
        keysize_rows, scope_names, country_scopes,
        lambda sub: (sub.get("algo"), sub.get("size")),
    )

    log("Step 4/7: Counting self-signed certificates (all scopes)")
    self_signed_rows = run_agg(source_collection, [
        {"$match": {"parsed.signature.self_signed": True}},
        {"$group": {"_id": "$scope", "n": {"$sum": 1}}},
    ], limit=limit)
    self_signed_by_scope = {s: 0 for s in scope_names}
    for row in self_signed_rows:
        self_signed_by_scope["all"] += row["n"]
        if row["_id"] in country_scopes:
            self_signed_by_scope[row["_id"]] = row["n"]

    log("Step 6/7: Computing hash trends (all scopes)")
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
            "scope": 1,
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
        {"$group": {"_id": {"scope": "$scope", "period": "$period", "hash": "$hash"}, "count": {"$sum": 1}}},
    ]
    trend_rows = run_agg(source_collection, trends_pipeline, limit=limit)

    # trend_data[scope][(year, quarter)] = {"total": n, "hashes": {hash: n}}
    trend_data = {s: {} for s in scope_names}

    def add_trend(scope, period, hash_name, count):
        period_key = (period.get("year", 0), period.get("quarter", 0))
        entry = trend_data[scope].setdefault(period_key, {"period": period, "total": 0, "hashes": {}})
        entry["total"] += count
        entry["hashes"][hash_name] = entry["hashes"].get(hash_name, 0) + count

    for row in trend_rows:
        period = row["_id"]["period"]
        hash_name = row["_id"]["hash"]
        add_trend("all", period, hash_name, row["count"])
        row_scope = row["_id"].get("scope")
        if row_scope in country_scopes:
            add_trend(row_scope, period, hash_name, row["count"])

    log("Step 7/7: Computing issuer algorithm matrix (all scopes)")
    issuer_algo_rows = run_agg(source_collection, [
        {"$group": {
            "_id": {
                "scope": "$scope",
                "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                "algo": "$parsed.subject_key_info.key_algorithm.name",
                "keySize": {
                    "$ifNull": [
                        "$parsed.subject_key_info.rsa_public_key.length",
                        "$parsed.subject_key_info.ecdsa_public_key.length",
                    ]
                },
            },
            "count": {"$sum": 1},
        }},
    ], limit=limit)
    issuer_algo_by_scope = split_rows_by_scope(
        issuer_algo_rows, scope_names, country_scopes,
        lambda sub: (sub.get("issuer"), sub.get("algo"), sub.get("keySize")),
    )

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

    log("Building and writing signature-and-hash documents per scope")
    for scope in scope_names:
        total = totals.get(scope, 0)

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
            continue

        # Signature algorithm distribution
        algorithm_distribution = []
        valid_algo_results = sorted(
            [item for item in algo_by_scope[scope] if item["_id"].get("name")],
            key=lambda item: item["count"],
            reverse=True,
        )
        for item in valid_algo_results[:10]:
            name = item["_id"]["name"]
            count = item["count"]
            algorithm_distribution.append({
                "name": name,
                "count": count,
                "percentage": round((count / total) * 100, 2),
                "color": algo_colors.get(name, "#6b7280"),
            })

        # Hash algorithm distribution
        hash_counts = {}
        for item in valid_algo_results:
            hash_name = classify_hash_algorithm(item["_id"]["name"])
            hash_counts[hash_name] = hash_counts.get(hash_name, 0) + item["count"]
        hash_results = [
            {"_id": name, "count": count}
            for name, count in sorted(hash_counts.items(), key=lambda entry: entry[1], reverse=True)
        ]

        hash_distribution = []
        weak_hash_count = 0
        compliant_count = 0
        for item in hash_results:
            name = item["_id"]
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

        # Key size distribution
        keysize_distribution = []
        key_score = 0
        encryption_type_counts = {}
        valid_keysize_results = sorted(
            [
                item for item in keysize_by_scope[scope]
                if item["_id"].get("algo") and item["_id"].get("size")
            ],
            key=lambda item: item["count"],
            reverse=True,
        )
        for item in valid_keysize_results:
            algo = item["_id"].get("algo", "Unknown")
            count = item["count"]
            encryption_type_counts[algo] = encryption_type_counts.get(algo, 0) + count

        for item in valid_keysize_results[:10]:
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

        self_signed_count = self_signed_by_scope.get(scope, 0)

        hash_compliance_rate = round((compliant_count / total) * 100, 1) if total > 0 else 0

        hash_score = hash_compliance_rate
        algo_score = 85
        for item in algorithm_distribution:
            if "ECDSA" in item.get("name", ""):
                algo_score += item.get("percentage", 0) * 0.15
        algo_score = min(100, algo_score)

        strength_score = int((key_score * 0.4) + (hash_score * 0.4) + (algo_score * 0.2))
        strength_score = max(0, min(100, strength_score))

        max_encryption_type = None
        if encryption_type_counts:
            enc_name, enc_count = max(encryption_type_counts.items(), key=lambda entry: entry[1])
            max_encryption_type = {
                "name": enc_name,
                "count": enc_count,
                "percentage": round((enc_count / total) * 100, 2),
            }

        # Hash trends
        hash_trends = []
        for period_key in sorted(trend_data[scope].keys()):
            entry = trend_data[scope][period_key]
            period = entry["period"]
            period_total = entry["total"]

            if granularity == "yearly":
                period_label = str(period.get("year", "Unknown"))
            else:
                year = period.get("year", 0)
                quarter = period.get("quarter", 0)
                period_label = f"Q{quarter} {year}"

            hash_pcts = {}
            for hash_name, count in entry["hashes"].items():
                hash_pcts[hash_name] = round((count / period_total) * 100, 1) if period_total else 0

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

        # Issuer algorithm matrix
        issuer_matrix_map = {}
        valid_issuer_algo_results = sorted(
            [
                item for item in issuer_algo_by_scope[scope]
                if item["_id"].get("issuer") and item["_id"].get("algo")
            ],
            key=lambda item: item["count"],
            reverse=True,
        )[:matrix_limit]
        for item in valid_issuer_algo_results:
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

        if verify:
            stored_doc = results_collection.find_one({"scope": scope})
            if not stored_doc:
                raise RuntimeError("Verification failed: missing signature-and-hash document")
            if stored_doc and stored_doc.get("totalCertificates") != total:
                raise RuntimeError("Verification failed: totalCertificates mismatch")
            if stored_doc.get("hash_trends_granularity") != granularity:
                raise RuntimeError("Verification failed: hash trend granularity mismatch")
            flattened_matrix_count = sum(len(item.get("algorithm_list", [])) for item in stored_doc.get("issuer-algo-matrix", []))
            if flattened_matrix_count != len(valid_issuer_algo_results):
                raise RuntimeError("Verification failed: issuer algorithm matrix mismatch")

    create_index_if_missing(results_collection, "scope", name="idx_signature_hash_scope", background=True)
    create_index_if_missing(results_collection, "computed_at", name="idx_signature_hash_computed_at", background=True)
    create_index_if_missing(results_collection, "computedAt", name="idx_signature_hash_computedAt", background=True)
    create_index_if_missing(results_collection, "hash_trends_granularity", name="idx_signature_hash_trend_granularity", background=True)
    create_index_if_missing(results_collection, "hash_trends_months", name="idx_signature_hash_trend_months", background=True)
    create_index_if_missing(results_collection, "issuer-algo-matrix.issuer", name="idx_signature_hash_issuer", background=True)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic signature stats pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--months", type=int, default=36, help="Number of months to look back for hash trends")
    parser.add_argument("--granularity", choices=["quarterly", "yearly", "both"], default="quarterly")
    parser.add_argument("--limit", type=int, default=50, help="Max issuer/algorithm combinations to store")
    parser.add_argument("--sample-limit", type=int, default=None, help="Limit source documents for fast testing only")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        granularity = "quarterly" if args.granularity == "both" else args.granularity
        compute_signature_stats(
            client,
            target["main"],
            target["results"],
            get_scopes_for_entry(target),
            months=args.months,
            granularity=granularity,
            matrix_limit=args.limit,
            verify=args.verify,
            limit=args.sample_limit,
        )
    client.close()


if __name__ == "__main__":
    main()
