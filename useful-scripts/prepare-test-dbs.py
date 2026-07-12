#!/usr/bin/env python3
"""
Prepare small test databases by copying the first N certificates.

For examples :
- tranco-latest-8-lakh -> test-api-tranco
- pakistani-domains -> test-api-pakistani

Usage:
  python3 prepare-test-dbs.py
  python3 prepare-test-dbs.py --limit 1000
  python3 prepare-test-dbs.py --pair tranco-latest-8-lakh=test-api-tranco --pair pakistani-domains=test-api-pakistani
  python3 prepare-test-dbs.py --no-drop
"""

import argparse
from pymongo import MongoClient

DEFAULT_PAIRS = [
    ("hugging-face-700k", "hahksk"),
]


def parse_pairs(pair_args):
    pairs = []
    for raw in pair_args:
        if "=" not in raw:
            raise ValueError(f"Invalid pair '{raw}'. Use source=target.")
        source, target = raw.split("=", 1)
        source = source.strip()
        target = target.strip()
        if not source or not target:
            raise ValueError(f"Invalid pair '{raw}'. Use source=target.")
        pairs.append((source, target))
    return pairs


def copy_first_n(client, source_db_name, target_db_name, limit, drop_target):
    source_db = client[source_db_name]
    target_db = client[target_db_name]

    source_collection = source_db["certificates"]
    target_collection = target_db["certificates"]

    if drop_target:
        target_db.drop_collection("certificates")

    cursor = source_collection.find({}).sort("_id", 1).limit(limit)

    batch = []
    inserted = 0
    batch_size = 200

    for doc in cursor:
        batch.append(doc)
        if len(batch) >= batch_size:
            result = target_collection.insert_many(batch, ordered=False)
            inserted += len(result.inserted_ids)
            batch = []

    if batch:
        result = target_collection.insert_many(batch, ordered=False)
        inserted += len(result.inserted_ids)

    return inserted


def main():
    parser = argparse.ArgumentParser(description="Create small test databases")
    parser.add_argument("--limit", type=int, default=1000, help="Number of certificates to copy")
    parser.add_argument(
        "--pair",
        action="append",
        default=[],
        help="Source=Target pair (can be repeated)",
    )
    parser.add_argument("--no-drop", action="store_true", help="Do not drop target certificates collection")

    args = parser.parse_args()

    pairs = parse_pairs(args.pair) if args.pair else DEFAULT_PAIRS
    drop_target = not args.no_drop

    client = MongoClient("mongodb://localhost:27017/")

    for source_db, target_db in pairs:
        print(f"Copying first {args.limit} certificates: {source_db} -> {target_db}")
        inserted = copy_first_n(client, source_db, target_db, args.limit, drop_target)
        print(f"  Inserted {inserted} documents into {target_db}.certificates")

    client.close()


if __name__ == "__main__":
    main()
