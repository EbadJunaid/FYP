#!/usr/bin/env python3
"""
Generic shared keys analytics pre-compute script.

Writes:
- <results_db>.shared-keys-detailed
- <results_db> metadata in shared-keys-detailed
"""

import argparse
import json
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from scope_utils import add_scope_match, create_index_if_missing, get_scope_filter, get_scopes_for_entry, merge_scope_query, normalize_db_entries


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
    targets = []
    for name in db_names:
        if name in lookup:
            targets.append(lookup[name])
        else:
            targets.append({"main": name, "results": f"{name}-results", "countries": []})
    return targets


def get_key_size(cert):
    try:
        if cert.get("parsed", {}).get("subject_key_info", {}).get("rsa_public_key"):
            return cert["parsed"]["subject_key_info"]["rsa_public_key"].get("length", 0)
        if cert.get("parsed", {}).get("subject_key_info", {}).get("ecdsa_public_key"):
            return cert["parsed"]["subject_key_info"]["ecdsa_public_key"].get("length", 0)
        return 0
    except Exception:
        return 0


def calculate_days_until_expiry(validity_end_str):
    try:
        if not validity_end_str:
            return None
        end_date = datetime.fromisoformat(validity_end_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = end_date - now
        return delta.days
    except Exception:
        return None


def compute_shared_keys(client, main_db, results_db, verify=False, scope="all"):
    log(f"Shared keys analytics: {main_db} -> {results_db} scope={scope}")

    source_collection = client[main_db]["certificates"]
    target_db = client[results_db]
    detailed_collection = target_db["shared-keys-detailed"]

    scope_filter = get_scope_filter(scope)
    total_docs = (
        source_collection.count_documents(scope_filter)
        if scope_filter
        else source_collection.estimated_document_count()
    )

    log("Step 1/4: Clearing old shared keys collections")
    old_collections = [
        "shared-keys-groups",
        "shared-keys-stats",
        "shared-keys-distribution",
        "shared-keys-by-issuer",
        "shared-keys-timeline",
        "shared-keys-heatmap",
    ]
    for coll_name in old_collections:
        target_db[coll_name].drop()

    detailed_collection.delete_many({"scope": scope})

    log("Step 2/4: Identifying shared public keys")
    start_time = datetime.now(timezone.utc)

    shared_keys_pipeline = [
        {"$match": {
            "parsed.subject_key_info.fingerprint_sha256": {"$exists": True, "$ne": None},
            "parsed.fingerprint_sha256": {"$exists": True, "$ne": None},
        }},
        {"$group": {
            "_id": "$parsed.subject_key_info.fingerprint_sha256",
            "cert_fingerprints": {"$addToSet": "$parsed.fingerprint_sha256"},
            "cert_count": {"$sum": 1},
        }},
        {"$addFields": {
            "distinct_certs": {"$size": "$cert_fingerprints"}
        }},
        {"$match": {"distinct_certs": {"$gt": 1}}},
    ]

    shared_key_groups = list(source_collection.aggregate(add_scope_match(shared_keys_pipeline, scope), allowDiskUse=True))
    log(f"Found {len(shared_key_groups):,} shared key groups")

    if not shared_key_groups:
        metadata = {
            "_id": f"metadata:{scope}",
            "doc_type": "metadata",
            "scope": scope,
            "last_computed": datetime.now(timezone.utc),
            "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
            "total_shared_groups": 0,
            "total_certs_at_risk": 0,
            "total_certificates_scanned": total_docs,
            "total_public_keys": total_docs,
            "unique_public_keys": total_docs,
        }
        detailed_collection.replace_one({"scope": scope, "doc_type": "metadata"}, metadata, upsert=True)
        if verify:
            stored_meta = detailed_collection.find_one({"scope": scope, "doc_type": "metadata"})
            if not stored_meta:
                raise RuntimeError("Verification failed: metadata missing")
        return

    log("Step 3/4: Processing shared key groups")

    processed_count = 0
    total_certs_at_risk = 0

    for idx, group in enumerate(shared_key_groups):
        if (idx + 1) % 100 == 0:
            log(f"Processed {idx + 1:,}/{len(shared_key_groups):,} groups")

        public_key_hash = group["_id"]

        certificates = list(source_collection.find(merge_scope_query({
            "parsed.subject_key_info.fingerprint_sha256": public_key_hash
        }, scope)))

        if not certificates:
            continue

        certificate_details = []
        all_domains = set()
        all_sans = []
        issuer_map = {}

        for cert in certificates:
            try:
                parsed = cert.get("parsed", {})
                extensions = parsed.get("extensions", {})
                san_ext = extensions.get("subject_alt_name", {})
                sans = san_ext.get("dns_names", [])

                issuer_info = parsed.get("issuer", {})
                issuer_org = issuer_info.get("organization", ["Unknown"])[0] if issuer_info.get("organization") else "Unknown"
                issuer_cn = issuer_info.get("common_name", ["Unknown"])[0] if issuer_info.get("common_name") else "Unknown"
                issuer_dn = parsed.get("issuer_dn", "Unknown")
                issuer_country = issuer_info.get("country", ["Unknown"])[0] if issuer_info.get("country") else "Unknown"

                if issuer_org not in issuer_map:
                    issuer_map[issuer_org] = {"name": issuer_org, "cn": issuer_cn, "count": 0}
                issuer_map[issuer_org]["count"] += 1

                validity = parsed.get("validity", {})
                validity_start = validity.get("start", "")
                validity_end = validity.get("end", "")
                validity_length_seconds = validity.get("length", 0)
                validity_days = validity_length_seconds / 86400 if validity_length_seconds else 0

                days_until_expiry = calculate_days_until_expiry(validity_end)
                is_expired = days_until_expiry is not None and days_until_expiry < 0
                is_expiring_soon = days_until_expiry is not None and 0 <= days_until_expiry < 30

                subject_info = parsed.get("subject", {})
                subject_cn = subject_info.get("common_name", ["Unknown"])[0] if subject_info.get("common_name") else "Unknown"
                subject_dn = parsed.get("subject_dn", "Unknown")

                key_info = parsed.get("subject_key_info", {})
                key_algo = key_info.get("key_algorithm", {}).get("name", "Unknown")
                key_size = get_key_size(cert)
                key_type = f"{key_algo}-{key_size}" if key_size > 0 else key_algo

                signature_info = parsed.get("signature_algorithm", {})
                signature_algo = signature_info.get("name", "Unknown")

                validation_level = parsed.get("validation_level", "Unknown")

                wildcard_sans = [san for san in sans if "*" in san]
                has_wildcard = len(wildcard_sans) > 0

                cert_fingerprint = parsed.get("fingerprint_sha256", "Unknown")
                cert_id = str(cert.get("_id", ""))
                serial_number = parsed.get("serial_number", "Unknown")

                is_self_signed = parsed.get("signature", {}).get("self_signed", False)

                domain = cert.get("domain", "Unknown")
                all_domains.add(domain)
                all_sans.extend(sans)

                scanned_at = cert.get("scanned_at")
                if scanned_at:
                    scanned_at = scanned_at.isoformat() if hasattr(scanned_at, "isoformat") else str(scanned_at)

                eku = extensions.get("extended_key_usage", {})
                extended_key_usage = []
                if eku.get("server_auth"):
                    extended_key_usage.append("serverAuth")
                if eku.get("client_auth"):
                    extended_key_usage.append("clientAuth")

                aia = extensions.get("authority_info_access", {})
                ocsp_urls = aia.get("ocsp_urls", [])
                issuer_urls = aia.get("issuer_urls", [])

                cert_detail = {
                    "certificate_id": cert_id,
                    "certificate_fingerprint": cert_fingerprint,
                    "certificate_fingerprint_short": cert_fingerprint[:16] if cert_fingerprint != "Unknown" else "Unknown",
                    "domain": domain,
                    "sans": sans,
                    "sans_count": len(sans),
                    "has_wildcard": has_wildcard,
                    "wildcard_sans": wildcard_sans,
                    "subject_cn": subject_cn,
                    "subject_dn": subject_dn,
                    "issuer_organization": issuer_org,
                    "issuer_cn": issuer_cn,
                    "issuer_dn": issuer_dn,
                    "issuer_country": issuer_country,
                    "validity_start": validity_start,
                    "validity_end": validity_end,
                    "validity_days": int(validity_days),
                    "is_expired": is_expired,
                    "days_until_expiry": days_until_expiry,
                    "is_expiring_soon": is_expiring_soon,
                    "validation_level": validation_level,
                    "key_algorithm": key_algo,
                    "key_size": key_size,
                    "key_type": key_type,
                    "signature_algorithm": signature_algo,
                    "is_self_signed": is_self_signed,
                    "serial_number": str(serial_number),
                    "extended_key_usage": extended_key_usage,
                    "ocsp_urls": ocsp_urls,
                    "issuer_urls": issuer_urls,
                    "scanned_at": scanned_at,
                }

                certificate_details.append(cert_detail)

            except Exception as exc:
                log(f"Error processing certificate: {exc}")
                continue

        if not certificate_details:
            continue

        cert_count = len(certificate_details)
        total_sans = len(set(all_sans))

        if cert_count >= 5 or total_sans >= 20:
            risk_level = "HIGH"
        elif cert_count >= 3 or total_sans >= 10:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        risk_factors = [
            f"{cert_count} certificates share the same private key",
            f"{len(all_domains)} different domains affected",
            f"{total_sans} SANs at risk if private key is compromised",
        ]

        if len(issuer_map) > 1:
            risk_factors.append(f"Certificates from {len(issuer_map)} different Certificate Authorities")

        domain_sans_count = {}
        for cert_detail in certificate_details:
            domain = cert_detail["domain"]
            sans_count = cert_detail["sans_count"]
            if domain not in domain_sans_count or sans_count > domain_sans_count[domain]:
                domain_sans_count[domain] = sans_count

        most_affected_domain = max(domain_sans_count.items(), key=lambda x: x[1]) if domain_sans_count else ("Unknown", 0)

        key_type = certificate_details[0]["key_type"]
        key_algo = certificate_details[0]["key_algorithm"]
        key_size = certificate_details[0]["key_size"]

        issuers_list = [
            {
                "organization": issuer_data["name"],
                "common_name": issuer_data["cn"],
                "certificate_count": issuer_data["count"],
            }
            for issuer_data in issuer_map.values()
        ]
        issuers_list.sort(key=lambda x: x["certificate_count"], reverse=True)

        sample_domains = list(all_domains)[:3]
        unique_sans = list(set(all_sans))
        sample_sans = unique_sans[:5]

        document = {
            "_id": f"{scope}:{public_key_hash}",
            "doc_type": "shared_key_group",
            "scope": scope,
            "public_key_hash": public_key_hash,
            "public_key_hash_short": public_key_hash[:16],
            "certificate_count": cert_count,
            "total_domains": len(all_domains),
            "sample_domains": sample_domains,
            "total_sans": total_sans,
            "sample_sans": sample_sans,
            "unique_sans": unique_sans,
            "key_algorithm": key_algo,
            "key_size": key_size,
            "key_type": key_type,
            "issuers": issuers_list,
            "issuer_count": len(issuers_list),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "most_affected_domain": {
                "domain": most_affected_domain[0],
                "sans_count": most_affected_domain[1],
            },
            "certificates": certificate_details,
            "computed_at": datetime.now(timezone.utc),
            "last_updated": datetime.now(timezone.utc),
        }

        detailed_collection.replace_one(
            {"scope": scope, "public_key_hash": public_key_hash},
            document,
            upsert=True,
        )

        processed_count += 1
        total_certs_at_risk += cert_count

    log("Step 4/4: Creating indexes")

    create_index_if_missing(detailed_collection, [("scope", 1), ("doc_type", 1)], name="idx_shared_keys_scope_doc_type", background=True)
    create_index_if_missing(detailed_collection, [("scope", 1), ("public_key_hash", 1)], name="idx_shared_keys_scope_public_key_hash", background=True)
    create_index_if_missing(detailed_collection, [("certificate_count", -1)], name="idx_shared_keys_certificate_count", background=True)
    create_index_if_missing(detailed_collection, [("total_sans", -1)], name="idx_shared_keys_total_sans", background=True)
    create_index_if_missing(detailed_collection, [("risk_level", 1)], name="idx_shared_keys_risk_level", background=True)
    create_index_if_missing(detailed_collection, [("key_type", 1)], name="idx_shared_keys_key_type", background=True)
    create_index_if_missing(detailed_collection, [("issuer_count", 1)], name="idx_shared_keys_issuer_count", background=True)
    create_index_if_missing(detailed_collection, [("certificates.domain", 1)], name="idx_shared_keys_cert_domain", background=True)
    create_index_if_missing(detailed_collection, [("issuers.organization", 1)], name="idx_shared_keys_issuer_org", background=True)
    create_index_if_missing(detailed_collection, [("computed_at", -1)], name="idx_shared_keys_computed_at", background=True)

    total_public_keys = total_docs - total_certs_at_risk + processed_count
    unique_public_keys = total_docs - total_certs_at_risk

    metadata = {
        "_id": f"metadata:{scope}",
        "doc_type": "metadata",
        "scope": scope,
        "last_computed": datetime.now(timezone.utc),
        "computation_duration_seconds": (datetime.now(timezone.utc) - start_time).total_seconds(),
        "total_shared_groups": processed_count,
        "total_certs_at_risk": total_certs_at_risk,
        "total_certificates_scanned": total_docs,
        "total_public_keys": total_public_keys,
        "unique_public_keys": unique_public_keys,
    }

    detailed_collection.replace_one({"scope": scope, "doc_type": "metadata"}, metadata, upsert=True)

    if verify:
        stored_groups = detailed_collection.count_documents({"scope": scope, "doc_type": "shared_key_group"})
        if stored_groups != processed_count:
            raise RuntimeError("Verification failed: shared groups count mismatch")
        stored_meta = detailed_collection.find_one({"scope": scope, "doc_type": "metadata"})
        if not stored_meta or stored_meta.get("total_shared_groups") != processed_count:
            raise RuntimeError("Verification failed: metadata shared groups mismatch")

    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    log(f"Completed {main_db} in {duration:.1f}s")


def main():
    parser = argparse.ArgumentParser(description="Generic shared keys analytics pre-compute")
    parser.add_argument("--dbs", nargs="*", help="Main database names")
    parser.add_argument("--config", default=get_default_config_path(), help="Path to databases.json")
    parser.add_argument("--verify", action="store_true", help="Verify stored results")
    args = parser.parse_args()

    entries = load_db_entries(args.config)
    targets = resolve_targets(args.dbs, entries)

    client = MongoClient("mongodb://localhost:27017/")
    for target in targets:
        for scope, _country in get_scopes_for_entry(target):
            compute_shared_keys(client, target["main"], target["results"], verify=args.verify, scope=scope)
    client.close()


if __name__ == "__main__":
    main()
