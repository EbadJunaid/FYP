#!/usr/bin/env python3
"""
Generic validity analytics pre-compute script.

Writes:
- <results_db>.validity-stats
- <results_db>.validity-distribution
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from pymongo import MongoClient


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
    entries = []
    for item in items:
        if isinstance(item, str):
            entries.append({"main": item, "results": f"{item}-results"})
        elif isinstance(item, dict):
            main_db = item.get("main") or item.get("db") or item.get("name")
            results_db = item.get("results") or (f"{main_db}-results" if main_db else None)
            if main_db:
                entries.append({"main": main_db, "results": results_db})
        else:
            raise ValueError("Unsupported database entry in list")
    return entries


def resolve_targets(db_names, entries):
    if not db_names:
        return entries

    lookup = {entry["main"]: entry for entry in entries}
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            targets.append({"main": name, "results": f"{name}-results"})
    return targets


def safe_count_documents(collection, filter_doc, hint):
    try:
        return collection.count_documents(filter_doc, hint=hint)
    except Exception:
        return collection.count_documents(filter_doc)


def compute_validity_analytics(client, main_db, results_db, verify=False):
    source_collection = client[main_db]["certificates"]
    stats_collection = client[results_db]["validity-stats"]
    distribution_collection = client[results_db]["validity-distribution"]

    log(f"Validity analytics: {main_db} -> {results_db}")
    start_time = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    now_iso = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    plus_30 = (now + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    plus_60 = (now + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%SZ")
    plus_90 = (now + timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")

    log("Step 1/3: Computing validity stats")
    stats_pipeline = [
        {
            "$match": {
                "parsed.validity.length": {"$exists": True, "$gt": 0}
            }
        },
        {
            "$project": {
                "lengthSeconds": "$parsed.validity.length",
                "durationDays": {"$divide": ["$parsed.validity.length", 86400]}
            }
        },
        {
            "$group": {
                "_id": None,
                "avgDuration": {"$avg": "$durationDays"},
                "minDuration": {"$min": "$durationDays"},
                "maxDuration": {"$max": "$durationDays"},
                "total": {"$sum": 1},
                "compliantCount": {
                    "$sum": {
                        "$cond": [
                            {"$lte": ["$durationDays", 398]},
                            1,
                            0
                        ]
                    }
                }
            }
        }
    ]

    stats_result = list(source_collection.aggregate(stats_pipeline, allowDiskUse=True))
    stats = stats_result[0] if stats_result else {}

    total = stats.get("total", 0)
    compliant = stats.get("compliantCount", 0)

    log("Step 2/3: Counting expiring certificates")
    expiring_30 = safe_count_documents(
        source_collection,
        {"parsed.validity.end": {"$gt": now_iso, "$lte": plus_30}},
        hint="idx_validity_end",
    )
    expiring_60 = safe_count_documents(
        source_collection,
        {"parsed.validity.end": {"$gt": now_iso, "$lte": plus_60}},
        hint="idx_validity_end",
    )
    expiring_90 = safe_count_documents(
        source_collection,
        {"parsed.validity.end": {"$gt": now_iso, "$lte": plus_90}},
        hint="idx_validity_end",
    )

    stats_doc = {
        "averageValidityDays": round(stats.get("avgDuration", 0) or 0),
        "shortestValidityDays": round(stats.get("minDuration", 0) or 0),
        "longestValidityDays": round(stats.get("maxDuration", 0) or 0),
        "expiring30Days": expiring_30,
        "expiring60Days": expiring_60,
        "expiring90Days": expiring_90,
        "complianceRate": round((compliant / total * 100), 1) if total > 0 else 0,
        "totalCertificates": total,
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCollection": f"{main_db}.certificates",
        "referenceDate": now_iso,
    }

    stats_collection.delete_many({})
    stats_collection.insert_one(stats_doc)

    log("Step 3/3: Computing validity distribution")
    distribution_pipeline = [
        {
            "$project": {
                "validFrom": "$parsed.validity.start",
                "validTo": "$parsed.validity.end",
            }
        },
        {
            "$addFields": {
                "validFromDate": {
                    "$dateFromString": {"dateString": "$validFrom", "onError": None}
                },
                "validToDate": {
                    "$dateFromString": {"dateString": "$validTo", "onError": None}
                }
            }
        },
        {
            "$addFields": {
                "durationDays": {
                    "$divide": [
                        {"$subtract": ["$validToDate", "$validFromDate"]},
                        86400000
                    ]
                }
            }
        },
        {
            "$match": {"durationDays": {"$ne": None, "$gt": 0}}
        },
        {
            "$bucket": {
                "groupBy": "$durationDays",
                "boundaries": [0, 90, 365, 730, 100000],
                "default": "Other",
                "output": {
                    "count": {"$sum": 1}
                }
            }
        }
    ]

    results = list(source_collection.aggregate(distribution_pipeline, allowDiskUse=True))

    bucket_labels = {
        0: "< 90 Days",
        90: "90 Days - 1 Year",
        365: "1 - 2 Years",
        730: "> 2 Years",
    }

    bucket_colors = {
        0: "#3b82f6",
        90: "#10b981",
        365: "#8b5cf6",
        730: "#f59e0b",
    }

    total_distribution = sum(r.get("count", 0) for r in results)
    distribution = []
    computed_at = datetime.now(timezone.utc).isoformat()

    for result in results:
        bucket_id = result.get("_id")
        if bucket_id in bucket_labels:
            count = result.get("count", 0)
            percentage = round((count / total_distribution * 100), 1) if total_distribution > 0 else 0
            distribution.append({
                "range": bucket_labels[bucket_id],
                "bucketId": bucket_id,
                "count": count,
                "percentage": percentage,
                "color": bucket_colors.get(bucket_id, "#6b7280"),
                "computedAt": computed_at,
                "sourceCollection": f"{main_db}.certificates",
            })

    distribution_collection.delete_many({})
    if distribution:
        distribution_collection.insert_many(distribution)

    if verify:
        stored_stats = stats_collection.count_documents({})
        if stored_stats != 1:
            raise RuntimeError("Verification failed: validity-stats count mismatch")
        stored_doc = stats_collection.find_one({})
        if stored_doc and stored_doc.get("totalCertificates") != total:
            raise RuntimeError("Verification failed: totalCertificates mismatch")
        if distribution:
            stored_dist = distribution_collection.count_documents({})
            if stored_dist != len(distribution):
                raise RuntimeError("Verification failed: validity-distribution count mismatch")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic validity analytics pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_validity_analytics(client, target["main"], target["results"], verify=args.verify)
    client.close()


if __name__ == "__main__":
    main()
