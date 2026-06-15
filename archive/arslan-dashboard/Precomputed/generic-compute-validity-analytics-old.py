#!/usr/bin/env python3
"""
Generic validity analytics pre-compute script.

Writes:
- <results_db>.validity-stats
- <results_db>.validity-distribution
- <results_db>.issuance-timeline
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
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


def compute_issuance_timeline(client, main_db, results_db, months=12, verify=False):
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


def compute_validity_analytics(client, main_db, results_db, months=12, verify=False):
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

    # Prepare to collect sample certificate IDs per distribution bucket (max 1000 each)
    bucket_keys = [0, 90, 365, 730]
    bucket_label_map = {
        0: "< 90 Days",
        90: "90 Days - 1 Year",
        365: "1 - 2 Years",
        730: "> 2 Years",
    }
    bucket_sample_ids = {k: [] for k in bucket_keys}

    # Cursor to iterate certificates and gather sample IDs for buckets
    sample_cursor = source_collection.find(
        {
            "parsed.validity.start": {"$exists": True},
            "parsed.validity.end": {"$exists": True},
        },
        {"_id": 1, "parsed.validity.start": 1, "parsed.validity.end": 1},
    ).batch_size(10000)

    from datetime import datetime as _dt

    for doc in sample_cursor:
        try:
            start_str_doc = doc.get("parsed", {}).get("validity", {}).get("start")
            end_str_doc = doc.get("parsed", {}).get("validity", {}).get("end")
            if not start_str_doc or not end_str_doc:
                continue
            start_dt = _dt.strptime(start_str_doc, "%Y-%m-%dT%H:%M:%SZ")
            end_dt = _dt.strptime(end_str_doc, "%Y-%m-%dT%H:%M:%SZ")
            duration_days = int((end_dt - start_dt).total_seconds() / 86400)
        except Exception:
            continue

        if duration_days < 90:
            key = 0
        elif duration_days <= 365:
            key = 90
        elif duration_days <= 730:
            key = 365
        else:
            key = 730

        if len(bucket_sample_ids[key]) < 1000:
            bucket_sample_ids[key].append(doc["_id"])

        # early exit if all buckets have 1000 samples
        if all(len(lst) >= 1000 for lst in bucket_sample_ids.values()):
            break

    # Build validity-distribution entries with certificate_ids and has_more
    validity_distribution = []
    # Map the earlier aggregation results (distribution) into our bucket order
    for bucket_id in bucket_keys:
        # find matching aggregation result for this bucket
        matching = next((r for r in results if r.get("_id") == bucket_id), None)
        count = matching.get("count", 0) if matching else 0
        sample_ids = bucket_sample_ids.get(bucket_id, [])
        validity_distribution.append({
            "bucket_id": bucket_id,
            "label": bucket_label_map.get(bucket_id, str(bucket_id)),
            "count": count,
            "certificate_ids": sample_ids,
            "has_more": count > len(sample_ids),
        })

    # Build issuance timeline sample IDs (issued and expiring) per month
    # We will collect up to 1000 sample _id per month for issued and expiring
    issued_ids_map = {}
    expiring_ids_map = {}
    # initialize maps for range
    current = (datetime.now(timezone.utc).replace(day=1) - relativedelta(months=months - 1)).replace(day=1)
    end_month = (datetime.now(timezone.utc).replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)).replace(day=1)
    while current <= end_month:
        key = f"{current.year}-{current.month}"
        issued_ids_map[key] = []
        expiring_ids_map[key] = []
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # Collect issued sample IDs
    issued_cursor = source_collection.find(
        {"parsed.validity.start": {"$exists": True, "$ne": None}},
        {"_id": 1, "parsed.validity.start": 1},
    ).batch_size(10000)

    for doc in issued_cursor:
        try:
            s = doc.get("parsed", {}).get("validity", {}).get("start")
            if not s:
                continue
            dt = _dt.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            key = f"{dt.year}-{dt.month}"
        except Exception:
            continue
        if key in issued_ids_map and len(issued_ids_map[key]) < 1000:
            issued_ids_map[key].append(doc["_id"])

    # Collect expiring sample IDs
    expiring_cursor = source_collection.find(
        {"parsed.validity.end": {"$exists": True, "$ne": None}},
        {"_id": 1, "parsed.validity.end": 1},
    ).batch_size(10000)

    for doc in expiring_cursor:
        try:
            s = doc.get("parsed", {}).get("validity", {}).get("end")
            if not s:
                continue
            dt = _dt.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            key = f"{dt.year}-{dt.month}"
        except Exception:
            continue
        if key in expiring_ids_map and len(expiring_ids_map[key]) < 1000:
            expiring_ids_map[key].append(doc["_id"])

    # Build issuance timeline entries similar to previous timeline but without repeating computedAt per month
    month_names = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]
    timeline_entries = []
    current = (datetime.now(timezone.utc).replace(day=1) - relativedelta(months=months - 1)).replace(day=1)
    end_month = (datetime.now(timezone.utc).replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)).replace(day=1)
    while current <= end_month:
        key = f"{current.year}-{current.month}"
        month_label = f"{month_names[current.month - 1]} '{str(current.year)[2:]}"
        issued_count = issued_lookup.get(key, 0)
        expiring_count = expiring_lookup.get(key, 0)
        issued_sample = issued_ids_map.get(key, [])
        expiring_sample = expiring_ids_map.get(key, [])
        timeline_entries.append({
            "month": month_label,
            "year": current.year,
            "monthNum": current.month,
            "issued": issued_count,
            "expiring": expiring_count,
            "issued_certificate_ids": issued_sample,
            "issued_has_more": issued_count > len(issued_sample),
            "expiring_certificate_ids": expiring_sample,
            "expiring_has_more": expiring_count > len(expiring_sample),
            "months": months,
            "sourceCollection": f"{main_db}.certificates",
        })
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # Build final validity-analysis document
    validity_analysis_doc = {
        "_id": "validity_analysis",
        "scope": "all",
        "averageValidityDays": round(stats.get("avgDuration", 0) or 0),
        "shortestValidityDays": round(stats.get("minDuration", 0) or 0),
        "longestValidityDays": round(stats.get("maxDuration", 0) or 0),
        "complianceRate": round((compliant / total * 100), 1) if total > 0 else 0,
        "totalCertificates": total,
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCollection": f"{main_db}.certificates",
        "validity_distribution": validity_distribution,
        "issuance_timeline": timeline_entries,
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        "testing_mode": bool(months != 12),
    }

    # Write single combined document
    target_collection = client[results_db]["validity-analysis"]
    target_collection.replace_one({"_id": "validity_analysis"}, validity_analysis_doc, upsert=True)

    # Optional verification
    if verify:
        stored_doc = target_collection.find_one({"_id": "validity_analysis"})
        if not stored_doc:
            raise RuntimeError("Verification failed: validity-analysis document missing")
        if stored_doc.get("totalCertificates") != total:
            raise RuntimeError("Verification failed: totalCertificates mismatch")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic validity analytics pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--months", type=int, default=12, help="Months to compute for issuance timeline")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_validity_analytics(
            client,
            target["main"],
            target["results"],
            months=args.months,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
