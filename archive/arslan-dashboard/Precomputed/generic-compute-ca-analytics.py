#!/usr/bin/env python3
"""
Generic CA analytics pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.ca-analytics.
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


def compute_ca_analytics(client, main_db, results_db, verify=False):
    source_collection = client[main_db]["certificates"]
    target_collection = client[results_db]["ca-analytics"]

    pipeline = [
        {"$project": {"issuer_org": {"$arrayElemAt": ["$parsed.issuer.organization", 0]}}},
        {"$match": {"issuer_org": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$issuer_org", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]

    start_time = datetime.now(timezone.utc)
    try:
        results = list(source_collection.aggregate(pipeline, hint="idx_issuer_org", allowDiskUse=True))
    except Exception:
        results = list(source_collection.aggregate(pipeline, allowDiskUse=True))

    if not results:
        target_collection.delete_many({})
        metadata = {
            "_id": "metadata",
            "last_computed": datetime.now(timezone.utc),
            "computation_duration_seconds": 0,
            "total_cas": 0,
            "total_certificates": 0,
            "source_database": main_db,
            "source_collection": "certificates",
        }
        target_collection.replace_one({"_id": "metadata"}, metadata, upsert=True)
        return

    total_with_issuer = sum(r["count"] for r in results)
    max_count = results[0]["count"] if results else 1

    colors = [
        "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444",
        "#06b6d4", "#14b8a6", "#6366f1", "#ec4899", "#84cc16",
        "#f97316", "#a855f7", "#22c55e", "#0ea5e9", "#d946ef",
        "#eab308", "#6b7280",
    ]

    ca_records = []
    for i, result in enumerate(results):
        ca_records.append({
            "ca_id": f"ca-{i}",
            "name": result["_id"],
            "count": result["count"],
            "max_count": max_count,
            "percentage": round((result["count"] / total_with_issuer) * 100, 1) if total_with_issuer else 0,
            "color": colors[i % len(colors)],
            "rank": i + 1,
            "computed_at": datetime.now(timezone.utc),
            "total_certificates": total_with_issuer,
        })

    target_collection.delete_many({})
    if ca_records:
        target_collection.insert_many(ca_records)

    target_collection.create_index("rank")
    target_collection.create_index("computed_at")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    metadata = {
        "_id": "metadata",
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": duration,
        "total_cas": len(ca_records),
        "total_certificates": total_with_issuer,
        "source_database": main_db,
        "source_collection": "certificates",
    }
    target_collection.replace_one({"_id": "metadata"}, metadata, upsert=True)

    if verify:
        stored_count = target_collection.count_documents({"_id": {"$ne": "metadata"}})
        if stored_count != len(ca_records):
            raise RuntimeError("Verification failed: record count mismatch")
        if sum(r["count"] for r in ca_records) != total_with_issuer:
            raise RuntimeError("Verification failed: total count mismatch")
        stored_meta = target_collection.find_one({"_id": "metadata"})
        if stored_meta and stored_meta.get("total_certificates") != total_with_issuer:
            raise RuntimeError("Verification failed: metadata total mismatch")


def main():
    # Deprecated entry point: CA analytics, CA stats, and issuer validation
    # matrix are now computed together by generic-compute-ca-stats.py into
    # <results_db>.ca-analysis. Old implementation is kept above for reference.
    import importlib.util

    merged_path = os.path.join(os.path.dirname(__file__), "generic-compute-ca-stats.py")
    spec = importlib.util.spec_from_file_location("generic_compute_ca_stats", merged_path)
    merged = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(merged)
    merged.main()


if __name__ == "__main__":
    main()
