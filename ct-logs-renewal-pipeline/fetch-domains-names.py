### This file is extracting all of the domains from the MongoDB collection and 
### writing them to a CSV file. It also checks for duplicates and optionally 
### creates a deduplicated CSV file. The script is designed to be memory-efficient
### by streaming data in batches and not loading everything into RAM at once.

#!/usr/bin/env python3

"""
extract_domains.py
==================
Production-level script to:
  1. Connect to a local MongoDB instance (MongoDB Compass / mongod)
  2. Stream all `domain` values from a collection directly to CSV
     — without loading them all into RAM
  3. Report duplicate domains (count + names)
  4. Optionally create a deduplicated CSV

Usage:
  python extract_domains.py

Dependencies:
  pip install pymongo
"""

import argparse
import csv
import json
# import logging       # ← LOGGING DISABLED: comment this back in if you re-enable the logging system
import sys
import time
from collections import defaultdict
from pathlib import Path

# ── Third-party ──────────────────────────────────────────────────────────────
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError
except ImportError:
    print("[FATAL] pymongo is not installed. Run:  pip install pymongo")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════
# CONFIGURATION — edit these values to match your setup
# ═══════════════════════════════════════════════════════════════════════════
_CONFIG_PATH = Path(__file__).resolve().parent.parent / "project-config.json"
with open(_CONFIG_PATH) as _f:
    _CONFIG_DATA = json.load(_f)["databases"][0]
_PROJECT_ROOT = _CONFIG_PATH.parent

MONGO_URI        = "mongodb://localhost:27017"   # Change if using auth: mongodb://user:pass@host:port
DATABASE_NAME    = _CONFIG_DATA["main"]          # ← replaced
COLLECTION_NAME  = "certificates"        # ← replace
DOMAIN_FIELD     = "domain"                      # top-level field in your documents

OUTPUT_CSV       = str(_PROJECT_ROOT / _CONFIG_DATA["csv_path"])
DEDUP_CSV        = "global-dataset-deduplicated.csv"    # written only if user confirms

BATCH_SIZE       = 1000    # cursor batch size — controls network round-trips
SERVER_TIMEOUT_MS = 5000   # ms to wait for MongoDB to respond on connect
# ═══════════════════════════════════════════════════════════════════════════


# ── Logging setup (DISABLED — comment back in to re-enable file logging) ──
# logging.basicConfig(
#     level=logging.DEBUG,
#     format="%(asctime)s  [%(levelname)-8s]  %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
#     handlers=[
#         logging.StreamHandler(sys.stdout),           # console
#         logging.FileHandler("extract_domains.log"),  # persistent log file
#     ],
# )
# log = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# STEP 1 — Connect
# ──────────────────────────────────────────────────────────────────────────
def get_collection():
    """Return a pymongo Collection handle after verifying connectivity."""
    print(f"[STEP 1/4] Connecting to MongoDB at {MONGO_URI} ...")
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=SERVER_TIMEOUT_MS,
        connectTimeoutMS=SERVER_TIMEOUT_MS,
    )
    try:
        # ping is the lightest way to confirm the server is reachable
        client.admin.command("ping")
        print("          ✓ Connected successfully.")
    except (ConnectionFailure, ServerSelectionTimeoutError) as exc:
        print(f"\n[FATAL] Cannot reach MongoDB: {exc}")
        print(
            "[FATAL] Ensure 'mongod' is running on localhost:27017 "
            "(or update MONGO_URI at the top of this script)."
        )
        sys.exit(1)

    db  = client[DATABASE_NAME]
    col = db[COLLECTION_NAME]
    print(f"          Using database={DATABASE_NAME!r}  collection={COLLECTION_NAME!r}")
    return col


# ──────────────────────────────────────────────────────────────────────────
# STEP 2 — Stream → CSV  +  build frequency map (no full-list in RAM)
# ──────────────────────────────────────────────────────────────────────────
def stream_to_csv(collection, output_path: str) -> tuple[int, dict]:
    """
    Iterate the collection with a server-side cursor in batches.
    Write each domain to CSV immediately — never holds all domains in memory.

    Returns
    -------
    total_written : int
        Total rows written to the CSV.
    freq : dict[str, int]
        Mapping of domain → occurrence count  (only for duplicate detection;
        stores counts, NOT domain strings — so memory stays O(unique domains)).
    """
    print(f"\n[STEP 2/4] Streaming domains → {output_path} ...")

    # Only project the field we need — saves network bandwidth
    cursor = collection.find(
        {},                          # no filter: all documents
        {DOMAIN_FIELD: 1, "_id": 0}, # projection: only domain field
        batch_size=BATCH_SIZE,
    )

    freq: dict[str, int] = defaultdict(int)
    total_written  = 0
    skipped_empty  = 0
    t_start        = time.perf_counter()
    last_log_at    = 0  # for progress printing every 10k rows

    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["index", "domain"])  # header

        for doc in cursor:
            raw = doc.get(DOMAIN_FIELD)

            # Skip documents that have no domain field or an empty value
            if not raw:
                skipped_empty += 1
                # Uncomment below to see every skipped doc in console:
                # print(f"  [SKIP] Missing/empty domain (total skipped: {skipped_empty})")
                continue

            domain = str(raw).strip().lower()  # normalise for dedup logic

            total_written += 1
            freq[domain] += 1

            writer.writerow([total_written, domain])

            # Progress heartbeat every 10 000 rows so you know it's alive
            if total_written - last_log_at >= 10_000:
                elapsed = time.perf_counter() - t_start
                rate    = total_written / elapsed if elapsed > 0 else 0
                print(
                    f"  [PROGRESS] {total_written:,} domains written  |  "
                    f"{rate:,.0f} docs/sec  |  {elapsed:.1f}s elapsed"
                )
                last_log_at = total_written

    elapsed = time.perf_counter() - t_start
    print(
        f"          ✓ Done: {total_written:,} domains written  |  "
        f"{elapsed:.1f}s total  |  {skipped_empty} skipped (no domain field)"
    )
    return total_written, freq


# ──────────────────────────────────────────────────────────────────────────
# STEP 3 — Duplicate analysis
# ──────────────────────────────────────────────────────────────────────────
def analyse_duplicates(freq: dict) -> list[tuple[str, int]]:
    """
    Given domain-frequency dict, return list of (domain, count) pairs
    where count > 1, sorted by count descending.
    """
    duplicates = [(d, c) for d, c in freq.items() if c > 1]
    duplicates.sort(key=lambda x: x[1], reverse=True)
    return duplicates


def report_duplicates(total_written: int, duplicates: list[tuple[str, int]]) -> None:
    """Print a human-readable duplicate report to stdout."""
    if not duplicates:
        print("\n✅  No duplicates found. All domains are unique.\n")
        return

    dup_domain_count = len(duplicates)
    dup_row_count    = sum(c - 1 for _, c in duplicates)  # extra rows above 1

    print("\n" + "═" * 60)
    print(f"  ⚠  DUPLICATES DETECTED")
    print("═" * 60)
    print(f"  Unique domains that appear more than once : {dup_domain_count}")
    print(f"  Extra (redundant) rows in the CSV        : {dup_row_count}")
    print(f"  Total rows written                       : {total_written}")
    print(f"  Rows a deduplicated CSV would have       : {total_written - dup_row_count}")
    print("─" * 60)
    print("  Duplicate domains (sorted by frequency):")
    print("─" * 60)

    # Show up to 50 duplicates on screen
    SCREEN_LIMIT = 50
    for i, (domain, count) in enumerate(duplicates, start=1):
        # log.debug("  [DUPLICATE #%d]  %s  →  appears %d times", i, domain, count)  # re-enable with logging
        if i <= SCREEN_LIMIT:
            print(f"    {i:>5}.  {domain}  ({count}×)")

    if dup_domain_count > SCREEN_LIMIT:
        print(f"\n    … and {dup_domain_count - SCREEN_LIMIT} more duplicates exist above.")

    print("═" * 60 + "\n")


# ──────────────────────────────────────────────────────────────────────────
# STEP 4 — Optional deduplication pass (stream original CSV, not MongoDB)
# ──────────────────────────────────────────────────────────────────────────
def write_deduplicated_csv(source_csv: str, dest_csv: str) -> int:
    """
    Read source_csv row-by-row (no full load into RAM) and write each domain
    only the first time it is seen.  Uses a set of already-seen domains —
    memory cost is O(unique domains × avg domain length), which is acceptable
    and far smaller than loading all records.

    Returns the number of unique rows written.
    """
    print(f"\n[STEP 4/4] Writing deduplicated CSV → {dest_csv} ...")

    seen: set[str] = set()
    new_index = 0

    with (
        open(source_csv, "r", newline="", encoding="utf-8") as src,
        open(dest_csv,   "w", newline="", encoding="utf-8") as dst,
    ):
        reader = csv.reader(src)
        writer = csv.writer(dst)

        header = next(reader, None)
        if header:
            writer.writerow(header)

        for row in reader:
            if len(row) < 2:
                continue
            domain = row[1].strip()
            if domain in seen:
                # Uncomment to see every skipped duplicate in console:
                # print(f"  [SKIP] Duplicate: {domain}")
                continue
            seen.add(domain)
            new_index += 1
            writer.writerow([new_index, domain])

            if new_index % 10_000 == 0:
                print(f"  [PROGRESS] {new_index:,} unique rows written ...")

    print(f"          ✓ Done: {new_index:,} unique domains → '{dest_csv}'")
    return new_index


# ──────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────
def main() -> None:
    # --- ADDED: Command Line Argument Parsing ---
    parser = argparse.ArgumentParser(description="Extract domains to CSV.")
    parser.add_argument(
        "--dedup", 
        choices=["y", "n"], 
        help="Bypass the user prompt by auto-answering the deduplication question (y/n)."
    )
    args = parser.parse_args()
    # --------------------------------------------

    print("═" * 60)
    print("  Domain Extraction Script  —  START")
    print("═" * 60)

    # 1. Connect
    collection = get_collection()

    try:
        approx_count = collection.estimated_document_count()
        print(f"          Estimated documents in collection: {approx_count:,}")
    except OperationFailure as exc:
        print(f"  [WARN] Could not estimate document count: {exc}")

    # 2. Stream → CSV
    total_written, freq = stream_to_csv(collection, OUTPUT_CSV)

    if total_written == 0:
        print("\n[WARN] No domains were written.")
        return

    # 3. Analyse duplicates
    print("\n[STEP 3/4] Analysing duplicates ...")
    duplicates = analyse_duplicates(freq)
    report_duplicates(total_written, duplicates)

    # 4. Ask user about deduplication (UPDATED LOGIC)
    if duplicates:
        # Check if the CLI argument was provided first
        if args.dedup:
            answer = args.dedup
            print(f"  [AUTO] Deduplication answer provided via command line: '{answer}'")
        else:
            # Fall back to interactive prompt if ran manually without flags
            try:
                answer = input(
                    "Do you want to create a duplicate-free CSV file? [y/N]: "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                answer = "n"

        if answer in ("y", "yes"):
            unique_count = write_deduplicated_csv(OUTPUT_CSV, DEDUP_CSV)
            print(f"\n✅  Deduplicated CSV saved → '{DEDUP_CSV}'  ({unique_count:,} unique domains)\n")
        else:
            print("\nℹ  Skipped deduplication. Original CSV kept as-is.\n")
    else:
        print("  No duplicates — deduplication step skipped.")

    print("═" * 60)
    print("  Script finished successfully.")
    print("═" * 60)


if __name__ == "__main__":
    main()