#!/usr/bin/env python3
"""
Generic hash trends pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.hash-trends.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient


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


def compute_hash_trends(source_collection, results_collection, months, granularity):
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

    pipeline = [
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

    results = list(source_collection.aggregate(pipeline, allowDiskUse=True))

    trends = []
    for item in results:
        period = item["_id"]
        total = item["total"]

        if granularity == "yearly":
            period_label = str(period.get("year", "Unknown"))
        else:
            year = period.get("year", 0)
            quarter = period.get("quarter", 0)
            period_label = f"Q{quarter} {year}"

        hash_pcts = {}
        for h in item.get("hashes", []):
            hash_name = h["hash"]
            hash_pcts[hash_name] = round((h["count"] / total) * 100, 1) if total else 0

        trend_doc = {
            "period": period_label,
            "year": period.get("year", 0),
            "quarter": period.get("quarter", 0) if granularity == "quarterly" else None,
            "total": total,
            "SHA-256": hash_pcts.get("SHA-256", 0),
            "SHA-384": hash_pcts.get("SHA-384", 0),
            "SHA-512": hash_pcts.get("SHA-512", 0),
            "SHA-1": hash_pcts.get("SHA-1", 0),
            "MD5": hash_pcts.get("MD5", 0),
            "Other": hash_pcts.get("Other", 0),
            "granularity": granularity,
            "months": months,
            "computedAt": datetime.now(timezone.utc).isoformat(),
        }
        trends.append(trend_doc)

    results_collection.delete_many({"granularity": granularity, "months": months})
    if trends:
        results_collection.insert_many(trends)

    return trends


def main():
    parser = argparse.ArgumentParser(description="Generic hash trends pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--months", type=int, default=36, help="Number of months to look back")
    parser.add_argument("--granularity", choices=["quarterly", "yearly", "both"], default="both")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        source_collection = client[target["main"]]["certificates"]
        results_collection = client[target["results"]]["hash-trends"]

        granularities = ["quarterly", "yearly"] if args.granularity == "both" else [args.granularity]
        for granularity in granularities:
            trends = compute_hash_trends(source_collection, results_collection, args.months, granularity)
            if args.verify:
                stored = list(results_collection.find({"granularity": granularity, "months": args.months}))
                if len(stored) != len(trends):
                    raise RuntimeError("Verification failed: trend count mismatch")

    client.close()


if __name__ == "__main__":
    main()
