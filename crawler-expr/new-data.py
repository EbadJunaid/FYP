#!/usr/bin/env python3
"""
pipeline.py — Senior-grade orchestration script

Pipeline steps:
  1. Connect to MongoDB "go-server" / "certificates"
  2. Extract up to 1,000,000 domains (found=false), first domain per doc,
     strip leading "www.", write to new-data.csv
  3. Rename "certificates" → "delete" in "go-server"
  4. Launch  main-v6.py  as a subprocess and wait for it to finish
  5. Append documents from "new-dataset"/"certificates" → "tranco-latest-66k"/"certificates"
  6. Append new-data.csv entries (re-indexed) into global-dataset.csv
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
# Configuration — adjust as needed
# ---------------------------------------------------------------------------
MONGO_URL          = "mongodb://localhost:27017"
SOURCE_DB          = "go-server"
SOURCE_COLLECTION  = "certificates"

NEW_CSV            = Path("new-data.csv")
GLOBAL_CSV         = Path("global-dataset.csv")

TARGET_DB          = "arslan-v3"
TARGET_COLLECTION  = "certificates"

NEW_DATASET_DB          = "new-dataset"
NEW_DATASET_COLLECTION  = "certificates"

MAIN_SCRIPT        = "main-v6.py"
MAIN_SCRIPT_MONGO  = "mongodb://localhost:27017"
MAIN_SCRIPT_DB     = "new-dataset"
MAIN_STATUS_COL    = "domain_status"
MAIN_CERTS_COL     = "certificates"

EXTRACT_LIMIT      = 1_500   # up to 1 million domains
BATCH_SIZE_CSV     = 5_000       # rows flushed per write cycle
BATCH_SIZE_MONGO   = 1_000       # documents per bulk-insert batch

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
    """Strip scheme artefacts and leading 'www.' from a domain string."""
    d = raw.strip()
    # Remove markdown-style links like [www.foo.com](https://www.foo.com)
    if d.startswith("[") and "](" in d:
        d = d[1 : d.index("](")]
    # Remove any remaining scheme prefix
    for prefix in ("https://", "http://"):
        if d.lower().startswith(prefix):
            d = d[len(prefix):]
    # Strip leading www.
    if d.lower().startswith("www."):
        d = d[4:]
    return d.rstrip("/")


def extract_domains_to_csv(client: MongoClient) -> int:
    """
    Query certificates where found=false, grab first domain per document,
    clean it, and stream-write to new-data.csv.

    Returns the number of rows written.
    """
    log.info("STEP 1/2 — Extracting domains from MongoDB …")

    db  = client[SOURCE_DB]
    col = db[SOURCE_COLLECTION]

    # Use the existing domains_1 index; project only what we need.
    cursor = (
        col.find(
            {"found": False},
            {"domains": {"$slice": 1}, "_id": 0},   # only first element
        )
        .batch_size(BATCH_SIZE_CSV)
        .limit(EXTRACT_LIMIT)
    )

    written  = 0
    buffer   = []

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
# STEP 3 — Rename "certificates" → "delete"
# ═══════════════════════════════════════════════════════════════════════════

def rename_collection(client: MongoClient) -> None:
    log.info("STEP 3 — Deleting '%s' in db '%s' …",
             SOURCE_COLLECTION, SOURCE_DB)

    db = client[SOURCE_DB]
    db[SOURCE_COLLECTION].drop()

    log.info("  Deletion complete.")


# ═══════════════════════════════════════════════════════════════════════════
# STEP 4 — Launch main-v6.py as a subprocess and wait
# ═══════════════════════════════════════════════════════════════════════════

def run_main_script() -> None:
    """
    Why subprocess (not multiprocessing / threading)?

    main-v6.py is an external script we do not own.  A subprocess gives full
    process isolation: independent memory space, separate Python interpreter,
    clean exit-code signalling, and no shared-state hazards.  We simply block
    on .wait() / communicate() until it finishes — exactly what's needed here.
    """
    log.info("STEP 4 — Launching %s …", MAIN_SCRIPT)

    cmd = [
        sys.executable,          # same Python that runs this script
        MAIN_SCRIPT,
        "--mongodb-url",  MAIN_SCRIPT_MONGO,
        "--db-name",      MAIN_SCRIPT_DB,
        "--status-collection",       MAIN_STATUS_COL,
        "--certificates-collection", MAIN_CERTS_COL,
        "--csv-file",     str(NEW_CSV.resolve()),
    ]

    log.info("  Command: %s", " ".join(cmd))

    t0 = time.monotonic()
    result = subprocess.run(
        cmd,
        stdout=sys.stdout,   # stream child output directly to our stdout
        stderr=sys.stderr,
        text=True,
    )
    elapsed = time.monotonic() - t0

    if result.returncode != 0:
        raise RuntimeError(
            f"{MAIN_SCRIPT} exited with code {result.returncode} "
            f"after {elapsed:.1f}s"
        )

    log.info("STEP 4 done — %s finished in %.1fs", MAIN_SCRIPT, elapsed)


# ═══════════════════════════════════════════════════════════════════════════
# STEP 5 — Append new-dataset/certificates → tranco-latest-66k/certificates
# ═══════════════════════════════════════════════════════════════════════════

def append_certificates(client: MongoClient) -> None:
    """
    Bulk-insert documents from new-dataset/certificates into
    tranco-latest-66k/certificates in batches.

    Why ordered=False?  It lets MongoDB continue on duplicate-key errors
    (in case a re-run overlaps) and maximises throughput on the server side.
    """
    log.info("STEP 5 — Copying certificates from '%s' → '%s' …",
             NEW_DATASET_DB, TARGET_DB)

    src_col = client[NEW_DATASET_DB][NEW_DATASET_COLLECTION]
    dst_col = client[TARGET_DB][TARGET_COLLECTION]

    total   = src_col.count_documents({})
    log.info("  Source document count: %d", total)

    cursor  = src_col.find({}).batch_size(BATCH_SIZE_MONGO)
    ops     = []
    copied  = 0
    errors  = 0

    for doc in cursor:
        # Remove _id so MongoDB assigns a fresh one in the target collection,
        # avoiding duplicate-key conflicts if this step is ever re-run.
        doc.pop("_id", None)
        ops.append(InsertOne(doc))

        if len(ops) >= BATCH_SIZE_MONGO:
            copied, errors = _flush_bulk(dst_col, ops, copied, errors)
            ops.clear()

    if ops:
        copied, errors = _flush_bulk(dst_col, ops, copied, errors)

    log.info(
        "STEP 5 done — %d documents inserted, %d errors skipped.",
        copied, errors,
    )


def _flush_bulk(col, ops: list, copied: int, errors: int):
    try:
        res = col.bulk_write(ops, ordered=False)
        copied += res.inserted_count
    except BulkWriteError as bwe:
        # Some docs may have inserted; count what succeeded
        copied  += bwe.details.get("nInserted", 0)
        errors  += len(bwe.details.get("writeErrors", []))
        log.warning("  Bulk-write partial error: %d write errors in this batch",
                    len(bwe.details.get("writeErrors", [])))

    if copied % 50_000 < BATCH_SIZE_MONGO:
        log.info("  … %d documents copied so far", copied)

    return copied, errors


# ═══════════════════════════════════════════════════════════════════════════
# Helper — fetch domains that finished processing in main-v6.py
# ═══════════════════════════════════════════════════════════════════════════

def get_completed_domains(client: MongoClient) -> set:
    """
    Query new-dataset/domain_status for documents where status == "completed"
    and return the set of cleaned domain names.

    This is run after main-v6.py finishes (STEP 4), since that's the script
    that populates domain_status. It gives us the authoritative list of
    domains that actually finished processing, independent of how the
    certificate copy in STEP 5 went — STEP 6 should only append these.
    """
    log.info("Querying '%s'/'%s' for status == 'completed' domains …",
              MAIN_SCRIPT_DB, MAIN_STATUS_COL)

    status_col = client[MAIN_SCRIPT_DB][MAIN_STATUS_COL]

    cursor = status_col.find(
        {"status": "completed"},
        {"domain": 1, "domains": 1, "_id": 0},
    ).batch_size(BATCH_SIZE_MONGO)

    completed_domains = set()
    for doc in cursor:
        # Handle either a singular "domain" field or a "domains" array,
        # since we don't control main-v6.py's exact schema.
        raw = doc.get("domain")
        if not raw:
            domains_field = doc.get("domains")
            raw = domains_field[0] if domains_field else None

        if not raw:
            continue

        domain = clean_domain(raw)
        if domain:
            completed_domains.add(domain)

    log.info("  Found %d domains with status == 'completed'.",
              len(completed_domains))
    return completed_domains


# ═══════════════════════════════════════════════════════════════════════════
# STEP 6 — Append new-data.csv (re-indexed) into global-dataset.csv
# ═══════════════════════════════════════════════════════════════════════════

def get_last_global_index(global_csv: Path) -> int:
    """
    Read the last line of global-dataset.csv and return its numeric index.
    Handles large files efficiently by seeking near the end of the file.
    """
    if not global_csv.exists() or global_csv.stat().st_size == 0:
        log.warning("  %s is empty or missing — starting index at 0.", global_csv)
        return 0

    with global_csv.open("rb") as fh:
        # Seek to last ~1 KB to find the final newline-terminated line
        fh.seek(0, 2)
        file_size = fh.tell()
        seek_back = min(4096, file_size)
        fh.seek(-seek_back, 2)
        tail = fh.read().decode("utf-8", errors="replace")

    last_line = tail.strip().splitlines()[-1]
    idx_str   = last_line.split(",", 1)[0].strip()

    try:
        return int(idx_str)
    except ValueError:
        raise ValueError(
            f"Could not parse index from last line of {global_csv}: {last_line!r}"
        )


def append_to_global_csv(new_csv: Path, global_csv: Path, completed_domains: set) -> None:
    """
    Append only the domains from new_csv whose status in
    new-dataset/domain_status is "completed" — not every row of new_csv.
    Index numbering is unchanged: it simply continues from the last global
    index, one per appended (i.e. completed) row.
    """
    log.info("STEP 6 — Appending completed domains from %s into %s …",
              new_csv, global_csv)

    start_index = get_last_global_index(global_csv) + 1
    log.info("  Global CSV last index: %d — new entries start at %d",
             start_index - 1, start_index)

    appended = 0
    skipped  = 0

    with new_csv.open("r", newline="", encoding="utf-8") as src, \
         global_csv.open("a", newline="", encoding="utf-8") as dst:

        reader = csv.DictReader(src)
        writer = csv.writer(dst)

        # Ensure we start on a new line if the file doesn't end with one
        # (handled implicitly by opening in append mode + csv.writer)

        for row in reader:
            domain = row.get("domain", "").strip()
            if not domain:
                continue

            if domain not in completed_domains:
                skipped += 1
                continue

            global_idx = start_index + appended
            writer.writerow([global_idx, domain])
            appended += 1

            if appended % 100_000 == 0:
                log.info("  … %d rows appended so far", appended)

    log.info(
        "STEP 6 done — %d rows appended (%d skipped, not completed) to %s (last index: %d)",
        appended,
        skipped,
        global_csv,
        start_index + appended - 1 if appended else start_index - 1,
    )


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    log.info("=" * 60)
    log.info("Pipeline starting")
    log.info("=" * 60)

    # ── Connect once; reuse client across steps ──────────────────────────
    log.info("Connecting to MongoDB at %s …", MONGO_URL)
    client = MongoClient(
        MONGO_URL,
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
    )
    # Force a real connection attempt
    client.server_info()
    log.info("MongoDB connection OK.")

    try:
        # Step 1 & 2
        rows_written = extract_domains_to_csv(client)
        if rows_written == 0:
            log.warning("No domains extracted — check MongoDB data and filters.")
            return

        # Step 3
        rename_collection(client)

        # Step 4  (subprocess; blocks until done)
        run_main_script()

        # Fetch the authoritative "completed" domain list now that
        # main-v6.py has finished writing to domain_status.
        completed_domains = get_completed_domains(client)

        # Step 5  (re-open client in case subprocess held locks)
        append_certificates(client)

        # Step 6 — only append domains whose status is "completed"
        append_to_global_csv(NEW_CSV, GLOBAL_CSV, completed_domains)

    finally:
        client.close()
        log.info("MongoDB connection closed.")

    log.info("=" * 60)
    log.info("Pipeline finished successfully.")
    log.info("=" * 60)


if __name__ == "__main__":
    main()