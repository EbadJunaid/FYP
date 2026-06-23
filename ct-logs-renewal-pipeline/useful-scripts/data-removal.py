"""
SSL Certificate Database Maintenance Script
============================================
Performs the following operations on your MongoDB SSL certificate collection:
  1. Remove 'raw' attribute from all documents (optional)
  2. Create 'scope' attribute (TLD extraction) for all documents (optional)
  3. Remove duplicate certificates based on parsed.fingerprint_sha256 (optional)
"""

from pymongo import MongoClient, UpdateMany
from pymongo.errors import ConnectionFailure, OperationFailure
from collections import defaultdict
import sys

# ──────────────────────────────────────────────
#  CONFIGURATION — update these before running
# ──────────────────────────────────────────────
MONGO_URI        = "mongodb://localhost:27017"   # your MongoDB connection URI
DATABASE_NAME    = "hugging-face-792k"          # your database name
COLLECTION_NAME  = "certificates"        # your collection name
# ──────────────────────────────────────────────


def get_collection():
    """Connect to MongoDB and return the collection."""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.admin.command("ping")
        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]
        print(f"\n✅ Connected to MongoDB — Database: '{DATABASE_NAME}' | Collection: '{COLLECTION_NAME}'")
        return collection
    except ConnectionFailure as e:
        print(f"\n❌ Could not connect to MongoDB: {e}")
        sys.exit(1)


def ask_yes_no(prompt: str) -> bool:
    """Ask a yes/no question and return True for yes, False for no."""
    while True:
        answer = input(f"\n{prompt} [yes/no]: ").strip().lower()
        if answer in ("yes", "y"):
            return True
        elif answer in ("no", "n"):
            return False
        else:
            print("   Please type 'yes' or 'no'.")


def separator():
    print("\n" + "=" * 60)


# ──────────────────────────────────────────────
#  STEP 1 — Remove 'raw' attribute
# ──────────────────────────────────────────────
def step1_remove_raw(collection):
    separator()
    print("STEP 1 — Checking for 'raw' attribute")

    count_with_raw = collection.count_documents({"raw": {"$exists": True}})

    if count_with_raw == 0:
        print("   ℹ️  'raw' attribute does not exist in any document. Skipping.")
        return

    print(f"   ⚠️  'raw' attribute found in {count_with_raw:,} document(s).")

    if not ask_yes_no("   Can I delete the 'raw' attribute from all documents?"):
        print("   ⏭️  Skipping 'raw' deletion.")
        return

    print("   🔄 Deleting 'raw' attribute from all documents...")

    result = collection.update_many(
        {"raw": {"$exists": True}},
        {"$unset": {"raw": ""}}
    )

    print(f"   ✅ Done. 'raw' removed from {result.modified_count:,} document(s).")


# ──────────────────────────────────────────────
#  STEP 2 — Create 'scope' attribute (TLD)
# ──────────────────────────────────────────────
def extract_tld(domain: str) -> str:
    """
    Extract the TLD (last part) from a domain name.
    Examples:
        example.com      → com
        apple.co.uk      → uk
        test.example.org → org
    """
    if not domain:
        return ""
    domain = domain.strip().lstrip("*").lstrip(".")  # handle wildcard domains
    parts = domain.split(".")
    if len(parts) >= 1:
        return parts[-1].lower()
    return ""


def step2_create_scope(collection):
    separator()
    print("STEP 2 — Checking for 'scope' attribute")

    count_without_scope = collection.count_documents({"scope": {"$exists": False}})
    count_total         = collection.count_documents({})

    if count_without_scope == 0:
        print("   ℹ️  'scope' attribute already exists in all documents. Skipping.")
        return

    print(f"   ℹ️  'scope' attribute is missing in {count_without_scope:,} of {count_total:,} document(s).")

    if not ask_yes_no("   Can I create the 'scope' attribute (TLD) for all documents?"):
        print("   ⏭️  Skipping 'scope' creation.")
        return

    print("   🔄 Extracting TLDs and writing 'scope' for all documents...")

    # Fetch only _id and domain fields to keep memory usage low
    cursor = collection.find(
        {"scope": {"$exists": False}},
        {"_id": 1, "domain": 1}
    )

    bulk_ops      = []
    BATCH_SIZE    = 1000
    total_updated = 0
    total_skipped = 0

    for doc in cursor:
        domain = doc.get("domain", "")
        tld    = extract_tld(domain)

        if not tld:
            total_skipped += 1
            continue

        bulk_ops.append(
            UpdateMany(
                {"_id": doc["_id"]},
                {"$set": {"scope": tld}}
            )
        )

        # Flush in batches to avoid memory buildup
        if len(bulk_ops) >= BATCH_SIZE:
            result = collection.bulk_write(bulk_ops)
            total_updated += result.modified_count
            bulk_ops = []

    # Flush remaining
    if bulk_ops:
        result = collection.bulk_write(bulk_ops)
        total_updated += result.modified_count

    print(f"   ✅ Done. 'scope' created for {total_updated:,} document(s).")
    if total_skipped > 0:
        print(f"   ⚠️  {total_skipped:,} document(s) skipped — missing or unparseable 'domain' field.")


# ──────────────────────────────────────────────
#  STEP 3 — Remove duplicate certificates
# ──────────────────────────────────────────────
def find_duplicates(collection):
    """
    Returns a dict:
      { fingerprint_sha256: [list of _id values] }
    Only includes fingerprints that appear more than once.
    """
    pipeline = [
        {
            "$match": {
                "parsed.fingerprint_sha256": {"$exists": True, "$ne": None}
            }
        },
        {
            "$group": {
                "_id":  "$parsed.fingerprint_sha256",
                "ids":  {"$push": "$_id"},
                "count": {"$sum": 1}
            }
        },
        {
            "$match": {"count": {"$gt": 1}}
        }
    ]

    duplicates = {}
    for doc in collection.aggregate(pipeline, allowDiskUse=True):
        duplicates[doc["_id"]] = doc["ids"]

    return duplicates


def step3_remove_duplicates(collection):
    separator()
    print("STEP 3 — Duplicate Certificate Removal")
    print("   Based on: parsed.fingerprint_sha256")

    if not ask_yes_no("   Can I scan and remove duplicate certificates?"):
        print("\n   👋 Exiting. No changes were made in this step.")
        return

    print("\n   🔄 Scanning for duplicates (this may take a moment)...")
    duplicates = find_duplicates(collection)

    if not duplicates:
        print("   ✅ No duplicate certificates found. Collection is clean.")
        return

    # Summary numbers
    total_duplicate_groups = len(duplicates)
    total_docs_to_delete   = sum(len(ids) - 1 for ids in duplicates.values())  # keep 1 per group
    sample_fingerprints    = list(duplicates.keys())[:5]  # show up to 5 samples

    print(f"\n   📊 Duplicate Summary:")
    print(f"      • Unique fingerprints with duplicates : {total_duplicate_groups:,}")
    print(f"      • Total documents that would be deleted: {total_docs_to_delete:,}  (1 kept per fingerprint)")
    print(f"\n   🔍 Sample fingerprint_sha256 values of duplicate groups:")
    for fp in sample_fingerprints:
        count = len(duplicates[fp])
        print(f"      - {fp}  ({count} copies, {count - 1} will be deleted)")

    separator()
    print("   Choose an option:")
    print("      a) Just show me the count and samples (no deletion)")
    print("      b) Delete all duplicates now")
    print("      c) Cancel and exit")

    while True:
        choice = input("\n   Your choice [a/b/c]: ").strip().lower()
        if choice in ("a", "b", "c"):
            break
        print("   Please enter 'a', 'b', or 'c'.")

    # ── Option A — Dry run (already printed above, just confirm)
    if choice == "a":
        print("\n   ℹ️  Dry-run complete. Summary shown above. No documents were deleted.")
        print(f"      Total duplicates that WOULD be deleted: {total_docs_to_delete:,}")

    # ── Option B — Actual deletion
    elif choice == "b":
        print(f"\n   ⚠️  You are about to permanently delete {total_docs_to_delete:,} documents.")

        if not ask_yes_no("   Are you absolutely sure you want to proceed?"):
            print("   ❌ Deletion cancelled. No documents were deleted.")
            return

        print("   🔄 Deleting duplicates — keeping 1 document per fingerprint...")

        ids_to_delete = []
        for fingerprint, ids in duplicates.items():
            # Keep the first document, delete the rest
            ids_to_delete.extend(ids[1:])

            # Flush in batches of 1000 to avoid large in-memory lists
            if len(ids_to_delete) >= 1000:
                collection.delete_many({"_id": {"$in": ids_to_delete}})
                ids_to_delete = []

        # Flush remaining
        if ids_to_delete:
            collection.delete_many({"_id": {"$in": ids_to_delete}})

        print(f"   ✅ Done. {total_docs_to_delete:,} duplicate document(s) deleted.")
        print(f"   ✅ {total_duplicate_groups:,} unique certificate(s) retained.")

    # ── Option C — Cancel
    elif choice == "c":
        print("   👋 Cancelled. No documents were deleted.")


# ──────────────────────────────────────────────
#  MAIN
# ──────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  SSL Certificate Database Maintenance Script")
    print("=" * 60)

    collection = get_collection()

    step1_remove_raw(collection)
    step2_create_scope(collection)
    step3_remove_duplicates(collection)

    separator()
    print("\n✅ All steps completed. Goodbye!\n")


if __name__ == "__main__":
    main()