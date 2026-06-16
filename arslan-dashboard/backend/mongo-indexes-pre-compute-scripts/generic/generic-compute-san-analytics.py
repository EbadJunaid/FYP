#!/usr/bin/env python3
"""
Generic SAN analytics pre-compute script.

Reads databases.json unless --dbs is provided, and writes one document to:
- <results_db>.san-analysis
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING
from scope_utils import get_scope_filter, get_scopes_for_entry, merge_scope_query, normalize_db_entries, scoped_doc_id


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
    return normalize_db_entries(items)


def resolve_targets(db_names, entries):
    if not db_names:
        return entries

    lookup = {entry["main"]: entry for entry in entries}
    # print(f"lookup: {lookup}")
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            # print(f"in else condition of resolve_targets: {name}")
            targets.append({"main": name, "results": f"{name}-results", "countries": []})
    return targets


def extract_tld(domain):
    if not domain or not isinstance(domain, str):
        return None
    parts = domain.lower().split(".")
    if len(parts) >= 2:
        return "." + parts[-1]
    return None


def count_vulnerabilities(zlint_data):
    if not zlint_data or "lints" not in zlint_data:
        return {"errors": 0, "warnings": 0}

    lints = zlint_data.get("lints", {})
    errors = sum(
        1 for v in lints.values() if isinstance(v, dict) and v.get("result") == "error"
    )
    warnings = sum(
        1 for v in lints.values() if isinstance(v, dict) and v.get("result") == "warn"
    )

    return {"errors": errors, "warnings": warnings}


def format_vulnerabilities(zlint_data):
    counts = count_vulnerabilities(zlint_data)
    if counts["errors"] > 0:
        return f"{counts['errors']} Critical"
    if counts["warnings"] > 0:
        return f"{counts['warnings']} Warning"
    return "0 Found"


def pick_country(cert):
    countries = cert.get("parsed", {}).get("issuer", {}).get("country", [])
    if not countries:
        countries = cert.get("parsed", {}).get("subject", {}).get("country", [])
    if isinstance(countries, list):
        return countries[0] if countries else "Unknown"
    if isinstance(countries, str):
        return countries
    return "Unknown"


def compute_san_analytics(client, main_db, results_db, limit=None, verify=False, scope="all"):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]

    # Legacy split-collection approach kept here for review:
    # wildcard_collection = results_db_ref["san-wildcard-certs"]
    # standard_collection = results_db_ref["san-standard-certs"]
    # multi_domain_collection = results_db_ref["san-multi-domain-certs"]
    # san_count_collection = results_db_ref["san-count-groups"]
    # tld_collection = results_db_ref["san-tld-certs"]
    # stats_collection = results_db_ref["san-stats"]
    # distribution_collection = results_db_ref["san-distribution"]
    # metadata_collection = results_db_ref["san-filter-metadata"]
    #
    # New approach requested for now:
    # one collection, one document with counts and first-1000 ObjectId arrays.
    target_collection = results_db_ref["san-analysis"]

    log(f"SAN analytics: {main_db} -> {results_db} scope={scope}")
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

    target_collection.delete_many({"scope": scope})

    start_time = datetime.now(timezone.utc)

    scope_filter = get_scope_filter(scope)
    total_docs = (
        source_collection.count_documents(scope_filter)
        if scope_filter
        else source_collection.estimated_document_count()
    )
    if limit:
        total_docs = min(limit, total_docs)

    log(f"Step 2/4: Scanning certificates ({total_docs:,} total)")

    # Legacy split-collection approach stored full cert_ref docs in these lists:
    # wildcard_certs = []
    # standard_certs = []
    # multi_domain_certs = []
    #
    # New approach stores only first 1000 ObjectIds per group/category.
    wildcard_count = 0
    standard_count = 0
    multi_domain_count = 0
    total_sans_count = 0
    wildcard_certificate_ids = []
    standard_certificate_ids = []
    multi_domain_certificate_ids = []

    bucket_order = ["0", "1", "2-3", "4-5", "6-10", "11-30", "31-50", "50+"]
    distribution_buckets = {bucket: 0 for bucket in bucket_order}

    san_count_groups = {}
    tld_groups = {}

    def add_group(group_map, bucket, cert_id):
        # Legacy shape was {"count": int, "certs": [cert_ref, ...]}.
        # New shape is {"count": int, "certificate_ids": [ObjectId, ...]}.
        entry = group_map.setdefault(bucket, {"count": 0, "certificate_ids": []})
        entry["count"] += 1
        if len(entry["certificate_ids"]) < 1000:
            entry["certificate_ids"].append(cert_id)

    def add_tld(tld, cert_id, seen_tlds):
        if tld in seen_tlds:
            return
        seen_tlds.add(tld)
        entry = tld_groups.setdefault(tld, {"count": 0, "certificate_ids": []})
        entry["count"] += 1
        if len(entry["certificate_ids"]) < 1000:
            entry["certificate_ids"].append(cert_id)

    batch_size = 10000
    progress_interval = 5000
    processed = 0

    cursor = source_collection.find(
        merge_scope_query({}, scope),
        {
            "_id": 1,
            "domain": 1,
            "parsed.extensions.subject_alt_name.dns_names": 1,
            "parsed.issuer.common_name": 1,
            "parsed.validity.end": 1,
            "parsed.signature_algorithm.name": 1,
            "parsed.issuer.country": 1,
            "parsed.subject.country": 1,
            "zlint": 1,
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
        domain = cert.get("domain", "")

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

        total_sans_count += san_count

        if san_count == 0:
            bucket = "0"
        elif san_count == 1:
            bucket = "1"
        elif 2 <= san_count <= 3:
            bucket = "2-3"
        elif 4 <= san_count <= 5:
            bucket = "4-5"
        elif 6 <= san_count <= 10:
            bucket = "6-10"
        elif 11 <= san_count <= 30:
            bucket = "11-30"
        elif 31 <= san_count <= 50:
            bucket = "31-50"
        else:
            bucket = "50+"

        distribution_buckets[bucket] += 1

        # Legacy code built a full cert_ref here and inserted it into separate
        # collections. Backend APIs now hydrate these ObjectIds from the main
        # certificates collection when filtered SAN certs are requested.
        #
        # cert_ref = {
        #     "cert_id": cert_id,
        #     "domain": domain,
        #     "san_count": san_count,
        #     "sample_sans": sans[:5] if sans else [],
        #     ...
        # }
        has_wildcard = any(s.startswith("*.") for s in sans)
        if has_wildcard:
            wildcard_count += 1
            if len(wildcard_certificate_ids) < 1000:
                wildcard_certificate_ids.append(cert_id)

        if san_count > 0 and not has_wildcard:
            standard_count += 1
            if len(standard_certificate_ids) < 1000:
                standard_certificate_ids.append(cert_id)

        if san_count >= 5:
            multi_domain_count += 1
            if len(multi_domain_certificate_ids) < 1000:
                multi_domain_certificate_ids.append(cert_id)

        add_group(san_count_groups, bucket, cert_id)

        seen_tlds = set()
        for san in sans:
            tld = extract_tld(san)
            if tld:
                add_tld(tld, cert_id, seen_tlds)

    log("Step 3/4: Building single san-analysis document")

    bucket_groups = []
    for bucket in bucket_order:
        entry = san_count_groups.get(bucket, {"count": 0, "certificate_ids": []})
        bucket_groups.append({
            "bucket": bucket,
            "count": entry["count"],
            "certificate_ids": entry["certificate_ids"],
            "has_more": entry["count"] > len(entry["certificate_ids"]),
        })

    tld_groups_list = []
    for tld, entry in sorted(tld_groups.items(), key=lambda x: x[1]["count"], reverse=True)[:50]:
        tld_groups_list.append({
            "tld": tld,
            "count": entry["count"],
            "certificate_ids": entry["certificate_ids"],
            "has_more": entry["count"] > len(entry["certificate_ids"]),
        })

    avg_sans = total_sans_count / processed if processed else 0
    san_analysis_doc = {
        "_id": scoped_doc_id("san_analysis", scope),
        "scope": scope,
        "total_san_count": total_sans_count,
        "avg_san_count": round(avg_sans, 2),
        "total_certificates": processed,
        "standard_san_count": standard_count,
        "standard_san_certificate_ids": standard_certificate_ids,
        "standard_san_has_more": standard_count > len(standard_certificate_ids),
        "multi_domain_count": multi_domain_count,
        "multi_domain_certificate_ids": multi_domain_certificate_ids,
        "multi_domain_has_more": multi_domain_count > len(multi_domain_certificate_ids),
        "wildcard_san_count": wildcard_count,
        "wildcard_certificate_ids": wildcard_certificate_ids,
        "wildcard_has_more": wildcard_count > len(wildcard_certificate_ids),
        "bucket_groups": bucket_groups,
        "tlds": tld_groups_list,
        "computed_at": datetime.now(timezone.utc),
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        "source_database": main_db,
        "source_collection": "certificates",
        "testing_mode": bool(limit),
    }

    log("Step 4/4: Writing san-analysis document")
    target_collection.replace_one({"scope": scope}, san_analysis_doc, upsert=True)
    target_collection.create_index([("scope", ASCENDING)])
    target_collection.create_index([("computed_at", ASCENDING)])

    if verify:
        stored_doc = target_collection.find_one({"scope": scope})
        if not stored_doc:
            raise RuntimeError("Verification failed: san-analysis document missing")
        if stored_doc.get("total_certificates") != processed:
            raise RuntimeError("Verification failed: total_certificates mismatch")
        if stored_doc.get("wildcard_san_count") != wildcard_count:
            raise RuntimeError("Verification failed: wildcard count mismatch")
        if stored_doc.get("standard_san_count") != standard_count:
            raise RuntimeError("Verification failed: standard count mismatch")
        if stored_doc.get("multi_domain_count") != multi_domain_count:
            raise RuntimeError("Verification failed: multi-domain count mismatch")
        stored_bucket_total = sum(item.get("count", 0) for item in stored_doc.get("bucket_groups", []))
        if stored_bucket_total != processed:
            raise RuntimeError("Verification failed: bucket total mismatch")

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
    # print(f"entries: {entries}")

    targets = resolve_targets(args.dbs, entries)
    # print(f"Targets: {targets}")
    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        for scope, _country in get_scopes_for_entry(target):
            compute_san_analytics(
                client,
                target["main"],
                target["results"],
                limit=args.limit,
                verify=args.verify,
                scope=scope,
            )
        # print(target," - Skipping actual computation (uncomment to run)")
    client.close()


if __name__ == "__main__":
    main()
