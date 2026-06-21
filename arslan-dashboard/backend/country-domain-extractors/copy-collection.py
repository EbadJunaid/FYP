#!/usr/bin/env python3
"""
Copy Collection Between Databases
==================================
Copies all documents from source database/collection to target database/collection.
Memory-efficient batch processing with duplicate handling.
"""

from pymongo import MongoClient
from datetime import datetime

# Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017

SOURCE_DATABASE = 'arslan-v3'
SOURCE_COLLECTION = 'certificates'

TARGET_DATABASE = 'pakistani-domains'
TARGET_COLLECTION = 'certificates'

BATCH_SIZE = 10000  # Process 10k documents at a time

# ============================================================================

def copy_collection():
    """Copy all documents from source to target collection."""
    
    print("=" * 80)
    print("MONGODB COLLECTION COPY UTILITY")
    print("=" * 80)
    print()
    print(f"📤 Source: {SOURCE_DATABASE}.{SOURCE_COLLECTION}")
    print(f"📥 Target: {TARGET_DATABASE}.{TARGET_COLLECTION}")
    print()
    
    # Connect to MongoDB
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    
    source_db = client[SOURCE_DATABASE]
    source_coll = source_db[SOURCE_COLLECTION]
    
    target_db = client[TARGET_DATABASE]
    target_coll = target_db[TARGET_COLLECTION]
    
    # Get counts
    source_count = source_coll.count_documents({})
    target_count_before = target_coll.count_documents({})
    
    print(f"📊 Source documents: {source_count:,}")
    print(f"📊 Target documents (before): {target_count_before:,}")
    print()
    
    if source_count == 0:
        print("❌ Source collection is empty! Nothing to copy.")
        return
    
    print("=" * 80)
    print("STARTING COPY...")
    print("=" * 80)
    print()
    
    # Statistics
    processed = 0
    inserted = 0
    duplicates = 0
    errors = 0
    
    start_time = datetime.now()
    
    # Stream documents in batches
    cursor = source_coll.find({})
    batch = []
    
    for doc in cursor:
        batch.append(doc)
        
        # Process batch when full
        if len(batch) >= BATCH_SIZE:
            batch_inserted, batch_duplicates, batch_errors = insert_batch(
                target_coll, batch
            )
            
            processed += len(batch)
            inserted += batch_inserted
            duplicates += batch_duplicates
            errors += batch_errors
            
            # Progress update
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed / elapsed if elapsed > 0 else 0
            progress_pct = (processed / source_count * 100)
            
            print(f"⏳ Processed: {processed:,}/{source_count:,} ({progress_pct:.1f}%) | "
                  f"Inserted: {inserted:,} | Duplicates: {duplicates:,} | "
                  f"Rate: {rate:.0f}/sec")
            
            batch = []
    
    # Process remaining documents
    if batch:
        batch_inserted, batch_duplicates, batch_errors = insert_batch(
            target_coll, batch
        )
        
        processed += len(batch)
        inserted += batch_inserted
        duplicates += batch_duplicates
        errors += batch_errors
    
    # Final statistics
    elapsed_time = (datetime.now() - start_time).total_seconds()
    target_count_after = target_coll.count_documents({})
    
    print()
    print("=" * 80)
    print("COPY COMPLETE!")
    print("=" * 80)
    print()
    print(f"⏱️  Total Time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"📊 Documents Processed: {processed:,}")
    print(f"✅ Documents Inserted: {inserted:,}")
    print(f"⚠️  Duplicates Skipped: {duplicates:,}")
    if errors > 0:
        print(f"❌ Errors: {errors:,}")
    print()
    print(f"📈 Target collection size:")
    print(f"   Before: {target_count_before:,}")
    print(f"   After:  {target_count_after:,}")
    print(f"   Added:  {target_count_after - target_count_before:,}")
    print()
    print("=" * 80)
    print("✅ Collection copied successfully!")
    print("=" * 80)
    
    client.close()


def insert_batch(collection, documents):
    """
    Insert a batch of documents into collection.
    Returns: (inserted_count, duplicate_count, error_count)
    """
    if not documents:
        return 0, 0, 0
    
    try:
        # Try to insert all documents (will fail on duplicates)
        result = collection.insert_many(documents, ordered=False)
        return len(result.inserted_ids), 0, 0
        
    except Exception as e:
        error_str = str(e).lower()
        
        if 'duplicate key error' in error_str:
            # Parse how many were actually inserted
            # MongoDB inserts what it can before hitting duplicates
            inserted_count = 0
            duplicate_count = 0
            
            # Try to count from error message or re-query
            try:
                # Count successful inserts by checking writeErrors
                if hasattr(e, 'details'):
                    write_errors = e.details.get('writeErrors', [])
                    duplicate_count = len(write_errors)
                    inserted_count = len(documents) - duplicate_count
                else:
                    # Fallback: assume all were duplicates if we can't parse
                    duplicate_count = len(documents)
                    inserted_count = 0
            except:
                # If parsing fails, be conservative
                duplicate_count = len(documents)
                inserted_count = 0
            
            return inserted_count, duplicate_count, 0
        else:
            # Some other error
            print(f"⚠️  Error during insert: {e}")
            return 0, 0, len(documents)


# ============================================================================

if __name__ == "__main__":
    try:
        copy_collection()
    except KeyboardInterrupt:
        print("\n\n⚠️  Copy operation interrupted by user!")
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
