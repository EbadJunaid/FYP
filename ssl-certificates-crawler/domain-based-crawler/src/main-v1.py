#!/usr/bin/env python3
"""
Production-oriented SSL certificate crawler (Threaded + MongoDB atomic-claim queue)

Updated: ZCERT_PATH default "./zcertificate", MAX_ATTEMPTS set to 3, failed tasks logged to file.
"""

import csv
import os
import time
import socket
import ssl
import hashlib
import tempfile
import subprocess
import json
import signal
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from pymongo import MongoClient, ReturnDocument, UpdateOne
from pymongo.errors import DuplicateKeyError

# Optional: cryptography for parsing cert content
try:
    from cryptography import x509
    from cryptography.hazmat.backends import default_backend
    HAVE_CRYPTO = True
except Exception:
    HAVE_CRYPTO = False

# -----------------------
# Configuration
# -----------------------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "hell-v1")

CSV_PATH = os.getenv("CSV_PATH", "../mini-dataset.csv")  # path to CSV file to import
STAGING_COLL = "staging_domains"
CERTS_COLL = "certificates"

THREAD_COUNT = int(os.getenv("THREAD_COUNT", "30"))

# Timeouts and intervals (seconds)
CONNECT_TIMEOUT = 8.0
READ_TIMEOUT = 8.0
HEARTBEAT_INTERVAL = 20           # worker updates last_heartbeat every N seconds while processing
RECLAIM_TIMEOUT = 60         # reclaim tasks with no heartbeat for this many seconds (10 minutes default)
RECLAIM_INTERVAL = 20             # how often the reclaimer runs
MAX_ATTEMPTS = 3                   # changed per your request
INITIAL_BACKOFF = 10              # seconds
MAX_BACKOFF = 20                # seconds (1 hour)

# Worker-safety
WORKER_POLL_SLEEP = 1.0           # when no tasks are available

# zcertificate executable (optional): set path to your executable if you want to use it
ZCERT_PATH = os.getenv("ZCERT_PATH", "../zcertificate/zcertificate")  # default to ./zcertificate

# Failure log path
FAILED_TASK_LOG = os.getenv("FAILED_TASK_LOG", "../logs/new-v1.log")

# Global shutdown event
SHUTDOWN = Event()


# -----------------------
# Utilities
# -----------------------
def utcnow():
    return datetime.utcnow()


def append_failure_log(domain: str, attempts: int, error_msg: str):
    """Append a line to failure log with timestamp, domain, attempts, and error."""
    ts = utcnow().isoformat()
    line = f"{ts}\t{domain}\tattempts={attempts}\t{error_msg}\n"
    try:
        with open(FAILED_TASK_LOG, "a", encoding="utf-8") as fh:
            fh.write(line)
    except Exception as e:
        # best-effort: don't crash the worker if logging fails
        print("Failed to write to failure log:", e)


def fingerprint_sha256_from_der(der_bytes: bytes) -> str:
    return hashlib.sha256(der_bytes).hexdigest()


def der_from_pem(pem_text: str) -> bytes:
    try:
        der = ssl.PEM_cert_to_DER_cert(pem_text)
        return der
    except Exception:
        try:
            header = "-----BEGIN CERTIFICATE-----"
            footer = "-----END CERTIFICATE-----"
            start = pem_text.index(header) + len(header)
            end = pem_text.index(footer)
            b64 = pem_text[start:end].strip()
            import base64
            return base64.b64decode(b64)
        except Exception:
            raise


def pem_from_der(der_bytes: bytes) -> str:
    return ssl.DER_cert_to_PEM_cert(der_bytes)


# -----------------------
# MongoDB helpers
# -----------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
staging = db[STAGING_COLL]
certs = db[CERTS_COLL]


def create_indexes():
    staging.create_index("domain", unique=True)
    staging.create_index([("status", 1), ("next_attempt_at", 1)])
    staging.create_index("last_heartbeat")
    staging.create_index("start_ts")

    certs.create_index("fingerprint_sha256", unique=True)
    # Ensure domain+fingerprint unique as well
    try:
        certs.create_index([("domain", 1), ("fingerprint_sha256", 1)], unique=True, name="domain_fp_unique")
    except Exception:
        # ignore if index already exists in incompatible form
        pass


# -----------------------
# CSV import into staging
# -----------------------
def import_csv_into_staging(csv_path, drop_and_import=False, batch_size=1000):
    """
    Import CSV rows into staging collection. CSV format: index,Websites URL
    If staging already has rows and drop_and_import is False, import is skipped.
    """
    if staging.count_documents({}) > 0 and not drop_and_import:
        print("Staging collection already populated. Skipping CSV import.")
        return

    if drop_and_import:
        staging.drop()
        create_indexes()

    ops = []
    now = utcnow()
    with open(csv_path, newline="", encoding="utf-8") as fh:
        reader = csv.reader(fh)
        first = next(reader, None)
        if first is None:
            print("CSV is empty.")
            return

        # detect header: if first[0] is non-numeric or contains letters, treat as header
        try:
            int(first[0])
            rows_iter = (first,)  # include first row as data
            rows_iter = (r for r in (first, *reader))
        except Exception:
            rows_iter = reader

        count = 0
        for row in rows_iter:
            if not row:
                continue
            if len(row) == 1:
                domain = row[0].strip()
            else:
                domain = row[1].strip()
            if not domain:
                continue
            domain = domain.strip().lower()
            doc = {
                "domain": domain,
                "status": "pending",
                "attempts": 0,
                "last_error": None,
                "next_attempt_at": now,
                "start_ts": None,
                "worker_id": None,
                "last_heartbeat": None,
                "inserted_at": now,
            }
            ops.append(UpdateOne({"domain": domain}, {"$setOnInsert": doc}, upsert=True))
            count += 1
            if len(ops) >= batch_size:
                staging.bulk_write(ops, ordered=False)
                ops = []
                print(f"Imported {count} rows (batch)...")
        if ops:
            staging.bulk_write(ops, ordered=False)
    print("CSV import completed. Total rows attempted to upsert:", staging.count_documents({}))


# -----------------------
# Certificate fetch & parse
# -----------------------
def fetch_certificate_from_host(domain: str, port: int = 443, timeout: float = CONNECT_TIMEOUT):
    hostname = domain
    if ":" in domain and domain.count(":") == 1:
        hostname, port_part = domain.rsplit(":", 1)
        try:
            port = int(port_part)
        except Exception:
            pass

    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE

    addr_info = socket.getaddrinfo(hostname, port, proto=socket.IPPROTO_TCP)
    if not addr_info:
        raise RuntimeError("DNS lookup failed")

    af, socktype, proto, canonname, sa = addr_info[0]
    s = socket.socket(af, socktype, proto)
    s.settimeout(timeout)
    try:
        with context.wrap_socket(s, server_hostname=hostname) as ss:
            ss.settimeout(timeout)
            ss.connect(sa)
            der = ss.getpeercert(True)
            if not der:
                raise RuntimeError("no peer cert")
            pem = pem_from_der(der)
            return der, pem
    finally:
        try:
            s.close()
        except Exception:
            pass


def parse_certificate_with_cryptography(der_bytes: bytes):
    if not HAVE_CRYPTO:
        return None
    cert = x509.load_der_x509_certificate(der_bytes, default_backend())
    meta = {}
    meta["serial_number"] = hex(cert.serial_number)
    try:
        meta["not_valid_before"] = cert.not_valid_before.isoformat()
        meta["not_valid_after"] = cert.not_valid_after.isoformat()
    except Exception:
        pass

    def name_to_dict(name):
        d = {}
        for attr in name:
            d.setdefault(attr.oid._name or str(attr.oid), []).append(attr.value)
        return d

    meta["issuer"] = name_to_dict(cert.issuer)
    meta["subject"] = name_to_dict(cert.subject)
    try:
        ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
        meta["san"] = ext.value.get_values_for_type(x509.DNSName)
    except Exception:
        meta["san"] = []
    return meta


def parse_with_zcertificate(pem_text: str):
    if not ZCERT_PATH:
        return None
    try:
        with tempfile.NamedTemporaryFile(mode="w+", delete=False, suffix=".pem") as tf:
            tf.write(pem_text)
            tf.flush()
            tmp_path = tf.name
        # adjust args for your zcertificate CLI if different
        proc = subprocess.run([ZCERT_PATH, tmp_path], capture_output=True, text=True, timeout=30)
        out = proc.stdout.strip()
        try:
            data = json.loads(out)
            return data
        except Exception:
            return None
    except Exception as e:
        print("zcertificate parse error:", e)
        return None
    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# -----------------------
# Worker & claim logic
# -----------------------
def compute_backoff_seconds(attempts: int) -> int:
    return int(min(MAX_BACKOFF, INITIAL_BACKOFF * (2 ** attempts)))


def claim_one_task(worker_id: str):
    now = utcnow()
    filter_q = {
        "status": "pending",
        "next_attempt_at": {"$lte": now}
    }
    update_q = {
        "$set": {"status": "in-progress", "worker_id": worker_id, "start_ts": now, "last_heartbeat": now}
    }
    claimed = staging.find_one_and_update(filter_q, update_q, sort=[("_id", 1)], return_document=ReturnDocument.AFTER)
    return claimed


def mark_task_done(task_doc, cert_fingerprint: str):
    now = utcnow()
    staging.update_one({"_id": task_doc["_id"]},
                       {"$set": {"status": "done", "done_at": now, "last_error": None, "cert_fingerprint": cert_fingerprint},
                        "$unset": {"worker_id": "", "start_ts": "", "last_heartbeat": ""}})


def mark_task_failed(task_doc, error_msg: str):
    now = utcnow()
    attempts = task_doc.get("attempts", 0) + 1

    if attempts >= MAX_ATTEMPTS:
        # Mark permanently failed and log details
        staging.update_one({"_id": task_doc["_id"]},
                           {"$set": {"status": "failed", "last_error": error_msg, "attempts": attempts, "failed_at": now},
                            "$unset": {"worker_id": "", "start_ts": "", "last_heartbeat": ""}})
        append_failure_log(task_doc.get("domain", "<unknown>"), attempts, error_msg)
        print(f"[mark_task_failed] {task_doc.get('domain')} marked FAILED after {attempts} attempts.")
        return

    backoff = compute_backoff_seconds(attempts)
    next_try = now + timedelta(seconds=backoff)
    staging.update_one({"_id": task_doc["_id"]},
                       {"$set": {"status": "pending", "last_error": error_msg, "next_attempt_at": next_try, "attempts": attempts},
                        "$unset": {"worker_id": "", "start_ts": "", "last_heartbeat": ""}})
    print(f"[mark_task_failed] {task_doc.get('domain')} will retry in {backoff}s (attempt {attempts}).")


def heartbeat_updater(stop_event: Event, task_id, worker_id: str):
    while not stop_event.wait(HEARTBEAT_INTERVAL):
        try:
            staging.update_one({"_id": task_id, "worker_id": worker_id},
                               {"$set": {"last_heartbeat": utcnow()}})
        except Exception:
            pass


def save_certificate_safe(domain: str, pem_text: str, der_bytes: bytes, parsed_meta: dict):
    fp = fingerprint_sha256_from_der(der_bytes)
    now = utcnow()
    doc = {
        "domain": domain,
        "retrieved_at": now,
        "pem": pem_text,
        "fingerprint_sha256": fp,
        "meta": parsed_meta or {},
    }
    try:
        certs.update_one({"fingerprint_sha256": fp, "domain": domain},
                         {"$set": doc}, upsert=True)
    except DuplicateKeyError:
        pass
    return fp


def worker_loop(worker_name: str):
    while not SHUTDOWN.is_set():
        task = None
        try:
            task = claim_one_task(worker_name)
            if not task:
                time.sleep(WORKER_POLL_SLEEP)
                continue

            domain = task["domain"]
            print(f"[{worker_name}] Claimed {domain}")
            hb_stop = Event()
            hb_thread = Thread(target=heartbeat_updater, args=(hb_stop, task["_id"], worker_name), daemon=True)
            hb_thread.start()

            try:
                der, pem = fetch_certificate_from_host(domain, timeout=CONNECT_TIMEOUT)
                parsed = None
                parsed = parse_with_zcertificate(pem)
                if parsed is None and HAVE_CRYPTO:
                    parsed = parse_certificate_with_cryptography(der)
                fp = save_certificate_safe(domain, pem, der, parsed)
                mark_task_done(task, cert_fingerprint=fp)
                print(f"[{worker_name}] {domain} -> saved (fp={fp[:12]})")
            except Exception as e:
                err = repr(e)
                print(f"[{worker_name}] {domain} -> ERROR: {err}")
                # fetch the latest version of task doc (attempt count may have changed)
                fresh = staging.find_one({"_id": task["_id"]})
                # If fresh is None, task may have been modified elsewhere — handle gracefully
                if fresh is None:
                    print(f"[{worker_name}] Task doc disappeared for {domain}. Skipping.")
                else:
                    mark_task_failed(fresh, err)
            finally:
                hb_stop.set()
                hb_thread.join(timeout=2)

        except Exception as e:
            print(f"[{worker_name}] Unexpected error: {e}")
            time.sleep(1)

    print(f"[{worker_name}] shutdown requested, exiting")


# -----------------------
# Reclaimer thread
# -----------------------
def reclaimer_loop():
    while not SHUTDOWN.is_set():
        try:
            cutoff = utcnow() - timedelta(seconds=RECLAIM_TIMEOUT)
            stale_filter = {"status": "in-progress", "last_heartbeat": {"$lt": cutoff}}
            stale_count = staging.count_documents(stale_filter)
            if stale_count:
                print(f"[reclaimer] Reclaiming {stale_count} stale tasks (last_heartbeat < {cutoff.isoformat()})")
                docs = staging.find(stale_filter, projection={"_id": 1, "attempts": 1, "domain": 1})
                for d in docs:
                    attempts = d.get("attempts", 0) + 1
                    if attempts >= MAX_ATTEMPTS:
                        # mark failed permanently
                        staging.update_one({"_id": d["_id"]},
                                           {"$set": {"status": "failed", "attempts": attempts, "failed_at": utcnow()},
                                            "$unset": {"worker_id": "", "start_ts": "", "last_heartbeat": ""}})
                        append_failure_log(d.get("domain", "<unknown>"), attempts, "reclaimed_and_failed")
                        print(f"[reclaimer] {d.get('domain')} reclaimed and marked failed after {attempts} attempts.")
                    else:
                        staging.update_one({"_id": d["_id"]},
                                           {"$set": {"status": "pending", "next_attempt_at": utcnow()},
                                            "$unset": {"worker_id": "", "start_ts": "", "last_heartbeat": ""},
                                            "$inc": {"attempts": 1}})
            for _ in range(int(RECLAIM_INTERVAL)):
                if SHUTDOWN.is_set():
                    break
                time.sleep(1)
        except Exception as e:
            print("[reclaimer] error:", e)
            time.sleep(5)
    print("[reclaimer] exiting")


# -----------------------
# Signal handling
# -----------------------
def setup_signal_handlers():
    def _handler(signum, frame):
        print(f"Signal {signum} received: initiating shutdown...")
        SHUTDOWN.set()
    signal.signal(signal.SIGINT, _handler)
    signal.signal(signal.SIGTERM, _handler)


# -----------------------
# Main entrypoint
# -----------------------
def main():
    print("Starting crawler (DB-backed queue)")

    create_indexes()

    # Import CSV if staging empty
    if staging.count_documents({}) == 0:
        print("Staging collection empty — importing CSV:", CSV_PATH)
        import_csv_into_staging(CSV_PATH)
    else:
        print("Staging collection already contains tasks. Skipping CSV import.")

    setup_signal_handlers()

    reclaimer_thread = Thread(target=reclaimer_loop, daemon=True)
    reclaimer_thread.start()

    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as ex:
        futures = []
        for i in range(THREAD_COUNT):
            wname = f"{os.uname().nodename}:{os.getpid()}:T{i}"
            futures.append(ex.submit(worker_loop, wname))
        try:
            while not SHUTDOWN.is_set():
                pending = staging.count_documents({"status": "pending"})
                working = staging.count_documents({"status": "in-progress"})
                
                if pending == 0 and working == 0:
                    print("\n[Main] No pending or active tasks found. Exiting...")
                    SHUTDOWN.set() # Tells workers to stop
                    break
                
                time.sleep(1)
        except KeyboardInterrupt:
            SHUTDOWN.set()
        print("Main: shutdown set, waiting for workers to finish...")

    reclaimer_thread.join(timeout=5)
    print("Crawler exiting cleanly.")


if __name__ == "__main__":
    main()
