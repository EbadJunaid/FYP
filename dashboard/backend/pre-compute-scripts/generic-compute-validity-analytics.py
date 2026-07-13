#!/usr/bin/env python3
"""
Generic validity analytics pre-compute script.

Writes one document to:
- <results_db>.validity-analysis

Optimized: all scopes ("all" + every configured country) are computed together.
Aggregations group by the scope field in a single server pass and the sample-id
scans read the collection once, bucketing per scope. Output documents keep the
exact same shape, ids and index names.
"""

import argparse
import json
import os
import re
from datetime import datetime, timezone, timedelta
from dateutil.relativedelta import relativedelta
from pymongo import MongoClient
from scope_utils import create_index_if_missing, get_scopes_for_entry, normalize_db_entries, scoped_doc_id


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


_ISO_Z_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})Z$")


def parse_validity_datetime(value):
    """Parse '%Y-%m-%dT%H:%M:%SZ' like datetime.strptime but faster.

    The fast path accepts exactly the canonical zero-padded form; anything else
    falls back to strptime so the accepted set of strings stays identical to
    the legacy per-scope implementation.
    """
    match = _ISO_Z_RE.match(value)
    if match:
        y, mo, d, h, mi, s = match.groups()
        return datetime(int(y), int(mo), int(d), int(h), int(mi), int(s))
    return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def compute_validity_analytics(client, main_db, results_db, scopes, months=12, verify=False):
    source_collection = client[main_db]["certificates"]
    target_collection = client[results_db]["validity-analysis"]

    scope_names = [scope for scope, _country in scopes]
    country_scopes = set(scope_names) - {"all"}

    log(f"Validity analytics: {main_db} -> {results_db} scopes={len(scope_names)}")
    start_time = datetime.now(timezone.utc)

    # Step 1: Compute validity stats for every scope in one grouped aggregation
    # (plus one covered global aggregation for the "all" scope).
    log("Step 1/4: Computing validity stats (all scopes)")
    duration_expr = {"$divide": ["$parsed.validity.length", 86400]}
    group_body = {
        "avgDuration": {"$avg": duration_expr},
        "minDuration": {"$min": duration_expr},
        "maxDuration": {"$max": duration_expr},
        "total": {"$sum": 1},
        "compliantCount": {
            "$sum": {"$cond": [{"$lte": [duration_expr, 398]}, 1, 0]}
        },
    }
    match_stage = {"$match": {"parsed.validity.length": {"$exists": True, "$gt": 0}}}

    def run_agg(pipeline, hint):
        if hint:
            try:
                return list(source_collection.aggregate(pipeline, hint=hint, allowDiskUse=True))
            except Exception:
                pass
        return list(source_collection.aggregate(pipeline, allowDiskUse=True))

    all_stats_rows = run_agg(
        [match_stage, {"$group": dict(group_body, _id=None)}],
        "idx_validity_length",
    )
    scoped_stats_rows = run_agg(
        [match_stage, {"$group": dict(group_body, _id="$scope")}],
        "idx_scope_validity_length",
    )

    stats_by_scope = {"all": all_stats_rows[0] if all_stats_rows else {}}
    for row in scoped_stats_rows:
        if row["_id"] in country_scopes:
            stats_by_scope[row["_id"]] = row

    # Step 2: Compute validity distribution with sample certificate IDs.
    # Single scan; each document is bucketed into "all" plus its own scope.
    log("Step 2/4: Computing validity distribution (single scan)")
    bucket_keys = [0, 90, 365, 730]
    bucket_label_map = {0: "< 90 Days", 90: "90 Days - 1 Year", 365: "1 - 2 Years", 730: "> 2 Years"}
    bucket_colors = {0: "#3b82f6", 90: "#10b981", 365: "#8b5cf6", 730: "#f59e0b"}
    bucket_counts = {s: {k: 0 for k in bucket_keys} for s in scope_names}
    bucket_sample_ids = {s: {k: [] for k in bucket_keys} for s in scope_names}

    validity_query = {
        "parsed.validity.start": {"$exists": True},
        "parsed.validity.end": {"$exists": True},
    }
    validity_projection = {"_id": 1, "scope": 1, "parsed.validity.start": 1, "parsed.validity.end": 1}
    try:
        validity_cursor = source_collection.find(
            validity_query, validity_projection, hint="idx_validity_start"
        ).batch_size(10000)
    except Exception:
        validity_cursor = source_collection.find(validity_query, validity_projection).batch_size(10000)

    for doc in validity_cursor:
        try:
            validity = doc.get("parsed", {}).get("validity", {})
            start_str_value = validity.get("start")
            end_str_value = validity.get("end")
            if not start_str_value or not end_str_value:
                continue
            start_dt = parse_validity_datetime(start_str_value)
            end_dt = parse_validity_datetime(end_str_value)
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

        doc_scope = doc.get("scope")
        for s in ("all", doc_scope) if doc_scope in country_scopes else ("all",):
            bucket_counts[s][key] += 1
            samples = bucket_sample_ids[s][key]
            if len(samples) < 1000:
                samples.append(doc["_id"])

    # Step 3: Compute issuance timeline with sample certificate IDs.
    log("Step 3/4: Computing issuance timeline (all scopes)")
    month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    now = datetime.now(timezone.utc)
    start_date = now.replace(day=1) - relativedelta(months=months - 1)
    end_date = now.replace(day=1) + relativedelta(months=1) - timedelta(seconds=1)

    start_str = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    end_str = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    def timeline_counts(field, hint):
        pipeline = [
            {"$match": {field: {"$gte": start_str, "$lte": end_str}}},
            {"$project": {"scope": 1, "validDate": {"$dateFromString": {"dateString": f"${field}", "onError": None}}}},
            {"$group": {
                "_id": {"scope": "$scope", "year": {"$year": "$validDate"}, "month": {"$month": "$validDate"}},
                "count": {"$sum": 1},
            }},
        ]
        rows = run_agg(pipeline, hint)
        lookup = {s: {} for s in scope_names}
        for row in rows:
            key = f"{row['_id']['year']}-{row['_id']['month']}"
            lookup["all"][key] = lookup["all"].get(key, 0) + row["count"]
            row_scope = row["_id"].get("scope")
            if row_scope in country_scopes:
                lookup[row_scope][key] = lookup[row_scope].get(key, 0) + row["count"]
        return lookup

    issued_lookup = timeline_counts("parsed.validity.start", "idx_validity_start")
    expiring_lookup = timeline_counts("parsed.validity.end", "idx_validity_end")

    def timeline_sample_ids(field, hint):
        query = {field: {"$gte": start_str, "$lte": end_str}}
        projection = {"_id": 1, "scope": 1, field: 1}
        try:
            cursor = source_collection.find(query, projection, hint=hint).batch_size(10000)
        except Exception:
            cursor = source_collection.find(query, projection).batch_size(10000)

        ids_map = {s: {} for s in scope_names}
        parts = field.split(".")
        for doc in cursor:
            try:
                value = doc
                for part in parts:
                    value = value.get(part, {})
                if not value:
                    continue
                dt = parse_validity_datetime(value)
                key = f"{dt.year}-{dt.month}"
            except Exception:
                continue

            doc_scope = doc.get("scope")
            for s in ("all", doc_scope) if doc_scope in country_scopes else ("all",):
                bucket = ids_map[s].setdefault(key, [])
                if len(bucket) < 1000:
                    bucket.append(doc["_id"])
        return ids_map

    issued_ids_map = timeline_sample_ids("parsed.validity.start", "idx_validity_start")
    expiring_ids_map = timeline_sample_ids("parsed.validity.end", "idx_validity_end")

    # Step 4: Build and write one document per scope
    log("Step 4/4: Writing validity-analysis documents")
    for scope in scope_names:
        stats = stats_by_scope.get(scope, {})
        total = stats.get("total", 0)
        compliant = stats.get("compliantCount", 0)

        validity_distribution = []
        for bucket_id in bucket_keys:
            count = bucket_counts[scope][bucket_id]
            sample_ids = bucket_sample_ids[scope][bucket_id]
            validity_distribution.append({
                "range": bucket_label_map[bucket_id],
                "count": count,
                "percentage": round((count / total * 100), 1) if total > 0 else 0,
                "color": bucket_colors[bucket_id],
                "certificate_ids": sample_ids,
                "has_more": count > len(sample_ids),
            })

        timeline_entries = []
        current = start_date.replace(day=1)
        while current <= end_date:
            key = f"{current.year}-{current.month}"
            month_label = f"{month_names[current.month - 1]} '{str(current.year)[2:]}"
            issued_count = issued_lookup[scope].get(key, 0)
            expiring_count = expiring_lookup[scope].get(key, 0)
            issued_sample = issued_ids_map[scope].get(key, [])
            expiring_sample = expiring_ids_map[scope].get(key, [])
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

        if verify:
            stored_doc = target_collection.find_one({"scope": scope})
            if not stored_doc:
                raise RuntimeError("Verification failed: validity-analysis document missing")
            if stored_doc.get("totalCertificates") != total:
                raise RuntimeError("Verification failed: totalCertificates mismatch")

    create_index_if_missing(target_collection, "scope", name="idx_validity_analysis_scope", background=True)
    create_index_if_missing(target_collection, "computedAt", name="idx_validity_analysis_computedAt", background=True)

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
            get_scopes_for_entry(target),
            months=args.months,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
