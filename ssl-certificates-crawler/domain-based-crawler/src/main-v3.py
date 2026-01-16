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
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

# -------------------- Configuration --------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG = {
    'MONGODB_URL': "mongodb://localhost:27017",
    'DB_NAME': "tranco-latest-full",
    'STATUS_COLLECTION': "domain_status",
    'CERTIFICATES_COLLECTION': "certificates",
    
    # Paths
    'CSV_FILE': os.path.join(BASE_DIR, "../datasets/tranco/raw/tranco-full-list-latest.csv"),
    'ZCERT_BINARY': os.path.join(BASE_DIR, "../zcertificate/zcertificate"),
    'LOG_FILE': os.path.join(BASE_DIR, "../logs/tranco-latest-full.log"),
    'ISSUE_LOG_FILE': os.path.join(BASE_DIR, "../logs/threads-issue-tranco.txt"),
    'NUM_THREADS': 30,
    'SOCKET_TIMEOUT': 10,
    'ZCERT_TIMEOUT': 10,
    'RETRY_ENABLED': True,
    'MAX_RETRIES': 3,
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
    certs_coll.create_index("domain", unique=True)

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
        except DuplicateKeyError:
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
    # Use lock to prevent threads from writing over each other
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
                print(f"[{worker_id}] {domain} -> SUCCESS")
                parsed_data['domain'] = domain
                parsed_data['scanned_at'] = datetime.now()
                try:
                    certs_coll.insert_one(parsed_data)
                except DuplicateKeyError:
                    pass 
                status_coll.update_one(
                    {"_id": task["_id"]},
                    {"$set": {"status": "completed", "completed_at": datetime.now(), "error": None}}
                )
                continue 

        # --- FAILURE HANDLING & LOGGING ---
        attempts += 1
        should_retry = False
        
        # Log the immediate error (V2 Style)
        # Only log if it's an error, not a success
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
            # Log the permanent failure block (V2 Style)
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
            "failed": status_coll.count_documents({"status": "failed"})
        }
        if stats['pending'] == 0 and stats['processing'] == 0:
            print("\n[DONE] All tasks finished. Exiting...")
            shutdown_event.set()
            break

        total_done = stats['completed'] + stats['failed']
        elapsed = time.time() - start_time
        speed = total_done / elapsed if elapsed > 0 else 0
        remaining = stats['pending'] + stats['processing']
        eta_min = (remaining / speed) / 60 if speed > 0 else 0
        
        print("-" * 60)
        print(f"[STATUS] Speed: {speed:.1f}/sec | ETA: {eta_min:.1f} min")
        print(f"  Queue: {stats['pending']} | Working: {stats['processing']} | Done: {stats['completed']} | Fail: {stats['failed']}")
        print("-" * 60)

def main():
    signal.signal(signal.SIGINT, lambda s, f: shutdown_event.set())
    print("="*60)
    print("      FINAL HYBRID CRAWLER (V3 + V2 LOGS)")
    print("="*60)
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