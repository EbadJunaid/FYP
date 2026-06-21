#!/usr/bin/env python3
"""
Generic issuer validation matrix pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.issuer-validation-matrix.
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


def compute_issuer_validation_matrix(client, main_db, results_db, top_limit, verify=False):
    if top_limit < 1:
        raise ValueError("limit must be >= 1")

    source_collection = client[main_db]["certificates"]
    target_collection = client[results_db]["issuer-validation-matrix"]

    start_time = datetime.now(timezone.utc)

    pipeline = [
        {
            "$project": {
                "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                "validationLevel": {"$ifNull": ["$parsed.validation_level", "Unknown"]},
            }
        },
        {"$match": {"issuer": {"$exists": True, "$ne": None}}},
        {
            "$group": {
                "_id": {"issuer": "$issuer", "validationLevel": "$validationLevel"},
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    try:
        results = list(source_collection.aggregate(
            pipeline,
            hint="idx_issuer_org",
            allowDiskUse=True,
        ))
    except Exception:
        results = list(source_collection.aggregate(pipeline, allowDiskUse=True))

    issuer_totals = {}
    for record in results:
        issuer = record["_id"]["issuer"]
        issuer_totals[issuer] = issuer_totals.get(issuer, 0) + record["count"]

    top_issuers = sorted(issuer_totals.items(), key=lambda x: x[1], reverse=True)[:top_limit]
    top_issuer_names = {issuer for issuer, _ in top_issuers}

    matrix_records = []
    for i, record in enumerate(results):
        issuer = record["_id"]["issuer"]
        if issuer in top_issuer_names:
            matrix_records.append({
                "record_id": f"matrix-{i}",
                "issuer": issuer,
                "validationLevel": record["_id"]["validationLevel"],
                "count": record["count"],
                "issuer_total": issuer_totals[issuer],
                "computed_at": datetime.now(timezone.utc),
            })

    target_collection.delete_many({})
    if matrix_records:
        target_collection.insert_many(matrix_records)

    target_collection.create_index("issuer")
    target_collection.create_index("issuer_total")
    target_collection.create_index("computed_at")
    target_collection.create_index([("issuer_total", -1), ("count", -1)])

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    metadata = {
        "_id": "metadata",
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": duration,
        "total_combinations": len(matrix_records),
        "total_issuers": len(top_issuer_names),
        "source_database": main_db,
        "source_collection": "certificates",
    }
    target_collection.replace_one({"_id": "metadata"}, metadata, upsert=True)

    if verify:
        stored_count = target_collection.count_documents({"_id": {"$ne": "metadata"}})
        if stored_count != len(matrix_records):
            raise RuntimeError("Verification failed: matrix record count mismatch")
        stored_meta = target_collection.find_one({"_id": "metadata"})
        if stored_meta and stored_meta.get("total_combinations") != len(matrix_records):
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
