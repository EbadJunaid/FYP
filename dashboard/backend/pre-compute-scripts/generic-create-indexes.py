#!/usr/bin/env python3
"""
Create MongoDB indexes for one or more databases.

Usage:
  python3 create-indexes-generic.py
  python3 create-indexes-generic.py --dbs tranco-latest-8-lakh pakistani-domains
  python3 create-indexes-generic.py --config ./databases.json
  python3 create-indexes-generic.py --dry-run
"""

import argparse
import json
import os
from pymongo import MongoClient, ASCENDING, DESCENDING
from scope_utils import create_index_if_missing

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SCRIPT_DIR, "..", "..", ".."))
DEFAULT_CONFIG = os.path.join(_PROJECT_ROOT, "project-config.json")


def load_db_entries(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return _normalize_db_entries(data)

    if isinstance(data, dict):
        if "databases" in data:
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


def build_source_indexes():
    # Indexes referenced by API queries or required for API behavior.
    return [
        {"name": "idx_validity_end", "keys": [("parsed.validity.end", ASCENDING)], "options": {"background": True}},
        {"name": "idx_validity_start", "keys": [("parsed.validity.start", ASCENDING)], "options": {"background": True}},
        {"name": "idx_validity_length", "keys": [("parsed.validity.length", ASCENDING)], "options": {"background": True}},
        {"name": "idx_key_algorithm_name", "keys": [("parsed.subject_key_info.key_algorithm.name", ASCENDING)], "options": {"background": True}},
        {"name": "idx_rsa_public_key_length", "keys": [("parsed.subject_key_info.rsa_public_key.length", ASCENDING)], "options": {"background": True}},
        {"name": "idx_ecdsa_public_key_length", "keys": [("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING)], "options": {"background": True}},
        {"name": "idx_signature_algo", "keys": [("parsed.signature_algorithm.name", ASCENDING)], "options": {"background": True}},
        {"name": "idx_zlint_errors", "keys": [("zlint.errors_present", ASCENDING)], "options": {"background": True}},
        {"name": "idx_zlint_warnings", "keys": [("zlint.warnings_present", ASCENDING)], "options": {"background": True}},
        {"name": "idx_self_signed", "keys": [("parsed.signature.self_signed", ASCENDING)], "options": {"background": True}},
        {"name": "idx_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
        {"name": "idx_validation_level", "keys": [("parsed.validation_level", ASCENDING)], "options": {"background": True}},
        {"name": "idx_cert_fingerprint_sha256", "keys": [("parsed.fingerprint_sha256", ASCENDING)], "options": {"background": True}},
        {"name": "idx_public_key_fingerprint", "keys": [("parsed.subject_key_info.fingerprint_sha256", ASCENDING)], "options": {"background": True}},
        {"name": "idx_domain", "keys": [("domain", ASCENDING)], "options": {"background": True}},
        {"name": "idx_issuer_country", "keys": [("parsed.issuer.country", ASCENDING)], "options": {"background": True}},
        {"name": "idx_issuer_org", "keys": [("parsed.issuer.organization", ASCENDING)], "options": {"background": True}},
        {"name": "idx_subject_dn", "keys": [("parsed.subject_dn", ASCENDING)], "options": {"background": True}},
        {"name": "idx_issuer_dn", "keys": [("parsed.issuer_dn", ASCENDING)], "options": {"background": True}},
        {"name": "idx_basic_constraints_ca", "keys": [("parsed.basic_constraints.ca", ASCENDING)], "options": {"background": True}},
        {"name": "idx_san_dns_names", "keys": [("parsed.extensions.subject_alt_name.dns_names", ASCENDING)], "options": {"background": True}},
        {"name": "idx_san_dns_names_50", "keys": [("parsed.extensions.subject_alt_name.dns_names.50", ASCENDING)], "options": {"background": True}},
        {
            "name": "idx_large_san_partial_domain",
            "keys": [("domain", ASCENDING)],
            "options": {
                "background": True,
                "partialFilterExpression": {
                    "parsed.extensions.subject_alt_name.dns_names.50": {"$exists": True}
                },
            },
        },
        {
            "name": "idx_algo_rsa_length",
            "keys": [
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.rsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_algo_ecdsa_length",
            "keys": [
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_issuer_org_validation_level",
            "keys": [
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.validation_level", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_cert_and_public_key_fingerprint",
            "keys": [
                ("parsed.fingerprint_sha256", ASCENDING),
                ("parsed.subject_key_info.fingerprint_sha256", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_validity_end",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.validity.end", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_zlint_errors",
            "keys": [
                ("scope", ASCENDING),
                ("zlint.errors_present", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_zlint_warnings",
            "keys": [
                ("scope", ASCENDING),
                ("zlint.warnings_present", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_id",
            "keys": [
                ("scope", ASCENDING),
                ("_id", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_validity_start",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.validity.start", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_validity_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.validity.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_algo_rsa_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.rsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_rsa_public_key_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.subject_key_info.rsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_algo_ecdsa_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_ecdsa_public_key_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_issuer_org",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_issuer_country",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.issuer.country", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_issuer_validation",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.validation_level", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_basic_constraints_ca",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.basic_constraints.ca", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_ca_ranking_scan",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.basic_constraints.ca", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.fingerprint_sha256", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_ca_ranking_scan",
            "keys": [
                ("parsed.basic_constraints.ca", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.fingerprint_sha256", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_is_leaf",
            "keys": [("is_leaf", ASCENDING)],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_signature_algo",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.signature_algorithm.name", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_self_signed",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.signature.self_signed", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_public_key_fingerprint",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.subject_key_info.fingerprint_sha256", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_domain",
            "keys": [
                ("scope", ASCENDING),
                ("domain", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_san_dns_names_50",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.extensions.subject_alt_name.dns_names.50", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_large_san_partial_id",
            "keys": [
                ("scope", ASCENDING),
                ("_id", ASCENDING),
            ],
            "options": {
                "background": True,
                "partialFilterExpression": {
                    "parsed.extensions.subject_alt_name.dns_names.50": {"$exists": True}
                },
            },
        },
         {
            "name": "idx_issuer_org_algo_rsa_length",
            "keys": [
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.rsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },  
         {
            "name": "idx_issuer_org_algo_ecdsa_length",
            "keys": [
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_issuer_algo_rsa_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.rsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
        {
            "name": "idx_scope_issuer_algo_ecdsa_length",
            "keys": [
                ("scope", ASCENDING),
                ("parsed.issuer.organization", ASCENDING),
                ("parsed.subject_key_info.key_algorithm.name", ASCENDING),
                ("parsed.subject_key_info.ecdsa_public_key.length", ASCENDING),
            ],
            "options": {"background": True},
        },
    ]


def build_results_indexes():
    return {
        "ca-analysis": [
            {"name": "idx_ca_analysis_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
            {"name": "idx_ca_analysis_computed_at", "keys": [("computed_at", ASCENDING)], "options": {"background": True}},
            {"name": "idx_ca_analysis_ca_rank", "keys": [("ca-list.rank", ASCENDING)], "options": {"background": True}},
            {"name": "idx_ca_analysis_ca_name", "keys": [("ca-list.name", ASCENDING)], "options": {"background": True}},
            {"name": "idx_ca_analysis_ca_score_rank", "keys": [("ca-list.scoreRank", ASCENDING)], "options": {"background": True}},
            {"name": "idx_ca_analysis_ca_score", "keys": [("ca-list.score", DESCENDING)], "options": {"background": True}},
        ],
        "san-analysis": [
            {"name": "idx_san_analysis_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
            {"name": "idx_san_analysis_computed_at", "keys": [("computed_at", ASCENDING)], "options": {"background": True}},
            {"name": "idx_san_analysis_bucket", "keys": [("bucket_groups.bucket", ASCENDING)], "options": {"background": True}},
            {"name": "idx_san_analysis_tld", "keys": [("tlds.tld", ASCENDING)], "options": {"background": True}},
        ],
        "signature-and-hash": [
            {"name": "idx_signature_hash_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
            {"name": "idx_signature_hash_computedAt", "keys": [("computedAt", ASCENDING)], "options": {"background": True}},
            {"name": "idx_signature_hash_trend_granularity", "keys": [("hash_trends_granularity", ASCENDING)], "options": {"background": True}},
            {"name": "idx_signature_hash_trend_months", "keys": [("hash_trends_months", ASCENDING)], "options": {"background": True}},
            {"name": "idx_signature_hash_issuer", "keys": [("issuer-algo-matrix.issuer", ASCENDING)], "options": {"background": True}},
            {"name": "idx_signature_hash_algo", "keys": [("issuer-algo-matrix.algorithm_list.algorithm", ASCENDING)], "options": {"background": True}},

        ],
        "validity-analysis": [
            {"name": "idx_validity_analysis_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
            {"name": "idx_validity_analysis_computedAt", "keys": [("computedAt", ASCENDING)], "options": {"background": True}},
        ],
        "geographic-distribution": [
            {"name": "idx_geo_distribution_scope", "keys": [("scope", ASCENDING)], "options": {"background": True}},
            {"name": "idx_geo_distribution_computed_at", "keys": [("computed_at", ASCENDING)], "options": {"background": True}},
            {"name": "idx_geo_distribution_country_rank", "keys": [("countries.rank", ASCENDING)], "options": {"background": True}},
            {"name": "idx_geo_distribution_country_count", "keys": [("countries.count", ASCENDING)], "options": {"background": True}},
            {"name": "idx_geo_distribution_country_name", "keys": [("countries.name", ASCENDING)], "options": {"background": True}},
        ],
        "shared-keys-detailed": [
            {"name": "idx_shared_keys_scope_doc_type", "keys": [("scope", ASCENDING), ("doc_type", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_scope_public_key_hash", "keys": [("scope", ASCENDING), ("public_key_hash", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_certificate_count", "keys": [("certificate_count", DESCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_total_sans", "keys": [("total_sans", DESCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_risk_level", "keys": [("risk_level", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_key_type", "keys": [("key_type", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_issuer_count", "keys": [("issuer_count", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_cert_domain", "keys": [("certificates.domain", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_issuer_org", "keys": [("issuers.organization", ASCENDING)], "options": {"background": True}},
            {"name": "idx_shared_keys_computed_at", "keys": [("computed_at", DESCENDING)], "options": {"background": True}},
        ],
    }


def create_indexes(collection, index_specs, dry_run=False, prefix=""):
    for spec in index_specs:
        name = spec["name"]
        keys = spec["keys"]
        options = spec.get("options", {})

        if dry_run:
            print(f"  [DRY] {prefix}{name} -> {keys}")
            continue

        try:
            created_name = create_index_if_missing(collection, keys, name=name, **options)
            print(f"  Created/reused {prefix}{created_name or name}")
        except Exception as exc:
            print(f"  Failed {prefix}{name}: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Create indexes across databases")
    parser.add_argument("--dbs", nargs="*", help="Database names (space-separated)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to databases.json")
    parser.add_argument("--collection", default="certificates", help="Collection name")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without creating indexes")
    args = parser.parse_args()

    if args.dbs:
        entries = [{"main": db_name, "results": f"{db_name}-results"} for db_name in args.dbs]
    else:
        entries = load_db_entries(args.config)

    if not entries:
        raise SystemExit("No databases provided")

    client = MongoClient("mongodb://localhost:27017/")
    source_index_specs = build_source_indexes()
    results_index_specs = build_results_indexes()

    for entry in entries:
        main_db = entry["main"]
        results_db = entry["results"]

        print(f"\n==> Source database: {main_db}")
        create_indexes(
            client[main_db][args.collection],
            source_index_specs,
            dry_run=args.dry_run,
        )

        print(f"\n==> Results database: {results_db}")
        for collection_name, specs in results_index_specs.items():
            print(f"  Collection: {collection_name}")
            create_indexes(
                client[results_db][collection_name],
                specs,
                dry_run=args.dry_run,
                prefix=f"{collection_name}.",
            )

    client.close()


if __name__ == "__main__":
    main()
