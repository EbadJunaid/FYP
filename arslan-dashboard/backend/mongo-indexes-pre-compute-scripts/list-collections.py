#!/usr/bin/env python3
"""
List all collections in tranco-latest-8-lakh-results database
"""
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['tranco-latest-8-lakh-results']

print("Collections in tranco-latest-8-lakh-results:")
print("=" * 70)
for collection in sorted(db.list_collection_names()):
    count = db[collection].count_documents({})
    print(f"  {collection.ljust(40)} - {count:,} documents")
print("=" * 70)
