#!/usr/bin/env python3
"""
Generic issuer algorithm matrix pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.issuer-algorithm-matrix.
"""

import argparse
import json
import os
from datetime import datetime, timezone
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


def compute_issuer_algorithm_matrix(client, main_db, results_db, limit, verify=False):
    if limit < 1:
        raise ValueError("limit must be >= 1")

    source_collection = client[main_db]["certificates"]
    results_collection = client[results_db]["issuer-algorithm-matrix"]

    total = source_collection.count_documents({})

    pipeline = [
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
        {"$limit": limit},
    ]

    results = list(source_collection.aggregate(pipeline, allowDiskUse=True))

    matrix = []
    for item in results:
        issuer = item["_id"].get("issuer", "Unknown")
        algo = item["_id"].get("algo", "Unknown")
        key_size = item["_id"].get("keySize", 0)
        count = item["count"]

        algo_str = f"{algo}-{key_size}" if key_size else algo

        matrix.append({
            "issuer": issuer,
            "algorithm": algo_str,
            "algorithmType": algo,
            "keySize": key_size,
            "count": count,
            "percentage": round((count / total) * 100, 2) if total > 0 else 0,
            "computedAt": datetime.now(timezone.utc).isoformat(),
            "sourceCollection": f"{main_db}.certificates",
        })

    results_collection.delete_many({})
    if matrix:
        results_collection.insert_many(matrix)

    if verify:
        stored_count = results_collection.count_documents({})
        if stored_count != len(matrix):
            raise RuntimeError("Verification failed: matrix count mismatch")
        if total > 0 and sum(doc["count"] for doc in matrix) > total:
            raise RuntimeError("Verification failed: count exceeds total")


def main():
    parser = argparse.ArgumentParser(description="Generic issuer algorithm matrix pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--limit", type=int, default=50, help="Max combinations to store")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_issuer_algorithm_matrix(
            client,
            target["main"],
            target["results"],
            limit=args.limit,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
