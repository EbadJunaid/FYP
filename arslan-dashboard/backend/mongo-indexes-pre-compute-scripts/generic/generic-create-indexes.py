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
from pymongo import MongoClient, ASCENDING, TEXT

DEFAULT_CONFIG = os.path.join(os.path.dirname(__file__), "databases.json")


def load_db_names(config_path):
    with open(config_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        return _normalize_db_list(data)

    if isinstance(data, dict):
        if "databases" in data:
            return _normalize_db_list(data["databases"])

    raise ValueError("Unsupported databases.json format")


def _normalize_db_list(items):
    dbs = []
    for item in items:
        if isinstance(item, str):
            dbs.append(item)
        elif isinstance(item, dict):
            main_db = item.get("main") or item.get("db") or item.get("name")
            if main_db:
                dbs.append(main_db)
        else:
            raise ValueError("Unsupported database entry in list")
    return dbs


def build_indexes():
    # Indexes referenced by API queries or required for API behavior.
    return [
        {"name": "idx_validity_end", "keys": [("parsed.validity.end", ASCENDING)], "options": {"background": True}},
        {"name": "idx_zlint_errors", "keys": [("zlint.errors_present", ASCENDING)], "options": {"background": True}},
        {"name": "idx_issuer_org_primary", "keys": [("parsed.issuer_org_primary", ASCENDING)], "options": {"background": True}},
        {
            "name": "idx_text_search",
            "keys": [("domain", TEXT), ("parsed.subject.common_name", TEXT)],
            "options": {
                "default_language": "english",
                "weights": {"domain": 10, "parsed.subject.common_name": 5},
            },
        },
        {"name": "idx_issuer_org", "keys": [("parsed.issuer.organization", ASCENDING)], "options": {"background": True}},
        {"name": "idx_signature_algo", "keys": [("parsed.signature_algorithm.name", ASCENDING)], "options": {"background": True}},
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
        {"name": "idx_self_signed", "keys": [("parsed.signature.self_signed", ASCENDING)], "options": {"background": True}},
        {"name": "idx_issuer_country", "keys": [("parsed.issuer.country", ASCENDING)], "options": {"background": True}},
        {"name": "idx_san_dns_names", "keys": [("parsed.extensions.subject_alt_name.dns_names", ASCENDING)], "options": {"background": True}},
        {"name": "idx_validity_length", "keys": [("parsed.validity.length", ASCENDING)], "options": {"background": True}},
        {"name": "idx_public_key_fingerprint", "keys": [("parsed.subject_key_info.fingerprint_sha256", ASCENDING)], "options": {"background": True}},
    ]


def main():
    parser = argparse.ArgumentParser(description="Create indexes across databases")
    parser.add_argument("--dbs", nargs="*", help="Database names (space-separated)")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Path to databases.json")
    parser.add_argument("--collection", default="certificates", help="Collection name")
    parser.add_argument("--dry-run", action="store_true", help="Print actions without creating indexes")
    args = parser.parse_args()

    if args.dbs:
        db_names = args.dbs
    else:
        db_names = load_db_names(args.config)

    if not db_names:
        raise SystemExit("No databases provided")

    client = MongoClient("mongodb://localhost:27017/")
    index_specs = build_indexes()

    for db_name in db_names:
        print(f"\n==> Database: {db_name}")
        collection = client[db_name][args.collection]
        for spec in index_specs:
            name = spec["name"]
            keys = spec["keys"]
            options = spec.get("options", {})

            if args.dry_run:
                print(f"  [DRY] {name} -> {keys}")
                continue

            try:
                collection.create_index(keys, name=name, **options)
                print(f"  Created {name}")
            except Exception as exc:
                print(f"  Failed {name}: {exc}")

    client.close()


if __name__ == "__main__":
    main()
