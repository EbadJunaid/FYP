#!/usr/bin/env python3
"""
Generic SAN analytics pre-compute script.

Reads databases.json unless --dbs is provided, and writes one document to:
- <results_db>.san-analysis

Optimized: all scopes ("all" + every configured country) are computed in a
single pass over the certificates collection instead of one full scan per
scope. Output documents keep the exact same shape, ids and index names.
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
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


def extract_tld(domain):
    if not domain or not isinstance(domain, str):
        return None
    parts = domain.lower().split(".")
    if len(parts) >= 2:
        return "." + parts[-1]
    return None


BUCKET_ORDER = ["0", "1", "2-3", "4-5", "6-10", "11-30", "31-50", "50+"]


def _new_bucket():
    return {
        "wildcard_count": 0,
        "standard_count": 0,
        "multi_domain_count": 0,
        "total_sans_count": 0,
        "processed": 0,
        "wildcard_certificate_ids": [],
        "standard_certificate_ids": [],
        "multi_domain_certificate_ids": [],
        "distribution_buckets": {bucket: 0 for bucket in BUCKET_ORDER},
        "san_count_groups": {},
        "tld_groups": {},
    }


def _bucket_for_count(san_count):
    if san_count == 0:
        return "0"
    if san_count == 1:
        return "1"
    if 2 <= san_count <= 3:
        return "2-3"
    if 4 <= san_count <= 5:
        return "4-5"
    if 6 <= san_count <= 10:
        return "6-10"
    if 11 <= san_count <= 30:
        return "11-30"
    if 31 <= san_count <= 50:
        return "31-50"
    return "50+"


def compute_san_analytics(client, main_db, results_db, scopes, limit=None, verify=False):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]
    target_collection = results_db_ref["san-analysis"]

    scope_names = [scope for scope, _country in scopes]
    log(f"SAN analytics: {main_db} -> {results_db} scopes={', '.join(scope_names[:5])}... ({len(scope_names)} total)")
    log("Step 1/4: Clearing existing SAN analytics collections")

    # Drop legacy split collections so stale data does not look authoritative.
    for collection_name in [
        "san-wildcard-certs",
        "san-standard-certs",
        "san-multi-domain-certs",
        "san-count-groups",
        "san-tld-certs",
        "san-stats",
        "san-distribution",
        "san-filter-metadata",
    ]:
        results_db_ref[collection_name].drop()

    target_collection.delete_many({"scope": {"$in": scope_names}})

    start_time = datetime.now(timezone.utc)

    total_docs = source_collection.estimated_document_count()
    if limit:
        total_docs = min(limit, total_docs)

    log(f"Step 2/4: Scanning certificates once for all scopes ({total_docs:,} total)")

    buckets = {scope: _new_bucket() for scope in scope_names}
    all_bucket = buckets.get("all")
    country_scopes = set(scope_names) - {"all"}

    batch_size = 10000
    progress_interval = 10000
    processed = 0

    cursor = source_collection.find(
        {},
        {
            "_id": 1,
            "scope": 1,
            "parsed.extensions.subject_alt_name.dns_names": 1,
        },
    ).batch_size(batch_size)

    if limit:
        cursor = cursor.limit(limit)

    for cert in cursor:
        processed += 1

        if processed % progress_interval == 0:
            elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
            rate = processed / elapsed if elapsed else 0
            remaining = (total_docs - processed) / rate if rate else 0
            percent = (processed / total_docs) * 100 if total_docs else 0
            log(f"  Processed {processed:,}/{total_docs:,} ({percent:.1f}%) - ETA {remaining:.0f}s")

        cert_id = cert["_id"]
        sans = (
            cert.get("parsed", {})
            .get("extensions", {})
            .get("subject_alt_name", {})
            .get("dns_names", [])
        )
        if not isinstance(sans, list):
            sans = []
        sans = [s for s in sans if s and isinstance(s, str)]
        san_count = len(sans)
        bucket_key = _bucket_for_count(san_count)
        has_wildcard = any(s.startswith("*.") for s in sans)

        # Distinct TLDs of this cert, preserving first-seen order.
        cert_tlds = []
        seen_tlds = set()
        for san in sans:
            tld = extract_tld(san)
            if tld and tld not in seen_tlds:
                seen_tlds.add(tld)
                cert_tlds.append(tld)

        targets = []
        if all_bucket is not None:
            targets.append(all_bucket)
        doc_scope = cert.get("scope")
        if doc_scope in country_scopes:
            targets.append(buckets[doc_scope])

        for acc in targets:
            acc["processed"] += 1
            acc["total_sans_count"] += san_count
            acc["distribution_buckets"][bucket_key] += 1

            if has_wildcard:
                acc["wildcard_count"] += 1
                if len(acc["wildcard_certificate_ids"]) < 1000:
                    acc["wildcard_certificate_ids"].append(cert_id)

            if san_count > 0 and not has_wildcard:
                acc["standard_count"] += 1
                if len(acc["standard_certificate_ids"]) < 1000:
                    acc["standard_certificate_ids"].append(cert_id)

            if san_count >= 5:
                acc["multi_domain_count"] += 1
                if len(acc["multi_domain_certificate_ids"]) < 1000:
                    acc["multi_domain_certificate_ids"].append(cert_id)

            group_entry = acc["san_count_groups"].setdefault(bucket_key, {"count": 0, "certificate_ids": []})
            group_entry["count"] += 1
            if len(group_entry["certificate_ids"]) < 1000:
                group_entry["certificate_ids"].append(cert_id)

            for tld in cert_tlds:
                tld_entry = acc["tld_groups"].setdefault(tld, {"count": 0, "certificate_ids": []})
                tld_entry["count"] += 1
                if len(tld_entry["certificate_ids"]) < 1000:
                    tld_entry["certificate_ids"].append(cert_id)

    log("Step 3/4: Building san-analysis documents per scope")

    for scope in scope_names:
        acc = buckets[scope]

        bucket_groups = []
        for bucket in BUCKET_ORDER:
            entry = acc["san_count_groups"].get(bucket, {"count": 0, "certificate_ids": []})
            bucket_groups.append({
                "bucket": bucket,
                "count": entry["count"],
                "certificate_ids": entry["certificate_ids"],
                "has_more": entry["count"] > len(entry["certificate_ids"]),
            })

        tld_groups_list = []
        for tld, entry in sorted(acc["tld_groups"].items(), key=lambda x: x[1]["count"], reverse=True)[:50]:
            tld_groups_list.append({
                "tld": tld,
                "count": entry["count"],
                "certificate_ids": entry["certificate_ids"],
                "has_more": entry["count"] > len(entry["certificate_ids"]),
            })

        scope_processed = acc["processed"]
        avg_sans = acc["total_sans_count"] / scope_processed if scope_processed else 0
        san_analysis_doc = {
            "_id": scoped_doc_id("san_analysis", scope),
            "scope": scope,
            "total_san_count": acc["total_sans_count"],
            "avg_san_count": round(avg_sans, 2),
            "total_certificates": scope_processed,
            "standard_san_count": acc["standard_count"],
            "standard_san_certificate_ids": acc["standard_certificate_ids"],
            "standard_san_has_more": acc["standard_count"] > len(acc["standard_certificate_ids"]),
            "multi_domain_count": acc["multi_domain_count"],
            "multi_domain_certificate_ids": acc["multi_domain_certificate_ids"],
            "multi_domain_has_more": acc["multi_domain_count"] > len(acc["multi_domain_certificate_ids"]),
            "wildcard_san_count": acc["wildcard_count"],
            "wildcard_certificate_ids": acc["wildcard_certificate_ids"],
            "wildcard_has_more": acc["wildcard_count"] > len(acc["wildcard_certificate_ids"]),
            "bucket_groups": bucket_groups,
            "tlds": tld_groups_list,
            "computed_at": datetime.now(timezone.utc),
            "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "source_database": main_db,
            "source_collection": "certificates",
            "testing_mode": bool(limit),
        }

        target_collection.replace_one({"scope": scope}, san_analysis_doc, upsert=True)

        if verify:
            stored_doc = target_collection.find_one({"scope": scope})
            if not stored_doc:
                raise RuntimeError("Verification failed: san-analysis document missing")
            if stored_doc.get("total_certificates") != scope_processed:
                raise RuntimeError("Verification failed: total_certificates mismatch")
            if stored_doc.get("wildcard_san_count") != acc["wildcard_count"]:
                raise RuntimeError("Verification failed: wildcard count mismatch")
            if stored_doc.get("standard_san_count") != acc["standard_count"]:
                raise RuntimeError("Verification failed: standard count mismatch")
            if stored_doc.get("multi_domain_count") != acc["multi_domain_count"]:
                raise RuntimeError("Verification failed: multi-domain count mismatch")
            stored_bucket_total = sum(item.get("count", 0) for item in stored_doc.get("bucket_groups", []))
            if stored_bucket_total != scope_processed:
                raise RuntimeError("Verification failed: bucket total mismatch")

    log("Step 4/4: Creating indexes")
    create_index_if_missing(target_collection, [("scope", ASCENDING)], name="idx_san_analysis_scope", background=True)
    create_index_if_missing(target_collection, [("computed_at", ASCENDING)], name="idx_san_analysis_computed_at", background=True)
    create_index_if_missing(target_collection, [("bucket_groups.bucket", ASCENDING)], name="idx_san_analysis_bucket", background=True)
    create_index_if_missing(target_collection, [("tlds.tld", ASCENDING)], name="idx_san_analysis_tld", background=True)

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic SAN analytics pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--limit", type=int, default=None, help="Limit documents processed")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        compute_san_analytics(
            client,
            target["main"],
            target["results"],
            get_scopes_for_entry(target),
            limit=args.limit,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
