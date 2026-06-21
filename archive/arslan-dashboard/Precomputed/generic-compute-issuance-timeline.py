#!/usr/bin/env python3
"""
Generic issuance timeline pre-compute script.

Reads databases.json unless --dbs is provided, and writes to <results_db>.issuance-timeline.
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
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


def compute_issuance_timeline(client, main_db, results_db, months, verify=False):
    if months < 1:
        raise ValueError("months must be >= 1")

    source_collection = client[main_db]["certificates"]
    results_collection = client[results_db]["issuance-timeline"]

    now = datetime.now(timezone.utc)
    end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)
    start_date = now.replace(day=1) - relativedelta(months=months - 1)

    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    issued_pipeline = [
        {
            "$match": {
                "parsed.validity.start": {
                    "$gte": start_str,
                    "$lte": end_str,
                }
            }
        },
        {"$project": {"validFrom": "$parsed.validity.start"}},
        {
            "$addFields": {
                "validFromDate": {
                    "$dateFromString": {"dateString": "$validFrom", "onError": None}
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$validFromDate"},
                    "month": {"$month": "$validFromDate"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]

    expiring_pipeline = [
        {
            "$match": {
                "parsed.validity.end": {
                    "$gte": start_str,
                    "$lte": end_str,
                }
            }
        },
        {"$project": {"validTo": "$parsed.validity.end"}},
        {
            "$addFields": {
                "validToDate": {
                    "$dateFromString": {"dateString": "$validTo", "onError": None}
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "year": {"$year": "$validToDate"},
                    "month": {"$month": "$validToDate"},
                },
                "count": {"$sum": 1},
            }
        },
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]

    issued_results = list(source_collection.aggregate(issued_pipeline, allowDiskUse=True))
    expiring_results = list(source_collection.aggregate(expiring_pipeline, allowDiskUse=True))

    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    issued_lookup = {
        f"{r['_id']['year']}-{r['_id']['month']}": r["count"] for r in issued_results
    }
    expiring_lookup = {
        f"{r['_id']['year']}-{r['_id']['month']}": r["count"] for r in expiring_results
    }

    timeline = []
    current = start_date.replace(day=1)
    end_month = end_date.replace(day=1)
    computed_at = datetime.now(timezone.utc).isoformat()

    while current <= end_month:
        key = f"{current.year}-{current.month}"
        month_label = f"{month_names[current.month - 1]} '{str(current.year)[2:]}"

        issued_count = issued_lookup.get(key, 0)
        expiring_count = expiring_lookup.get(key, 0)

        timeline.append({
            "month": month_label,
            "year": current.year,
            "monthNum": current.month,
            "issued": issued_count,
            "expiring": expiring_count,
            "months": months,
            "computedAt": computed_at,
            "sourceCollection": f"{main_db}.certificates",
        })

        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    results_collection.delete_many({"months": months})
    if timeline:
        results_collection.insert_many(timeline)

    if verify:
        stored_count = results_collection.count_documents({"months": months})
        if stored_count != len(timeline):
            raise RuntimeError("Verification failed: timeline count mismatch")


def main():
    parser = argparse.ArgumentParser(description="Generic issuance timeline pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--months", type=int, default=12, help="Number of months to compute")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_issuance_timeline(
            client,
            target["main"],
            target["results"],
            months=args.months,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
