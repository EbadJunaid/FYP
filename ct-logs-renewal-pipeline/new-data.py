#!/usr/bin/env python3
"""
pipeline.py — Senior-grade orchestration script

Pipeline steps:
  1. Connect to MongoDB "go-server" / "certificates"
  2. Extract up to 1,500 domains (found=false), first domain per doc,
     strip leading "www.", write to new-data.csv
  3. Drop "certificates" in "go-server"
  4. Launch  crawler-args.py  as a subprocess and wait for it to finish
  5. Append documents from "new-dataset"/"certificates" → "hugging-face-792k"/"certificates"
     Track exactly which domains were successfully inserted using
     parsed.fingerprint_sha256 (unique index) for duplicate detection.
  6. Append ONLY those confirmed-inserted domains into global-dataset.csv
"""

import csv
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

from pymongo import MongoClient, InsertOne
from pymongo.errors import BulkWriteError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
MONGO_URL          = "mongodb://localhost:27017"
SOURCE_DB          = "go-server"
SOURCE_COLLECTION  = "certificates"

NEW_CSV            = Path("new-data.csv")
GLOBAL_CSV         = Path("global-dataset.csv")

TARGET_DB          = "hugging-face-792k"
TARGET_COLLECTION  = "certificates"

NEW_DATASET_DB         = "new-data"
NEW_DATASET_COLLECTION = "certificates"

MAIN_SCRIPT        = "../ssl-certificates-crawler/domain-based-crawler/src/crawler-args.py"
MAIN_SCRIPT_MONGO  = "mongodb://localhost:27017"
MAIN_SCRIPT_DB     = "new-data"
MAIN_STATUS_COL    = "domain_status"
MAIN_CERTS_COL     = "certificates"

EXTRACT_LIMIT      = 1_500
BATCH_SIZE_CSV     = 5_000
BATCH_SIZE_MONGO   = 1_000

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1 & 2 — Extract domains → new-data.csv
# ═══════════════════════════════════════════════════════════════════════════

def clean_domain(raw: str) -> str:
    d = raw.strip()
    if d.startswith("[") and "](" in d:
        d = d[1 : d.index("](")]
    for prefix in ("https://", "http://"):
        if d.lower().startswith(prefix):
            d = d[len(prefix):]
    if d.lower().startswith("www."):
        d = d[4:]
    return d.rstrip("/")


def extract_domains_to_csv(client: MongoClient) -> int:
    log.info("STEP 1/2 — Extracting domains from MongoDB …")

    col = client[SOURCE_DB][SOURCE_COLLECTION]

    cursor = (
        col.find(
            {"found": False},
            {"domains": {"$slice": 1}, "_id": 0},
        )
        .batch_size(BATCH_SIZE_CSV)
        .limit(EXTRACT_LIMIT)
    )

    written = 0
    buffer  = []

    with NEW_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["index", "domain"])

        for doc in cursor:
            domains = doc.get("domains")
            if not domains:
                continue
            domain = clean_domain(domains[0])
            if not domain:
                continue
            written += 1
            buffer.append([written, domain])
            if len(buffer) >= BATCH_SIZE_CSV:
                writer.writerows(buffer)
                buffer.clear()
                if written % 100_000 == 0:
                    log.info("  … %d domains written so far", written)

        if buffer:
            writer.writerows(buffer)

    log.info("STEP 2 done — %d rows written to %s", written, NEW_CSV)
    return written


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3 — Drop source collection
# ═══════════════════════════════════════════════════════════════════════════

# def rename_collection(client: MongoClient) -> None:
#     log.info("STEP 3 — Dropping '%s' in db '%s' …", SOURCE_COLLECTION, SOURCE_DB)
#     client[SOURCE_DB][SOURCE_COLLECTION].drop()
#     log.info("  Drop complete.")




def rename_collection(client: MongoClient) -> None:
    collections = client[SOURCE_DB].list_collection_names()
    log.info(
        "STEP 3 — Dropping entire database '%s' (collections found: %s) …",
        SOURCE_DB,
        collections if collections else "none",
    )
    client.drop_database(SOURCE_DB)
    log.info("  Database '%s' dropped completely.", SOURCE_DB)

# ═══════════════════════════════════════════════════════════════════════════
# STEP 4 — Launch crawler-args.py and wait
# ═══════════════════════════════════════════════════════════════════════════

def run_main_script() -> None:
    log.info("STEP 4 — Launching %s …", MAIN_SCRIPT)

    cmd = [
        sys.executable,
        MAIN_SCRIPT,
        "--mongodb-url",             MAIN_SCRIPT_MONGO,
        "--db-name",                 MAIN_SCRIPT_DB,
        "--status-collection",       MAIN_STATUS_COL,
        "--certificates-collection", MAIN_CERTS_COL,
        "--csv-file",                str(NEW_CSV.resolve()),
    ]

    log.info("  Command: %s", " ".join(cmd))
    t0     = time.monotonic()
    ## below is before the issue 
    #result = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr, text=True)
    ## below is after the issue
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if result.stdout:
        log.info("Crawler output:\n%s", result.stdout)
    elapsed = time.monotonic() - t0

    if result.returncode != 0:
        raise RuntimeError(
            f"{MAIN_SCRIPT} exited with code {result.returncode} after {elapsed:.1f}s"
        )

    log.info("STEP 4 done — crawler finished in %.1fs", elapsed)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 5 — Append certificates with full consistency tracking
# ═══════════════════════════════════════════════════════════════════════════

def append_certificates(client: MongoClient) -> set:
    """
    Bulk-insert documents from new-dataset/certificates → hugging-face-792k/certificates.

    How duplicate detection works:
    ─────────────────────────────
    The destination collection has a UNIQUE INDEX on `parsed.fingerprint_sha256`.
    When we try to insert a document whose fingerprint already exists,
    MongoDB rejects it with a duplicate-key error and tells us the EXACT
    position (index) of that document inside our batch.

    We keep a parallel list of domain names in the same order as the batch.
    After each bulk_write:
      - If ALL succeeded  → every domain in the batch is confirmed inserted.
      - If SOME failed    → MongoDB's writeErrors[].index tells us which
                            positions failed.  We subtract those from the
                            batch and only the remaining positions are confirmed.

    This gives us a 100% accurate set of successfully inserted domains
    which is then used to drive CSV appending — guaranteeing that exactly
    the same domains that made it into MongoDB are written into global-dataset.csv.
    """
    log.info("STEP 5 — Copying certificates '%s' → '%s' …", NEW_DATASET_DB, TARGET_DB)

    src_col = client[NEW_DATASET_DB][NEW_DATASET_COLLECTION]
    dst_col = client[TARGET_DB][TARGET_COLLECTION]

    total = src_col.count_documents({})
    log.info("  Source document count: %d", total)

    cursor = src_col.find({}).batch_size(BATCH_SIZE_MONGO)

    # batch_domains  — domain name for each position in the current batch
    # batch_ops      — InsertOne operation for each position
    # Both lists are always the same length and same order.
    batch_domains: list[str | None] = []
    batch_ops:     list[InsertOne]  = []

    successfully_inserted_domains: set[str] = set()
    skipped_domains:               list[str] = []
    total_inserted = 0
    total_skipped  = 0

    for doc in cursor:
        # ── Extract the domain BEFORE popping _id ──────────────────────────
        raw_domains = doc.get("domains")
        raw_domain  = doc.get("domain")
        if raw_domains:
            domain = clean_domain(raw_domains[0])
        elif raw_domain:
            domain = clean_domain(raw_domain)
        else:
            domain = None

        doc.pop("_id", None)   # let MongoDB generate a fresh _id in the target

        batch_domains.append(domain)
        batch_ops.append(InsertOne(doc))

        if len(batch_ops) >= BATCH_SIZE_MONGO:
            ins, skip = _flush_batch(dst_col, batch_domains, batch_ops)
            successfully_inserted_domains.update(ins)
            skipped_domains.extend(skip)
            total_inserted += len(ins)
            total_skipped  += len(skip)
            batch_domains.clear()
            batch_ops.clear()

    # Flush the final partial batch
    if batch_ops:
        ins, skip = _flush_batch(dst_col, batch_domains, batch_ops)
        successfully_inserted_domains.update(ins)
        skipped_domains.extend(skip)
        total_inserted += len(ins)
        total_skipped  += len(skip)

    # ── Summary ─────────────────────────────────────────────────────────────
    log.info("─" * 60)
    log.info("STEP 5 SUMMARY")
    log.info("  ✔  Total inserted into MongoDB : %d", total_inserted)
    log.info("  ✘  Total skipped (duplicates)  : %d", total_skipped)

    # Print a sample of successfully inserted domains (up to 10)
    sample = list(successfully_inserted_domains)[:10]
    log.info("  Sample of inserted domains     : %s", sample)

    # Print ALL skipped domains
    if skipped_domains:
        log.info("  Domains skipped due to duplicates (all %d):", len(skipped_domains))
        for d in skipped_domains:
            log.info("    ✘ %s", d)
    else:
        log.info("  No domains were skipped — zero duplicates found.")

    log.info("─" * 60)

    return successfully_inserted_domains


def _flush_batch(
    col,
    domains: list,
    ops: list,
) -> tuple[list[str], list[str]]:
    """
    Execute one bulk_write batch and return:
      - inserted_domains : domains that were successfully inserted
      - skipped_domains  : domains that were rejected (duplicate fingerprint)

    How we know which positions failed:
      MongoDB's BulkWriteError.details["writeErrors"] is a list of dicts.
      Each dict has an "index" key = the 0-based position in our ops list
      that caused the error.  Everything NOT in that set was inserted.
    """
    try:
        col.bulk_write(ops, ordered=False)
        # No exception = all inserted
        inserted = [d for d in domains if d]
        skipped  = []

    except BulkWriteError as bwe:
        write_errors   = bwe.details.get("writeErrors", [])
        failed_indices = {err["index"] for err in write_errors}

        inserted = [
            domains[i]
            for i in range(len(domains))
            if i not in failed_indices and domains[i]
        ]
        skipped = [
            domains[i]
            for i in failed_indices
            if domains[i]
        ]

        log.warning(
            "  Batch partial: %d inserted, %d skipped (duplicate fingerprint_sha256)",
            len(inserted), len(skipped),
        )

    return inserted, skipped


# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — Append confirmed-inserted domains into global-dataset.csv
# ═══════════════════════════════════════════════════════════════════════════

def get_last_global_index(global_csv: Path) -> int:
    if not global_csv.exists() or global_csv.stat().st_size == 0:
        log.warning("  %s is empty or missing — starting index at 0.", global_csv)
        return 0

    with global_csv.open("rb") as fh:
        fh.seek(0, 2)
        file_size = fh.tell()
        fh.seek(-min(4096, file_size), 2)
        tail = fh.read().decode("utf-8", errors="replace")

    last_line = tail.strip().splitlines()[-1]
    idx_str   = last_line.split(",", 1)[0].strip()

    try:
        return int(idx_str)
    except ValueError:
        raise ValueError(
            f"Could not parse index from last line of {global_csv}: {last_line!r}"
        )


def append_to_global_csv(
    new_csv: Path,
    global_csv: Path,
    inserted_domains: set,
) -> None:
    """
    Append rows from new_csv into global_csv ONLY for domains that are
    confirmed present in inserted_domains (i.e. confirmed written to MongoDB).

    This is the consistency guarantee:
      MongoDB inserted N domains  →  CSV gets exactly those same N domains.
    """
    log.info("STEP 6 — Appending confirmed domains from %s into %s …", new_csv, global_csv)

    start_index = get_last_global_index(global_csv) + 1
    log.info("  Global CSV continues from index %d", start_index)

    appended = 0
    skipped  = 0

    with new_csv.open("r", newline="", encoding="utf-8") as src, \
         global_csv.open("a", newline="", encoding="utf-8") as dst:

        reader = csv.DictReader(src)
        writer = csv.writer(dst)

        for row in reader:
            domain = row.get("domain", "").strip()
            if not domain:
                continue

            if domain not in inserted_domains:
                skipped += 1
                continue

            writer.writerow([start_index + appended, domain])
            appended += 1

            if appended % 100_000 == 0:
                log.info("  … %d rows appended so far", appended)

    log.info("─" * 60)
    log.info("STEP 6 SUMMARY")
    log.info("  ✔  Domains appended to global CSV : %d", appended)
    log.info("  ✘  Domains skipped (not in MongoDB confirmed set) : %d", skipped)
    log.info(
        "  Last index in global CSV now     : %d",
        start_index + appended - 1 if appended else start_index - 1,
    )
    log.info("─" * 60)


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    log.info("=" * 60)
    log.info("Pipeline starting")
    log.info("=" * 60)

    log.info("Connecting to MongoDB at %s …", MONGO_URL)
    client = MongoClient(
        MONGO_URL,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
    )
    client.server_info()
    log.info("MongoDB connection OK.")

    try:
        # Step 1 & 2 — extract domains to CSV
        rows_written = extract_domains_to_csv(client)
        if rows_written == 0:
            log.warning("No domains extracted — check MongoDB data and filters.")
            return

        # Step 3 — drop source collection
        rename_collection(client)

        # Step 4 — run crawler, block until done
        run_main_script()

        # Step 5 — insert certificates, get back confirmed domain set
        inserted_domains = append_certificates(client)

        # Step 6 — append ONLY confirmed domains to global CSV
        append_to_global_csv(NEW_CSV, GLOBAL_CSV, inserted_domains)

        # Step 7 — cleanup: delete new-data.csv and drop new-data database
        log.info("Step 7: cleaning up new-data CSV and database ...")
        try:
            csv_path = Path(NEW_CSV)
            if csv_path.exists():
                csv_path.unlink()  # Path.unlink() is cross-platform
                log.info("Deleted %s successfully.", NEW_CSV)
            else:
                log.info("%s already absent — skipping.", NEW_CSV)
        except Exception as e:
            log.error("Failed to delete %s: %s", NEW_CSV, e)

        try:
            client.drop_database("new-data")
            log.info("Database 'new-data' dropped successfully.")
        except Exception as e:
            log.error("Failed to drop database 'new-data': %s", e)

    finally:
        client.close()
        log.info("MongoDB connection closed.")

    log.info("=" * 60)
    log.info("Pipeline finished successfully.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()