#!/usr/bin/env python3
"""
Generic SAN analytics pre-compute script.

Reads databases.json unless --dbs is provided, and writes:
- <results_db>.san-stats
- <results_db>.san-distribution
- <results_db>.san-wildcard-certs
- <results_db>.san-standard-certs
- <results_db>.san-multi-domain-certs
- <results_db>.san-count-groups
- <results_db>.san-tld-certs
- <results_db>.san-filter-metadata
"""

import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING


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


def compute_san_analytics(client, main_db, results_db, limit=None, verify=False):
    source_collection = client[main_db]["certificates"]
    results_db_ref = client[results_db]

    wildcard_collection = results_db_ref["san-wildcard-certs"]
    standard_collection = results_db_ref["san-standard-certs"]
    multi_domain_collection = results_db_ref["san-multi-domain-certs"]
    san_count_collection = results_db_ref["san-count-groups"]
    tld_collection = results_db_ref["san-tld-certs"]
    stats_collection = results_db_ref["san-stats"]
    distribution_collection = results_db_ref["san-distribution"]
    metadata_collection = results_db_ref["san-filter-metadata"]

    log(f"SAN analytics: {main_db} -> {results_db}")
    log("Step 1/5: Clearing existing SAN collections")

    wildcard_collection.drop()
    standard_collection.drop()
    multi_domain_collection.drop()
    san_count_collection.drop()
    tld_collection.drop()
    stats_collection.drop()
    distribution_collection.drop()
    metadata_collection.drop()

    start_time = datetime.now(timezone.utc)

    total_docs = source_collection.estimated_document_count()
    if limit:
        total_docs = min(limit, total_docs)

    log(f"Step 2/5: Scanning certificates ({total_docs:,} total)")

    wildcard_certs = []
    standard_certs = []
    multi_domain_certs = []

    wildcard_count = 0
    standard_count = 0
    multi_domain_count = 0
    total_sans_count = 0

    bucket_order = ["0", "1", "2-3", "4-5", "6-10", "11-30", "31-50", "50+"]
    distribution_buckets = {bucket: 0 for bucket in bucket_order}

    san_count_groups = {}
    tld_groups = {}

    def add_group(group_map, bucket, cert_ref):
        entry = group_map.setdefault(bucket, {"count": 0, "certs": []})
        entry["count"] += 1
        if len(entry["certs"]) < 1000:
            entry["certs"].append(cert_ref)

    def add_tld(tld, cert_ref, seen_tlds):
        if tld in seen_tlds:
            return
        seen_tlds.add(tld)
        entry = tld_groups.setdefault(tld, {"count": 0, "certs": []})
        entry["count"] += 1
        if len(entry["certs"]) < 1000:
            entry["certs"].append(cert_ref)

    def flush_batches():
        if wildcard_certs:
            wildcard_collection.insert_many(wildcard_certs, ordered=False)
            wildcard_certs.clear()
        if standard_certs:
            standard_collection.insert_many(standard_certs, ordered=False)
            standard_certs.clear()
        if multi_domain_certs:
            multi_domain_collection.insert_many(multi_domain_certs, ordered=False)
            multi_domain_certs.clear()

    batch_size = 10000
    flush_interval = 10000
    progress_interval = 5000
    processed = 0

    cursor = source_collection.find(
        {},
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

        if processed % flush_interval == 0:
            flush_batches()

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

        sig_alg = cert.get("parsed", {}).get("signature_algorithm", {})
        encryption = sig_alg.get("name", "Unknown") if sig_alg else "Unknown"
        country = pick_country(cert)
        vulnerabilities = format_vulnerabilities(cert.get("zlint", {}))

        cert_ref = {
            "cert_id": cert_id,
            "domain": domain,
            "san_count": san_count,
            "sample_sans": sans[:5] if sans else [],
            "issuer": cert.get("parsed", {}).get("issuer", {}).get("common_name", "N/A"),
            "expiry": cert.get("parsed", {}).get("validity", {}).get("end"),
            "encryption": encryption,
            "country": country,
            "vulnerabilities": vulnerabilities,
        }

        has_wildcard = any(s.startswith("*.") for s in sans)
        if has_wildcard:
            wildcard_certs.append(cert_ref)
            wildcard_count += 1

        if san_count > 0 and not has_wildcard:
            standard_certs.append(cert_ref)
            standard_count += 1

        if san_count >= 5:
            multi_domain_certs.append(cert_ref)
            multi_domain_count += 1

        add_group(san_count_groups, bucket, cert_ref)

        seen_tlds = set()
        for san in sans:
            tld = extract_tld(san)
            if tld:
                add_tld(tld, cert_ref, seen_tlds)

    flush_batches()
    log("Step 3/5: Creating indexes")

    wildcard_count_total = wildcard_collection.count_documents({})
    if wildcard_count_total > 0:
        wildcard_collection.create_index([("domain", ASCENDING)])
        wildcard_collection.create_index([("san_count", ASCENDING)])
        wildcard_collection.create_index([("cert_id", ASCENDING)])

    standard_count_total = standard_collection.count_documents({})
    if standard_count_total > 0:
        standard_collection.create_index([("domain", ASCENDING)])
        standard_collection.create_index([("san_count", ASCENDING)])
        standard_collection.create_index([("cert_id", ASCENDING)])

    multi_count_total = multi_domain_collection.count_documents({})
    if multi_count_total > 0:
        multi_domain_collection.create_index([("san_count", ASCENDING)])
        multi_domain_collection.create_index([("domain", ASCENDING)])
        multi_domain_collection.create_index([("cert_id", ASCENDING)])

    log("Step 4/5: Writing grouped collections")

    for bucket, entry in san_count_groups.items():
        doc = {
            "_id": bucket,
            "certificate_count": entry["count"],
            "certificates": entry["certs"],
            "has_more": entry["count"] > len(entry["certs"]),
            "total_count": entry["count"],
        }
        san_count_collection.replace_one({"_id": bucket}, doc, upsert=True)

    san_count_collection.create_index([("certificate_count", ASCENDING)])

    tld_sorted = sorted(tld_groups.items(), key=lambda x: x[1]["count"], reverse=True)[:50]
    for tld, entry in tld_sorted:
        doc = {
            "_id": tld,
            "certificate_count": entry["count"],
            "certificates": entry["certs"],
            "has_more": entry["count"] > len(entry["certs"]),
            "total_count": entry["count"],
        }
        tld_collection.replace_one({"_id": tld}, doc, upsert=True)

    tld_collection.create_index([("certificate_count", ASCENDING)])

    log("Step 5/5: Writing stats and distribution")

    avg_sans = total_sans_count / processed if processed else 0
    stats_doc = {
        "_id": "san_stats",
        "total_sans": total_sans_count,
        "avg_sans_per_cert": round(avg_sans, 2),
        "wildcard_certs": wildcard_count,
        "multi_domain_certs": multi_domain_count,
        "total_certs": processed,
        "computed_at": datetime.now(timezone.utc),
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
    }
    stats_collection.replace_one({"_id": "san_stats"}, stats_doc, upsert=True)

    for idx, bucket in enumerate(bucket_order):
        dist_doc = {
            "_id": idx,
            "bucket_id": idx,
            "bucket": bucket,
            "count": distribution_buckets[bucket],
            "computed_at": datetime.now(timezone.utc),
        }
        distribution_collection.replace_one({"_id": idx}, dist_doc, upsert=True)

    dist_metadata = {
        "_id": "metadata",
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        "total_buckets": len(bucket_order),
    }
    distribution_collection.replace_one({"_id": "metadata"}, dist_metadata, upsert=True)

    metadata = {
        "_id": "metadata",
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        "total_certificates_scanned": processed,
        "wildcard_certificates": wildcard_count_total,
        "standard_certificates": standard_count_total,
        "multi_domain_certificates": multi_count_total,
        "san_count_groups": {k: v["count"] for k, v in san_count_groups.items()},
        "top_tlds_count": len(tld_sorted),
    }
    metadata_collection.replace_one({"_id": "metadata"}, metadata, upsert=True)

    if verify:
        if wildcard_count_total != wildcard_count:
            raise RuntimeError("Verification failed: wildcard count mismatch")
        if standard_count_total != standard_count:
            raise RuntimeError("Verification failed: standard count mismatch")
        if multi_count_total != multi_domain_count:
            raise RuntimeError("Verification failed: multi-domain count mismatch")
        stored_stats = stats_collection.find_one({"_id": "san_stats"})
        if not stored_stats or stored_stats.get("total_certs") != processed:
            raise RuntimeError("Verification failed: san-stats total_certs mismatch")
        if sum(distribution_buckets.values()) != processed:
            raise RuntimeError("Verification failed: distribution total mismatch")

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
            limit=args.limit,
            verify=args.verify,
        )
    client.close()


if __name__ == "__main__":
    main()
