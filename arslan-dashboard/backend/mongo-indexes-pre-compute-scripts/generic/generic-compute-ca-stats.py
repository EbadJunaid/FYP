#!/usr/bin/env python3
"""
Generic CA stats pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.ca-stats.
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


def compute_ca_stats(client, main_db, results_db, verify=False):
    source_collection = client[main_db]["certificates"]
    target_collection = client[results_db]["ca-stats"]

    total_certs = source_collection.estimated_document_count()

    ca_pipeline = [
        {"$unwind": {"path": "$parsed.issuer.organization", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$parsed.issuer.organization"}},
        {"$count": "total"},
    ]
    try:
        ca_result = list(source_collection.aggregate(ca_pipeline, hint="idx_issuer_org", allowDiskUse=True))
    except Exception:
        ca_result = list(source_collection.aggregate(ca_pipeline, allowDiskUse=True))
    total_cas = ca_result[0]["total"] if ca_result else 0

    top_ca_pipeline = [
        {"$unwind": {"path": "$parsed.issuer.organization", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$parsed.issuer.organization", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 1},
    ]
    try:
        top_ca_result = list(source_collection.aggregate(top_ca_pipeline, hint="idx_issuer_org", allowDiskUse=True))
    except Exception:
        top_ca_result = list(source_collection.aggregate(top_ca_pipeline, allowDiskUse=True))

    top_ca = None
    top_ca_count = 0
    top_ca_percentage = 0
    if top_ca_result:
        top_ca = top_ca_result[0]["_id"] or "Unknown"
        top_ca_count = top_ca_result[0]["count"]
        top_ca_percentage = round((top_ca_count / total_certs) * 100, 1) if total_certs else 0

    try:
        self_signed_count = source_collection.count_documents(
            {"parsed.signature.self_signed": True},
            hint="idx_self_signed",
        )
    except Exception:
        self_signed_count = source_collection.count_documents({"parsed.signature.self_signed": True})

    country_pipeline = [
        {"$unwind": {"path": "$parsed.issuer.country", "preserveNullAndEmptyArrays": True}},
        {"$group": {"_id": "$parsed.issuer.country"}},
        {"$match": {"_id": {"$ne": None}}},
        {"$count": "total"},
    ]
    try:
        country_result = list(source_collection.aggregate(
            country_pipeline,
            hint="idx_issuer_country",
            allowDiskUse=True,
        ))
    except Exception:
        country_result = list(source_collection.aggregate(country_pipeline, allowDiskUse=True))
    unique_countries = country_result[0]["total"] if country_result else 0

    stats_document = {
        "_id": "ca_stats",
        "total_cas": total_cas,
        "total_certs": total_certs,
        "top_ca": {
            "name": top_ca,
            "count": top_ca_count,
            "percentage": top_ca_percentage,
        },
        "self_signed_count": self_signed_count,
        "unique_countries": unique_countries,
        "computed_at": datetime.now(timezone.utc),
        "computation_duration_seconds": 0,
    }

    target_collection.replace_one({"_id": "ca_stats"}, stats_document, upsert=True)

    if verify:
        stored = target_collection.find_one({"_id": "ca_stats"})
        if not stored:
            raise RuntimeError("Verification failed: missing stats document")
        if stored.get("total_cas") != total_cas:
            raise RuntimeError("Verification failed: total_cas mismatch")
        if stored.get("total_certs") != total_certs:
            raise RuntimeError("Verification failed: total_certs mismatch")


def main():
    parser = argparse.ArgumentParser(description="Generic CA stats pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_ca_stats(client, target["main"], target["results"], verify=args.verify)
    client.close()


if __name__ == "__main__":
    main()
