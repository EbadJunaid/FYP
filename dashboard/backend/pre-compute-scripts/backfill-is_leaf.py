#!/usr/bin/env python3
"""
One-time backfill: add 'is_leaf' boolean to every document in
<db>.certificates, then create an index on the field.

Usage:
  python backfill-is_leaf.py --dbs hugging-face-400k
  python backfill-is_leaf.py --dbs hugging-face-400k hugging-face-792k
"""

import argparse
import sys
from datetime import datetime

from pymongo import MongoClient, UpdateOne
from pymongo.errors import DuplicateKeyError


MONGO_URI = "mongodb://localhost:27017/"

# Matches LEAF_EXPR from generic-compute-ca-stats.py
IS_LEAF_EXPR = {
    "$and": [
        {
            "$not": {
                "$and": [
                    {"$ne": [{"$ifNull": ["$parsed.subject_dn", ""]}, ""]},
                    {"$eq": ["$parsed.subject_dn", "$parsed.issuer_dn"]},
                ]
            }
        },
        {"$not": {"$eq": ["$parsed.basic_constraints.ca", True]}},
    ]
}


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def backfill_database(client, db_name):
    collection = client[db_name]["certificates"]
    total = collection.estimated_document_count()
    log(f"{db_name}.certificates: {total:,} documents")

    # Use an aggregation pipeline update — computes is_leaf server-side,
    # touches no Python per-doc logic.
    log(f"  Setting is_leaf on all documents via aggregation pipeline...")
    result = collection.update_many(
        {},
        [{"$set": {"is_leaf": IS_LEAF_EXPR}}],
    )
    log(f"  Matched: {result.matched_count:,}, Modified: {result.modified_count:,}")

    # Create index (sparse = False so leaf-filtered queries can use it)
    log(f"  Creating index on is_leaf...")
    index_name = "idx_is_leaf"
    existing = {idx["name"] for idx in collection.list_indexes()}
    if index_name not in existing:
        collection.create_index("is_leaf", name=index_name, background=True)
        log(f"  Created index '{index_name}'")
    else:
        log(f"  Index '{index_name}' already exists")

    # Verify a few docs
    leaf_count = collection.count_documents({"is_leaf": True})
    non_leaf_count = collection.count_documents({"is_leaf": False})
    null_count = collection.count_documents({"is_leaf": {"$exists": False}})
    log(f"  leaf={leaf_count:,}  non-leaf={non_leaf_count:,}  missing={null_count:,}")
    log(f"  Done")


def main():
    parser = argparse.ArgumentParser(description="Backfill is_leaf field")
    parser.add_argument("--dbs", nargs="+", required=True, help="Database names")
    args = parser.parse_args()

    client = MongoClient(MONGO_URI)
    for db_name in args.dbs:
        backfill_database(client, db_name)
    client.close()


if __name__ == "__main__":
    main()
