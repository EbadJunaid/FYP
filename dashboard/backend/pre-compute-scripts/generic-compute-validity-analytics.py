#!/usr/bin/env python3
"""
Generic validity analytics pre-compute script.

Writes one document to:
- <results_db>.validity-analysis
"""

import argparse
import json
import os
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
from scope_utils import add_scope_match, create_index_if_missing, get_scope_filter, get_scopes_for_entry, merge_scope_query, normalize_db_entries, scoped_doc_id


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


def aggregate_scoped(collection, pipeline, scope, hint=None):
    scoped_pipeline = add_scope_match(pipeline, scope)
    if hint:
        try:
            return list(collection.aggregate(scoped_pipeline, hint=hint, allowDiskUse=True))
        except Exception:
            pass
    return list(collection.aggregate(scoped_pipeline, allowDiskUse=True))


def compute_validity_analytics(client, main_db, results_db, months=12, verify=False, scope="all"):
    from datetime import datetime as _dt
    
    source_collection = client[main_db]["certificates"]
    target_collection = client[results_db]["validity-analysis"]

    log(f"Validity analytics: {main_db} -> {results_db} scope={scope}")
    start_time = datetime.now(timezone.utc)
    scope_filter = get_scope_filter(scope)
    scoped = bool(scope_filter)

    # Step 1: Compute validity stats
    log("Step 1/4: Computing validity stats")
    stats_pipeline = [
        {"$match": {"parsed.validity.length": {"$exists": True, "$gt": 0}}},
        {
            "$group": {
                "_id": None,
                "avgDuration": {"$avg": {"$divide": ["$parsed.validity.length", 86400]}},
                "minDuration": {"$min": {"$divide": ["$parsed.validity.length", 86400]}},
                "maxDuration": {"$max": {"$divide": ["$parsed.validity.length", 86400]}},
                "total": {"$sum": 1},
                "compliantCount": {
                    "$sum": {
                        "$cond": [
                            {"$lte": [{"$divide": ["$parsed.validity.length", 86400]}, 398]},
                            1,
                            0,
                        ]
                    }
                },
            }
        }
    ]
    stats_result = aggregate_scoped(
        source_collection,
        stats_pipeline,
        scope,
        "idx_scope_validity_length" if scoped else "idx_validity_length",
    )
    stats = stats_result[0] if stats_result else {}
    total = stats.get("total", 0)
    compliant = stats.get("compliantCount", 0)

    # Step 2: Compute validity distribution with sample certificate IDs
    log("Step 2/4: Computing validity distribution")
    bucket_keys = [0, 90, 365, 730]
    bucket_label_map = {0: "< 90 Days", 90: "90 Days - 1 Year", 365: "1 - 2 Years", 730: "> 2 Years"}
    bucket_colors = {0: "#3b82f6", 90: "#10b981", 365: "#8b5cf6", 730: "#f59e0b"}
    bucket_counts = {k: 0 for k in bucket_keys}
    bucket_sample_ids = {k: [] for k in bucket_keys}

    # Scan certificates to count and collect sample IDs. Keep the legacy
    # start/end parsing behavior so results match older pre-compute output.
    validity_find_kwargs = {"hint": "idx_scope_validity_start" if scoped else "idx_validity_start"}
    try:
        validity_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.start": {"$exists": True}, "parsed.validity.end": {"$exists": True}}, scope),
            {"_id": 1, "parsed.validity.start": 1, "parsed.validity.end": 1},
            **validity_find_kwargs,
        ).batch_size(10000)
    except Exception:
        validity_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.start": {"$exists": True}, "parsed.validity.end": {"$exists": True}}, scope),
            {"_id": 1, "parsed.validity.start": 1, "parsed.validity.end": 1},
        ).batch_size(10000)

    for doc in validity_cursor:
        try:
            start_str_value = doc.get("parsed", {}).get("validity", {}).get("start")
            end_str_value = doc.get("parsed", {}).get("validity", {}).get("end")
            if not start_str_value or not end_str_value:
                continue
            start_dt = _dt.strptime(start_str_value, "%Y-%m-%dT%H:%M:%SZ")
            end_dt = _dt.strptime(end_str_value, "%Y-%m-%dT%H:%M:%SZ")
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

        bucket_counts[key] += 1
        if len(bucket_sample_ids[key]) < 1000:
            bucket_sample_ids[key].append(doc["_id"])

    validity_distribution = []
    for bucket_id in bucket_keys:
        count = bucket_counts[bucket_id]
        sample_ids = bucket_sample_ids[bucket_id]
        validity_distribution.append({
            "range": bucket_label_map[bucket_id],
            "count": count,
            "percentage": round((count / total * 100), 1) if total > 0 else 0,
            "color": bucket_colors[bucket_id],
            "certificate_ids": sample_ids,
            "has_more": count > len(sample_ids),
        })

    # Step 3: Compute issuance timeline with sample certificate IDs
    log("Step 3/4: Computing issuance timeline")
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    now = datetime.now(timezone.utc)
    start_date = now.replace(day=1) - relativedelta(months=months - 1)
    end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)

    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Get issued counts
    issued_pipeline = [
        {"$match": {"parsed.validity.start": {"$gte": start_str, "$lte": end_str}}},
        {"$project": {"validFrom": "$parsed.validity.start"}},
        {"$addFields": {"validFromDate": {"$dateFromString": {"dateString": "$validFrom", "onError": None}}}},
        {"$group": {"_id": {"year": {"$year": "$validFromDate"}, "month": {"$month": "$validFromDate"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    issued_results = aggregate_scoped(
        source_collection,
        issued_pipeline,
        scope,
        "idx_scope_validity_start" if scoped else "idx_validity_start",
    )
    issued_lookup = {f"{r['_id']['year']}-{r['_id']['month']}": r["count"] for r in issued_results}

    # Get expiring counts
    expiring_pipeline = [
        {"$match": {"parsed.validity.end": {"$gte": start_str, "$lte": end_str}}},
        {"$project": {"validTo": "$parsed.validity.end"}},
        {"$addFields": {"validToDate": {"$dateFromString": {"dateString": "$validTo", "onError": None}}}},
        {"$group": {"_id": {"year": {"$year": "$validToDate"}, "month": {"$month": "$validToDate"}}, "count": {"$sum": 1}}},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ]
    expiring_results = aggregate_scoped(
        source_collection,
        expiring_pipeline,
        scope,
        "idx_scope_validity_end" if scoped else "idx_validity_end",
    )
    expiring_lookup = {f"{r['_id']['year']}-{r['_id']['month']}": r["count"] for r in expiring_results}

    # Collect issued sample IDs
    issued_ids_map = {}
    try:
        issued_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.start": {"$gte": start_str, "$lte": end_str}}, scope),
            {"_id": 1, "parsed.validity.start": 1},
            hint="idx_scope_validity_start" if scoped else "idx_validity_start",
        ).batch_size(10000)
    except Exception:
        issued_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.start": {"$gte": start_str, "$lte": end_str}}, scope),
            {"_id": 1, "parsed.validity.start": 1},
        ).batch_size(10000)

    for doc in issued_cursor:
        try:
            s = doc.get("parsed", {}).get("validity", {}).get("start")
            if not s:
                continue
            dt = _dt.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            key = f"{dt.year}-{dt.month}"
            if key not in issued_ids_map:
                issued_ids_map[key] = []
            if len(issued_ids_map[key]) < 1000:
                issued_ids_map[key].append(doc["_id"])
        except Exception:
            continue

    # Collect expiring sample IDs
    expiring_ids_map = {}
    try:
        expiring_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.end": {"$gte": start_str, "$lte": end_str}}, scope),
            {"_id": 1, "parsed.validity.end": 1},
            hint="idx_scope_validity_end" if scoped else "idx_validity_end",
        ).batch_size(10000)
    except Exception:
        expiring_cursor = source_collection.find(
            merge_scope_query({"parsed.validity.end": {"$gte": start_str, "$lte": end_str}}, scope),
            {"_id": 1, "parsed.validity.end": 1},
        ).batch_size(10000)

    for doc in expiring_cursor:
        try:
            s = doc.get("parsed", {}).get("validity", {}).get("end")
            if not s:
                continue
            dt = _dt.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            key = f"{dt.year}-{dt.month}"
            if key not in expiring_ids_map:
                expiring_ids_map[key] = []
            if len(expiring_ids_map[key]) < 1000:
                expiring_ids_map[key].append(doc["_id"])
        except Exception:
            continue

    # Build timeline entries
    timeline_entries = []
    current = start_date.replace(day=1)
    while current <= end_date:
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
        })
        if current.month == 12:
            current = current.replace(year=current.year + 1, month=1)
        else:
            current = current.replace(month=current.month + 1)

    # Step 4: Build and write single document
    log("Step 4/4: Writing validity-analysis document")
    validity_analysis_doc = {
        "_id": scoped_doc_id("validity_analysis", scope),
        "scope": scope,
        "averageValidityDays": round(stats.get("avgDuration", 0) or 0),
        "shortestValidityDays": round(stats.get("minDuration", 0) or 0),
        "longestValidityDays": round(stats.get("maxDuration", 0) or 0),
        "complianceRate": round((compliant / total * 100), 1) if total > 0 else 0,
        "totalCertificates": total,
        "computedAt": datetime.now(timezone.utc).isoformat(),
        "sourceCollection": f"{main_db}.certificates",
        "validity_distribution": validity_distribution,
        "issuance_timeline": timeline_entries,
    }

    target_collection.replace_one({"scope": scope}, validity_analysis_doc, upsert=True)
    create_index_if_missing(target_collection, "scope", name="idx_validity_analysis_scope", background=True)
    create_index_if_missing(target_collection, "computedAt", name="idx_validity_analysis_computedAt", background=True)

    if verify:
        stored_doc = target_collection.find_one({"scope": scope})
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
        for scope, _country in get_scopes_for_entry(target):
            compute_validity_analytics(
                client,
                target["main"],
                target["results"],
                months=args.months,
                verify=args.verify,
                scope=scope,
            )
    client.close()


if __name__ == "__main__":
    main()
