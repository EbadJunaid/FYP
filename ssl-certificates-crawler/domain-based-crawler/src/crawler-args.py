### This code is just the copy of crawler.py and just adds command line arguments 
### It has features like does not have raw field , also adds the scope field and also supports CLI args
### This code also checks for parsed.fingerprint_sha256 means if the google.com and youtube.com has same
### certificates [because of SAN] then first google is added into db and then when it tries to add 
### youtube.com it check parsed.fingerprint_sha256 and knows that same certificate is already there 

import csv
import socket
import ssl
import json
import time
import signal
import sys
import threading
import os
import subprocess
import argparse
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError, BulkWriteError

# -------------------- Configuration --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

_START_TIMESTAMP = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


CONFIG = {
    'MONGODB_URL': "mongodb://localhost:27017",
    'DB_NAME': "hugging-face-700k",
    'STATUS_COLLECTION': "domain_status",
    'CERTIFICATES_COLLECTION': "certificates",
    
    # Paths
    'CSV_FILE': os.path.join(BASE_DIR, "../../../ct-logs-renewal-pipeline/global-dataset.csv"),
    'ZCERT_BINARY': os.path.join(BASE_DIR, "../../../binaries/zcertificate"),
    'LOG_FILE': os.path.join(BASE_DIR,f"./logs/renew-{_START_TIMESTAMP}.log"),
    'ISSUE_LOG_FILE': os.path.join(BASE_DIR,f"./logs/renew-thread-issues-{_START_TIMESTAMP}.log"),
    'NUM_THREADS': 30,
    'SOCKET_TIMEOUT': 10,
    'ZCERT_TIMEOUT': 10,
    'RETRY_ENABLED': False,
    'MAX_RETRIES': 2,
    'RETRY_DELAYS': [5, 10, 15],
    'MONITOR_INTERVAL': 5,
    'HEARTBEAT_INTERVAL': 10,
    'STALE_THRESHOLD': 60,
}

# -------------------- Global State --------------------
shutdown_event = threading.Event()
client = None
db = None
status_coll = None
certs_coll = None
log_lock = threading.Lock() # Prevents jumbled logs

# -------------------- Argument Parsing --------------------
def parse_arguments():
    parser = argparse.ArgumentParser(description="Hybrid Crawler Configuration")
    
    # Core Database and File Arguments
    parser.add_argument('--mongodb-url', type=str, help='MongoDB connection string')
    parser.add_argument('--db-name', type=str, help='Target Database name')
    parser.add_argument('--status-collection', type=str, help='Name of the status collection')
    parser.add_argument('--certificates-collection', type=str, help='Name of the certificates collection')
    parser.add_argument('--csv-file', type=str, help='Path to the input CSV file')
    
    # Process Arguments
    parser.add_argument('--zcert-binary', type=str, help='Path to zcertificate binary')
    parser.add_argument('--log-file', type=str, help='Path to the main log file')
    parser.add_argument('--issue-log-file', type=str, help='Path to the issue log file')
    parser.add_argument('--num-threads', type=int, help='Number of worker threads')
    parser.add_argument('--socket-timeout', type=int, help='Socket timeout in seconds')
    parser.add_argument('--zcert-timeout', type=int, help='Zcert binary timeout in seconds')
    parser.add_argument('--retry-enabled', action='store_true', help='Flag to enable retry logic')
    parser.add_argument('--max-retries', type=int, help='Maximum number of retries')
    parser.add_argument('--retry-delays', type=int, nargs='+', help='List of delays for retries (e.g., 5 10 15)')
    parser.add_argument('--monitor-interval', type=int, help='Dashboard update interval in seconds')
    parser.add_argument('--heartbeat-interval', type=int, help='Worker heartbeat interval in seconds')
    parser.add_argument('--stale-threshold', type=int, help='Threshold for stale worker detection in seconds')

    args = parser.parse_args()

    # Override CONFIG only if the argument was explicitly provided
    if args.mongodb_url is not None: CONFIG['MONGODB_URL'] = args.mongodb_url
    if args.db_name is not None: CONFIG['DB_NAME'] = args.db_name
    if args.status_collection is not None: CONFIG['STATUS_COLLECTION'] = args.status_collection
    if args.certificates_collection is not None: CONFIG['CERTIFICATES_COLLECTION'] = args.certificates_collection
    if args.csv_file is not None: CONFIG['CSV_FILE'] = args.csv_file
    
    if args.zcert_binary is not None: CONFIG['ZCERT_BINARY'] = args.zcert_binary
    if args.log_file is not None: CONFIG['LOG_FILE'] = args.log_file
    if args.issue_log_file is not None: CONFIG['ISSUE_LOG_FILE'] = args.issue_log_file
    if args.num_threads is not None: CONFIG['NUM_THREADS'] = args.num_threads
    if args.socket_timeout is not None: CONFIG['SOCKET_TIMEOUT'] = args.socket_timeout
    if args.zcert_timeout is not None: CONFIG['ZCERT_TIMEOUT'] = args.zcert_timeout
    if args.retry_enabled: CONFIG['RETRY_ENABLED'] = True 
    if args.max_retries is not None: CONFIG['MAX_RETRIES'] = args.max_retries
    if args.retry_delays is not None: CONFIG['RETRY_DELAYS'] = args.retry_delays
    if args.monitor_interval is not None: CONFIG['MONITOR_INTERVAL'] = args.monitor_interval
    if args.heartbeat_interval is not None: CONFIG['HEARTBEAT_INTERVAL'] = args.heartbeat_interval
    if args.stale_threshold is not None: CONFIG['STALE_THRESHOLD'] = args.stale_threshold

# -------------------- Pre-Flight Validations --------------------
def validate_environment():
    print("[INIT] Validating environment...")
    if not os.path.exists(CONFIG['CSV_FILE']):
        print(f"[FATAL] CSV file not found at: {CONFIG['CSV_FILE']}")
        sys.exit(1)
    if not os.path.exists(CONFIG['ZCERT_BINARY']):
        print(f"[FATAL] zcertificate binary not found at: {CONFIG['ZCERT_BINARY']}")
        sys.exit(1)
    
    # Create logs directory if missing
    log_dir = os.path.dirname(CONFIG['LOG_FILE'])
    if log_dir and not os.path.exists(log_dir):
        try:
            os.makedirs(log_dir)
            print(f"[INIT] Created log directory: {log_dir}")
        except Exception as e:
            print(f"[FATAL] Could not create log directory '{log_dir}': {e}")
            sys.exit(1)
            
    try:
        test_client = MongoClient(CONFIG['MONGODB_URL'], serverSelectionTimeoutMS=2000)
        test_client.admin.command('ping')
        print("[INIT] MongoDB connection successful.")
    except Exception as e:
        print(f"[FATAL] Could not connect to MongoDB: {e}")
        sys.exit(1)
    print("[INIT] All checks passed.")

# -------------------- Database & Setup --------------------
def init_db():
    global client, db, status_coll, certs_coll
    client = MongoClient(CONFIG['MONGODB_URL'])
    db = client[CONFIG['DB_NAME']]
    status_coll = db[CONFIG['STATUS_COLLECTION']]
    certs_coll = db[CONFIG['CERTIFICATES_COLLECTION']]
    
    status_coll.create_index([("status", ASCENDING), ("attempt_count", ASCENDING)])
    status_coll.create_index("domain", unique=True)
    status_coll.create_index("last_heartbeat")
    
    certs_coll.create_index("parsed.fingerprint_sha256")

def load_csv_if_empty():
    if status_coll.count_documents({}) > 0:
        print("[INIT] Database already populated. Skipping CSV load.")
        return

    print(f"[INIT] Loading domains from {CONFIG['CSV_FILE']}...")
    domains = []
    try:
        with open(CONFIG['CSV_FILE'], 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                domain_col = None
                for col in reader.fieldnames:
                    if col.strip().lower() in ['domain', 'domains', 'websites url']:
                        domain_col = col
                        break
                if not domain_col:
                    print(f"[FATAL] Could not find a 'domain' column in your CSV!")
                    sys.exit(1)
            else:
                print("[FATAL] CSV file appears empty.")
                sys.exit(1)

            for row in reader:
                d = row.get(domain_col, '').strip()
                if d:
                    domains.append({
                        'domain': d,
                        'status': 'pending',
                        'attempt_count': 0,
                        'last_heartbeat': None,
                        'worker_id': None
                    })
    except Exception as e:
        print(f"[ERROR] Failed to read CSV: {e}")
        sys.exit(1)
    
    if domains:
        try:
            status_coll.insert_many(domains, ordered=False)
            print(f"[INIT] Successfully loaded {len(domains)} domains.")
        except (DuplicateKeyError, BulkWriteError):
            inserted = status_coll.count_documents({})
            print(f"[INIT] Loaded with some duplicates skipped. Total in DB: {inserted}")
            pass

# -------------------- Logging Functions (V2 Style) --------------------
def log_issue(message):
    """Internal Watchdog/Thread logs"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(CONFIG['ISSUE_LOG_FILE'], "a") as f:
        f.write(f"[{timestamp}] {message}\n")

def write_activity_log(domain, log_messages):
    """Writes detailed process logs (V2 Style)"""
    if not log_messages:
        return
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        with open(CONFIG['LOG_FILE'], "a") as f:
            f.write(f"[{timestamp}] Processing {domain}\n")
            for msg in log_messages:
                f.write(f"  - {msg}\n")
            f.write("\n")

def log_failed_domain(domain, attempt_count, error_message):
    """Writes permanent failure logs (V2 Style)"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        with open(CONFIG['LOG_FILE'], "a") as f:
            f.write(f"[{timestamp}] PERMANENTLY FAILED: {domain}\n")
            f.write(f"  - Attempts: {attempt_count}/{CONFIG['MAX_RETRIES']}\n")
            f.write(f"  - Final Error: {error_message}\n")
            f.write("\n")

# -------------------- Core Functions --------------------
def get_pem_from_domain(domain):
    try:
        sock = socket.create_connection((domain, 443), timeout=CONFIG['SOCKET_TIMEOUT'])
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        with context.wrap_socket(sock, server_hostname=domain) as ssl_sock:
            der_cert = ssl_sock.getpeercert(True)
            pem_cert = ssl.DER_cert_to_PEM_cert(der_cert)
            return pem_cert, None
    except socket.timeout:
        return None, "Connection Timed Out"
    except Exception as e:
        return None, str(e)

def parse_with_zcertificate(pem_data):
    try:
        if isinstance(pem_data, bytes):
            pem_input = pem_data.decode('utf-8', errors='ignore')
        else:
            pem_input = pem_data

        process = subprocess.run(
            [CONFIG['ZCERT_BINARY'], "-format", "pem"],
            input=pem_input, 
            capture_output=True,
            text=True,
            timeout=CONFIG['ZCERT_TIMEOUT']
        )
        if process.returncode != 0:
            return None, f"zcertificate error: {process.stderr}"
        return json.loads(process.stdout), None
    except subprocess.TimeoutExpired:
        return None, "zcertificate binary Timed Out"
    except Exception as e:
        return None, f"Parsing error: {e}"

# -------------------- Scope (TLD) Extraction --------------------
def extract_tld(domain):
    """Returns the top-level domain only, e.g. 'apple.com' -> 'com' (no dot)."""
    cleaned = domain.strip().rstrip('.')
    if '.' in cleaned:
        return cleaned.rsplit('.', 1)[-1].lower()
    return cleaned.lower()


def _compute_is_leaf(parsed_data):
    """Return True if this certificate is a leaf (not self-signed, not a CA).

    Matches LEAF_EXPR from generic-compute-ca-stats.py exactly.
    """
    parsed = parsed_data.get('parsed', {}) or {}
    subject_dn = parsed.get('subject_dn') or ''
    issuer_dn = parsed.get('issuer_dn') or ''
    bc = parsed.get('basic_constraints', {}) or {}
    is_self_subject = bool(subject_dn) and subject_dn == issuer_dn
    is_ca = bc.get('ca', False) is True
    return not is_self_subject and not is_ca


# -------------------- Worker Logic --------------------
def worker_thread(worker_id):
    while not shutdown_event.is_set():
        task = status_coll.find_one_and_update(
            {"status": "pending"},
            {
                "$set": {
                    "status": "processing",
                    "worker_id": worker_id,
                    "started_at": datetime.now(),
                    "last_heartbeat": datetime.now()
                }
            },
            sort=[("attempt_count", ASCENDING)],
            return_document=ReturnDocument.AFTER
        )
        
        if not task:
            time.sleep(2)
            continue
            
        domain = task['domain']
        attempts = task['attempt_count']
        
        attempt_msg = f"(Try {attempts+1})" if attempts > 0 else ""
        print(f"[{worker_id}] Processing {domain} {attempt_msg}...")

        # Process
        status_coll.update_one({"_id": task["_id"]}, {"$set": {"last_heartbeat": datetime.now()}})
        pem, error = get_pem_from_domain(domain)
        
        if not error:
            status_coll.update_one({"_id": task["_id"]}, {"$set": {"last_heartbeat": datetime.now()}})
            parsed_data, error = parse_with_zcertificate(pem)
            
            if not error and parsed_data:
                parsed_data.pop('raw', None)
                parsed_data['domain'] = domain
                parsed_data['scope'] = extract_tld(domain)
                parsed_data['scanned_at'] = datetime.now()
                parsed_data['is_leaf'] = _compute_is_leaf(parsed_data)

                certs_coll.insert_one(parsed_data)
                print(f"[{worker_id}] {domain} -> SUCCESS")
                status_coll.update_one(
                    {"_id": task["_id"]},
                    {"$set": {"status": "completed", "completed_at": datetime.now(), "error": None}}
                )
                continue 

        # --- FAILURE HANDLING & LOGGING ---
        attempts += 1
        should_retry = False
        
        write_activity_log(domain, [f"Error on attempt {attempts}: {error}"])
        
        if CONFIG['RETRY_ENABLED'] and attempts < CONFIG['MAX_RETRIES']:
            should_retry = True
            
        if should_retry:
            delay_index = attempts - 1
            if delay_index < len(CONFIG['RETRY_DELAYS']):
                delay_sec = CONFIG['RETRY_DELAYS'][delay_index]
            else:
                delay_sec = CONFIG['RETRY_DELAYS'][-1]

            print(f"[{worker_id}] {domain} -> FAILED: {error}. Waiting {delay_sec}s...")
            time.sleep(delay_sec)
            
            status_coll.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "status": "pending",
                        "attempt_count": attempts,
                        "last_error": error,
                        "worker_id": None
                    }
                }
            )
        else:
            print(f"[{worker_id}] {domain} -> PERMANENTLY FAILED")
            log_failed_domain(domain, attempts, error)
            
            status_coll.update_one(
                {"_id": task["_id"]},
                {
                    "$set": {
                        "status": "failed",
                        "attempt_count": attempts,
                        "last_error": error,
                        "failed_at": datetime.now()
                    }
                }
            )

# -------------------- Doctor & Dashboard --------------------
def doctor_thread():
    print("[DOCTOR] System health monitor started.")
    while not shutdown_event.is_set():
        try:
            cutoff = datetime.now() - timedelta(seconds=CONFIG['STALE_THRESHOLD'])
            stale = list(status_coll.find({"status": "processing", "last_heartbeat": {"$lt": cutoff}}))
            for task in stale:
                msg = f"Freeze Detected: {task['domain']} (Worker: {task.get('worker_id')})"
                print(f"[DOCTOR] {msg}")
                log_issue(msg)
                status_coll.update_one(
                    {"_id": task["_id"]},
                    {"$set": {"status": "pending", "worker_id": None, "last_error": "Watchdog Reset"}}
                )
            
            active = threading.active_count() - 2
            if active < CONFIG['NUM_THREADS']:
                missing = CONFIG['NUM_THREADS'] - active
                if missing > 0:
                    for i in range(missing):
                        threading.Thread(target=worker_thread, args=(f"Rescue-{int(time.time())}-{i}",), daemon=True).start()
            time.sleep(5)
        except Exception as e:
            print(f"[DOCTOR] Error: {e}")
            time.sleep(5)

def dashboard_loop():
    start_time = time.time()
    while not shutdown_event.is_set():
        time.sleep(CONFIG['MONITOR_INTERVAL'])
        stats = {
            "pending": status_coll.count_documents({"status": "pending"}),
            "processing": status_coll.count_documents({"status": "processing"}),
            "completed": status_coll.count_documents({"status": "completed"}),
            "duplicated": status_coll.count_documents({"status": "duplicated because of fingerprint"}),
            "failed": status_coll.count_documents({"status": "failed"})
        }
        if stats['pending'] == 0 and stats['processing'] == 0:
            print("\n[DONE] All tasks finished. Exiting...")
            shutdown_event.set()
            break

        total_done = stats['completed'] + stats['failed'] + stats['duplicated']
        elapsed = time.time() - start_time
        speed = total_done / elapsed if elapsed > 0 else 0
        remaining = stats['pending'] + stats['processing']
        eta_min = (remaining / speed) / 60 if speed > 0 else 0
        
        print("-" * 75)
        print(f"[STATUS] Speed: {speed:.1f}/sec | ETA: {eta_min:.1f} min")
        print(f"  Queue: {stats['pending']} | Working: {stats['processing']} | Done: {stats['completed']} | Dupes: {stats['duplicated']} | Fail: {stats['failed']}")
        print("-" * 75)

def main():
    parse_arguments()
    
    signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
    print("="*75)
    print("      FINAL HYBRID CRAWLER (V3 + V2 LOGS + ALL CLI ARGS + DUPE TRACKING)")
    print("="*75)
    validate_environment()
    init_db()
    load_csv_if_empty()
    threading.Thread(target=doctor_thread, daemon=True).start()
    print(f"[INIT] Spawning {CONFIG['NUM_THREADS']} worker threads...")
    for i in range(CONFIG['NUM_THREADS']):
        threading.Thread(target=worker_thread, args=(f"Worker-{i}",), daemon=True).start()
    dashboard_loop()

if __name__ == "__main__":
    main()