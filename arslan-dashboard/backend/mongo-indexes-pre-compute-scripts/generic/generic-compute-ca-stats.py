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


def compute_ca_stats(client, main_db, results_db, top_limit=50, verify=False):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    target_collection = results_db_ref["ca-analysis"]

    start_time = datetime.now(timezone.utc)

    # Legacy split collections are cleared so stale data is not mistaken for
    # the current materialized view.
    for collection_name in ["ca-stats", "ca-analytics", "issuer-validation-matrix"]:
        results_db_ref[collection_name].drop()

    total_certs = source_collection.estimated_document_count()

    colors = [
        "#10b981", "#3b82f6", "#8b5cf6", "#f59e0b", "#ef4444",
        "#06b6d4", "#14b8a6", "#6366f1", "#ec4899", "#84cc16",
        "#f97316", "#a855f7", "#22c55e", "#0ea5e9", "#d946ef",
        "#eab308", "#6b7280",
    ]

    ca_validation_pipeline = [
        {
            "$project": {
                "issuer": {"$arrayElemAt": ["$parsed.issuer.organization", 0]},
                "validationLevel": {"$ifNull": ["$parsed.validation_level", "Unknown"]},
            }
        },
        {"$match": {"issuer": {"$exists": True, "$ne": None}}},
        {
            "$group": {
                "_id": {
                    "issuer": "$issuer",
                    "validationLevel": "$validationLevel",
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"count": -1}},
    ]

    try:
        validation_results = list(source_collection.aggregate(
            ca_validation_pipeline,
            hint="idx_issuer_org",
            allowDiskUse=True,
        ))
    except Exception:
        validation_results = list(source_collection.aggregate(
            ca_validation_pipeline,
            allowDiskUse=True,
        ))

    issuer_map = {}
    for record in validation_results:
        issuer = record["_id"]["issuer"]
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

    ca_list = []
    for index, record in enumerate(ca_records):
        ca_list.append({
            "ca_id": f"ca-{index}",
            "name": record["name"],
            "count": record["count"],
            "percentage": round((record["count"] / total_with_issuer) * 100, 1) if total_with_issuer else 0,
            "color": colors[index % len(colors)],
            "rank": index + 1,
            "validationLevel": sorted(
                record["validationLevel"],
                key=lambda item: item["count"],
                reverse=True,
            ),
        })

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

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    analysis_document = {
        "_id": "ca_analysis",
        "scope": "all",
        "total_cas": len(ca_list),
        "total_certs": total_certs,
        "self_signed_count": self_signed_count,
        "unique_countries": unique_countries,
        "max_ca_count": max_count,
        "computed_at": datetime.now(timezone.utc),
        "computation_duration_seconds": duration,
        "source_database": main_db,
        "source_collection": "certificates",

        "ca-list": ca_list,
        "top_limit": top_limit,
    }

    target_collection.replace_one({"_id": "ca_analysis"}, analysis_document, upsert=True)
    target_collection.create_index("scope")
    target_collection.create_index("computed_at")
    target_collection.create_index("ca-list.rank")

    if verify:
        stored = target_collection.find_one({"_id": "ca_analysis"})
        if not stored:
            raise RuntimeError("Verification failed: missing ca-analysis document")
        if stored.get("total_cas") != len(ca_list):
            raise RuntimeError("Verification failed: total_cas mismatch")
        if stored.get("total_certs") != total_certs:
            raise RuntimeError("Verification failed: total_certs mismatch")
        if sum(ca["count"] for ca in stored.get("ca-list", [])) != total_with_issuer:
            raise RuntimeError("Verification failed: ca-list total mismatch")


def main():
    parser = argparse.ArgumentParser(description="Generic CA stats pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--limit", type=int, default=50, help="Top issuers expected by old matrix script; full CA list is still stored")
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
            top_limit=args.limit,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
