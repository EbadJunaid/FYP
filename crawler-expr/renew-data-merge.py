"""
sync_renew_to_main.py

Syncs certificate documents from `renew-database.certificates` into the main
`certificates` collection used by the dashboard. renew-database is always
fresh crawl output, so every document there is unconditionally the latest
version for that domain - no fingerprint comparison needed. Each document
is written via an upsert-by-domain whole-document overwrite: replaced if
the domain already exists in main, inserted if it doesn't.

Design notes (read this before changing batch sizes / removing checkpointing):
  - Matching/targeting is done via the existing unique index on `domain`.
  - Writes are done via bulk_write() of ReplaceOne(..., upsert=True)
    operations, ordered=False. Each ReplaceOne is itself atomic at the
    document level - that's MongoDB's own guarantee, not something we add.
    The batch as a whole is NOT atomic, and that's intentional: the job is
    idempotent (re-writing the same document twice is harmless), so partial
    progress is always safe to resume.
  - A checkpoint (last processed renew _id) is stored in a small collection
    in the MAIN database. It only advances after a batch's bulk_write
    succeeds, so a crash mid-run never causes a silently-skipped domain -
    you just rerun the script and it resumes right after the last
    successfully committed batch.
  - No delete+insert anywhere. Delete-then-insert is two non-atomic steps
    and creates a window where the dashboard could read a missing
    certificate; ReplaceOne avoids that entirely.
  - No pre-read of main before writing. Since every renew document is
    blindly overwritten regardless of content, there's nothing to compare,
    so each batch costs exactly one round trip (the bulk_write itself).
"""

import sys
import time
import signal
from datetime import datetime

from pymongo import MongoClient, ReplaceOne, ASCENDING
from pymongo.errors import BulkWriteError, PyMongoError

# -------------------- Configuration --------------------
CONFIG = {
    'MAIN_MONGODB_URL': "mongodb://localhost:27017",
    'MAIN_DB_NAME': "tranco-latest-8-lakh",
    'MAIN_CERTS_COLLECTION': "certificates",

    'RENEW_MONGODB_URL': "mongodb://localhost:27017",
    'RENEW_DB_NAME': "renew-database",
    'RENEW_CERTS_COLLECTION': "certificates",

    # Checkpoint is stored as a single document in this collection, inside
    # the MAIN database.
    'SYNC_META_COLLECTION': "sync_checkpoints",
    'CHECKPOINT_KEY': "renew_to_main_certificates",

    'BATCH_SIZE': 500,          # docs per bulk_write call
    'USE_CHECKPOINT': True,     # set False to force a full re-scan from start
}

# -------------------- Global State --------------------
stop_requested = False


def handle_sigint(signum, frame):
    global stop_requested
    if stop_requested:
        # second Ctrl+C -> exit immediately, no more graceful waiting
        print("\n[ABORT] Second interrupt received, exiting immediately.")
        sys.exit(1)
    print("\n[INTERRUPT] Stop requested. Finishing current batch, then exiting cleanly...")
    stop_requested = True


def log(tag, message):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] [{tag}] {message}")


# -------------------- Setup / Validation --------------------
def connect():
    log("INIT", "Connecting to MongoDB (main + renew)...")
    try:
        main_client = MongoClient(CONFIG['MAIN_MONGODB_URL'], serverSelectionTimeoutMS=5000)
        main_client.admin.command('ping')
        renew_client = MongoClient(CONFIG['RENEW_MONGODB_URL'], serverSelectionTimeoutMS=5000)
        renew_client.admin.command('ping')
    except Exception as e:
        log("FATAL", f"Could not connect to MongoDB: {e}")
        sys.exit(1)

    main_db = main_client[CONFIG['MAIN_DB_NAME']]
    renew_db = renew_client[CONFIG['RENEW_DB_NAME']]

    main_coll = main_db[CONFIG['MAIN_CERTS_COLLECTION']]
    renew_coll = renew_db[CONFIG['RENEW_CERTS_COLLECTION']]
    meta_coll = main_db[CONFIG['SYNC_META_COLLECTION']]

    # Sanity check: we rely on this index existing for the upsert-by-domain
    # writes to be fast (and unique, to avoid duplicate documents per domain).
    existing_indexes = main_coll.index_information()
    has_domain_index = any(
        idx.get('key') == [('domain', ASCENDING)] for idx in existing_indexes.values()
    )
    if not has_domain_index:
        log("WARN", "No index found on main.certificates.domain - writes will be slow "
                     "and duplicates won't be prevented. Expected one from the crawler's init_db() step.")
    else:
        log("INIT", "Confirmed unique index on main.certificates.domain.")

    log("INIT", "Connected successfully.")
    return main_coll, renew_coll, meta_coll


# -------------------- Checkpoint --------------------
def load_checkpoint(meta_coll):
    if not CONFIG['USE_CHECKPOINT']:
        return None
    doc = meta_coll.find_one({"_id": CONFIG['CHECKPOINT_KEY']})
    if doc and doc.get("last_id") is not None:
        log("INIT", f"Resuming from checkpoint, last processed _id = {doc['last_id']}")
        return doc["last_id"]
    log("INIT", "No checkpoint found, starting from the beginning.")
    return None


def save_checkpoint(meta_coll, last_id):
    if not CONFIG['USE_CHECKPOINT']:
        return
    meta_coll.update_one(
        {"_id": CONFIG['CHECKPOINT_KEY']},
        {"$set": {"last_id": last_id, "updated_at": datetime.now()}},
        upsert=True
    )


# -------------------- Core Sync Logic --------------------
def build_replacement(doc):
    """Strips _id so MongoDB keeps the existing _id on update, or generates
    a fresh one on insert. Whole-document overwrite, nothing else stripped."""
    return {k: v for k, v in doc.items() if k != "_id"}


def process_batch(main_coll, batch):
    """Blindly upserts every document in the batch by domain - no
    fingerprint comparison, no pre-read. Returns (new_count, overwritten_count)
    straight from MongoDB's own bulk_write result, or raises on a genuine
    write failure (caller decides whether to advance checkpoint)."""
    ops = [
        ReplaceOne({"domain": doc["domain"]}, build_replacement(doc), upsert=True)
        for doc in batch
    ]

    result = main_coll.bulk_write(ops, ordered=False)
    new_count = result.upserted_count
    overwritten_count = result.matched_count
    return new_count, overwritten_count


def sync():
    main_coll, renew_coll, meta_coll = connect()

    last_id = load_checkpoint(meta_coll)
    query_filter = {"_id": {"$gt": last_id}} if last_id is not None else {}

    total_remaining = renew_coll.count_documents(query_filter)
    log("INFO", f"{total_remaining} document(s) left to sync from renew-database.")

    if total_remaining == 0:
        log("DONE", "Nothing to sync. Exiting.")
        return

    cursor = renew_coll.find(query_filter).sort("_id", ASCENDING).batch_size(CONFIG['BATCH_SIZE'])

    batch = []
    total_new = 0
    total_overwritten = 0
    total_processed = 0
    batch_num = 0
    start_time = time.time()

    def flush(batch):
        nonlocal total_new, total_overwritten, total_processed, batch_num
        if not batch:
            return
        batch_num += 1
        try:
            n, o = process_batch(main_coll, batch)
        except BulkWriteError as bwe:
            log("ERROR", f"Batch {batch_num} failed during bulk_write: {bwe.details}")
            log("ERROR", "Checkpoint NOT advanced past this batch. Fix the issue and rerun; "
                          "the script will safely resume right before this batch.")
            sys.exit(1)
        except PyMongoError as e:
            log("ERROR", f"Batch {batch_num} failed: {e}")
            log("ERROR", "Checkpoint NOT advanced past this batch. Rerun is safe.")
            sys.exit(1)

        total_new += n
        total_overwritten += o
        total_processed += len(batch)

        last_doc_id = batch[-1]["_id"]
        save_checkpoint(meta_coll, last_doc_id)

        elapsed = time.time() - start_time
        speed = total_processed / elapsed if elapsed > 0 else 0
        pct = (total_processed / total_remaining) * 100 if total_remaining else 100
        eta_min = ((total_remaining - total_processed) / speed) / 60 if speed > 0 else 0

        log("PROGRESS",
            f"Batch {batch_num} | new={n} overwritten={o} | "
            f"{total_processed}/{total_remaining} ({pct:.1f}%) | "
            f"{speed:.1f} docs/sec | ETA {eta_min:.1f} min")

    for doc in cursor:
        batch.append(doc)
        if len(batch) >= CONFIG['BATCH_SIZE']:
            flush(batch)
            batch = []
            if stop_requested:
                log("INTERRUPT", "Stopping after completed batch as requested. "
                                  "Checkpoint is saved - rerun to resume.")
                cursor.close()
                return

    # final partial batch
    if batch and not stop_requested:
        flush(batch)

    elapsed = time.time() - start_time
    log("DONE",
        f"Sync complete in {elapsed:.1f}s | "
        f"new={total_new} overwritten={total_overwritten} | "
        f"total processed={total_processed}")


def main():
    signal.signal(signal.SIGINT, handle_sigint)
    print("=" * 60)
    print("      RENEW -> MAIN CERTIFICATE SYNC")
    print("=" * 60)
    sync()


if __name__ == "__main__":
    main()