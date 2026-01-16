import csv
import socket
import ssl
import json
import time
import signal
import sys
import threading
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
import subprocess


# -------------------- Configuration --------------------
CONFIG = {
    'MONGODB_URL': "mongodb://localhost:27017",
    'DB_NAME': "arslan-v2",
    'CERTIFICATES_COLLECTION': "certificates",
    'STATUS_COLLECTION': "domain_processing_status",
    'METRICS_COLLECTION': "crawler_metrics",
    'CSV_FILE': "../datasets/final-dataset-mine/merged-pk-tranco-rapid.csv",
    'LOG_FILE': "../logs/new-v2.log",
    'NUM_THREADS': 30,
    'CONNECTION_TIMEOUT': 5,
    'MAX_RETRIES': 3,
    'RETRY_DELAYS': [5, 10, 15],  # seconds to wait for each retry
    'HEARTBEAT_INTERVAL': 30,  # seconds
    'STALE_THRESHOLD': 300,  # 5 minutes in seconds
    'SHUTDOWN_GRACE_PERIOD': 60  # seconds
}

# -------------------- Global State --------------------
shutdown_requested = False
active_threads = 0
threads_lock = threading.Lock()
client = None
db = None
status_collection = None
certificates_collection = None
metrics_collection = None


# -------------------- Signal Handlers --------------------
def signal_handler(signum, frame):
    global shutdown_requested
    print(f"\n[SIGNAL] Received shutdown signal ({signum}). Initiating graceful shutdown...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


# -------------------- Logging Functions --------------------
def write_log(domain, log_messages):
    """Write log messages for a domain to the log file."""
    try:
        with open(CONFIG['LOG_FILE'], "a") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] Processing {domain}\n")
            for message in log_messages:
                log_file.write(f"  - {message}\n")
            log_file.write("\n")
            log_file.flush()
    except Exception as e:
        print(f"[ERROR] Failed to write log: {e}")


def log_failed_domain(domain, attempt_count, error_message):
    """Log a permanently failed domain with timestamp."""
    try:
        with open(CONFIG['LOG_FILE'], "a") as log_file:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_file.write(f"[{timestamp}] PERMANENTLY FAILED: {domain}\n")
            log_file.write(f"  - Attempts: {attempt_count}/{CONFIG['MAX_RETRIES']}\n")
            log_file.write(f"  - Final Error: {error_message}\n")
            log_file.write("\n")
            log_file.flush()
    except Exception as e:
        print(f"[ERROR] Failed to log permanently failed domain: {e}")


# -------------------- MongoDB Setup --------------------
def init_mongodb():
    """Initialize MongoDB connection and collections."""
    global client, db, status_collection, certificates_collection, metrics_collection
    
    try:
        client = MongoClient(CONFIG['MONGODB_URL'], serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("[MONGODB] Successfully connected to MongoDB")
        
        db = client[CONFIG['DB_NAME']]
        status_collection = db[CONFIG['STATUS_COLLECTION']]
        certificates_collection = db[CONFIG['CERTIFICATES_COLLECTION']]
        metrics_collection = db[CONFIG['METRICS_COLLECTION']]
        
        # Create indexes for optimal performance
        setup_indexes()
        
        return True
    except ServerSelectionTimeoutError:
        print("[ERROR] MongoDB connection failed. Please ensure MongoDB is running.")
        return False
    except Exception as e:
        print(f"[ERROR] MongoDB initialization failed: {e}")
        return False


def setup_indexes():
    """Create necessary indexes on collections."""
    try:
        # Index for efficient work claiming
        status_collection.create_index([
            ("status", ASCENDING),
            ("attempt_count", ASCENDING)
        ], name="status_attempt_idx")
        
        # Index for domain lookup
        status_collection.create_index([("domain", ASCENDING)], unique=True, name="domain_idx")
        
        # Unique index on certificates collection to prevent duplicates
        certificates_collection.create_index([("domain", ASCENDING)], unique=True, name="cert_domain_idx")
        
        print("[MONGODB] Indexes created successfully")
    except Exception as e:
        print(f"[WARNING] Index creation warning (may already exist): {e}")


def check_and_initialize_status_table():
    """Check if status table exists and initialize if needed."""
    try:
        count = status_collection.count_documents({})
        
        if count > 0:
            print(f"[INIT] Status table already exists with {count} domains")
            print("[INIT] Checking for stale 'processing' records...")
            recover_stale_work()
            return True
        else:
            print("[INIT] Status table is empty. Loading domains from CSV...")
            return load_domains_from_csv()
            
    except Exception as e:
        print(f"[ERROR] Failed to check status table: {e}")
        return False


def load_domains_from_csv():
    """Load domains from CSV and populate status collection."""
    try:
        domain_list = []
        
        with open(CONFIG['CSV_FILE'], newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                domain = row.get("domains")
                if domain:
                    domain = domain.strip()
                    if domain:
                        domain_list.append({
                            'domain': domain,
                            'status': 'pending',
                            'attempt_count': 0,
                            'worker_id': None,
                            'error_message': None,
                            'started_at': None,
                            'completed_at': None,
                            'last_updated': datetime.now()
                        })
        
        if not domain_list:
            print("[ERROR] No domains found in CSV file")
            return False
        
        print(f"[INIT] Found {len(domain_list)} domains in CSV")
        print("[INIT] Inserting domains into status collection...")
        
        # Bulk insert with error handling for duplicates
        inserted_count = 0
        for domain_doc in domain_list:
            try:
                status_collection.insert_one(domain_doc)
                inserted_count += 1
            except DuplicateKeyError:
                # Domain already exists, skip it
                pass
            except Exception as e:
                print(f"[WARNING] Failed to insert {domain_doc['domain']}: {e}")
        
        print(f"[INIT] Successfully initialized {inserted_count} domains")
        return True
        
    except FileNotFoundError:
        print(f"[ERROR] CSV file not found: {CONFIG['CSV_FILE']}")
        return False
    except Exception as e:
        print(f"[ERROR] Failed to load domains from CSV: {e}")
        return False


def recover_stale_work():
    """Reset stale 'processing' records back to 'pending'."""
    try:
        stale_threshold = datetime.now() - timedelta(seconds=CONFIG['STALE_THRESHOLD'])
        
        result = status_collection.update_many(
            {
                'status': 'processing',
                'last_updated': {'$lt': stale_threshold}
            },
            {
                '$set': {
                    'status': 'pending',
                    'worker_id': None
                }
            }
        )
        
        if result.modified_count > 0:
            print(f"[RECOVERY] Recovered {result.modified_count} stale records")
        else:
            print("[RECOVERY] No stale records found")
            
    except Exception as e:
        print(f"[ERROR] Failed to recover stale work: {e}")


# -------------------- SSL Certificate Functions --------------------
def connect_to_domain(domain, timeout=5):
    """Connect to domain and retrieve SSL certificate in PEM format."""
    try:
        sock = socket.create_connection((domain, 443), timeout=timeout)
    except (socket.gaierror, socket.timeout, ConnectionRefusedError, OSError) as e:
        return None, f"Cannot connect to {domain}: {e}"

    try:
        ssl_context = ssl.create_default_context()
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname=domain)
        cert_bin = ssl_sock.getpeercert(binary_form=True)
        pem_data = ssl.DER_cert_to_PEM_cert(cert_bin)

        ssl_sock.close()
        sock.close()
        return pem_data, None

    except ssl.SSLError as e:
        sock.close()
        return None, f"SSL handshake failed: {e}"

    except Exception as e:
        sock.close()
        return None, f"Unexpected error: {e}"


def run_zcertificate_on_pem(pem_data):
    """Run zcertificate tool on PEM data and return parsed JSON."""
    try:
        process = subprocess.Popen(
            ["../zcertificate/zcertificate", "-format", "pem"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=pem_data.encode())
        
        if process.returncode != 0:
            return None, f"zcertificate failed with return code {process.returncode}"
        
        parsed_json = json.loads(stdout)
        return parsed_json, None
        
    except FileNotFoundError:
        return None, "zcertificate binary not found"
    except json.JSONDecodeError as e:
        return None, f"Failed to parse zcertificate output: {e}"
    except Exception as e:
        return None, f"Error running zcertificate: {e}"


def save_certificate_to_mongodb(parsed_data, domain):
    """Save parsed certificate data to MongoDB."""
    try:
        parsed_data["domain"] = domain
        certificates_collection.insert_one(parsed_data)
        return True, None
    except DuplicateKeyError:
        # Certificate already exists, consider this a success
        return True, None
    except Exception as e:
        return False, f"Error inserting into MongoDB: {e}"


# -------------------- Worker Thread Functions --------------------
def claim_work(worker_id):
    """Atomically claim a domain to process."""
    try:
        result = status_collection.find_one_and_update(
            {
                'status': 'pending',
                'attempt_count': {'$lt': CONFIG['MAX_RETRIES']}
            },
            {
                '$set': {
                    'status': 'processing',
                    'worker_id': worker_id,
                    'started_at': datetime.now(),
                    'last_updated': datetime.now()
                },
                '$inc': {'attempt_count': 1}
            },
            sort=[('attempt_count', ASCENDING), ('domain', ASCENDING)],
            return_document=True
        )
        
        return result
        
    except Exception as e:
        print(f"[ERROR] Worker {worker_id} failed to claim work: {e}")
        return None


def mark_completed(domain, worker_id):
    """Mark a domain as successfully completed."""
    try:
        status_collection.update_one(
            {'domain': domain, 'worker_id': worker_id},
            {
                '$set': {
                    'status': 'completed',
                    'completed_at': datetime.now(),
                    'last_updated': datetime.now(),
                    'error_message': None
                }
            }
        )
    except Exception as e:
        print(f"[ERROR] Failed to mark {domain} as completed: {e}")


def mark_failed(domain, worker_id, error_message, attempt_count):
    """Mark a domain as failed (either retry or permanent)."""
    try:
        if attempt_count >= CONFIG['MAX_RETRIES']:
            # Permanent failure
            status_collection.update_one(
                {'domain': domain, 'worker_id': worker_id},
                {
                    '$set': {
                        'status': 'failed',
                        'completed_at': datetime.now(),
                        'last_updated': datetime.now(),
                        'error_message': error_message
                    }
                }
            )
            # Log permanently failed domain
            log_failed_domain(domain, attempt_count, error_message)
        else:
            # Retry available
            status_collection.update_one(
                {'domain': domain, 'worker_id': worker_id},
                {
                    '$set': {
                        'status': 'pending',
                        'worker_id': None,
                        'last_updated': datetime.now(),
                        'error_message': error_message
                    }
                }
            )
    except Exception as e:
        print(f"[ERROR] Failed to mark {domain} as failed: {e}")


def process_domain(domain, worker_id, attempt_count):
    """Process a single domain: fetch cert, parse, save."""
    log_messages = []
    
    print(f"[Worker-{worker_id}] Processing {domain} (attempt {attempt_count}/{CONFIG['MAX_RETRIES']})")
    
    # Step 1: Connect and fetch certificate
    pem_data, error = connect_to_domain(domain, CONFIG['CONNECTION_TIMEOUT'])
    if error:
        log_messages.append(error)
        return False, error, log_messages
    
    # Step 2: Parse certificate using zcertificate
    parsed_json, error = run_zcertificate_on_pem(pem_data)
    if error:
        log_messages.append(error)
        return False, error, log_messages
    
    # Step 3: Save to MongoDB
    success, error = save_certificate_to_mongodb(parsed_json, domain)
    if not success:
        log_messages.append(error)
        return False, error, log_messages
    
    return True, None, log_messages


def worker_thread(worker_id):
    """Main worker thread function."""
    global active_threads, shutdown_requested
    
    with threads_lock:
        active_threads += 1
    
    print(f"[Worker-{worker_id}] Started")
    
    try:
        while not shutdown_requested:
            # Claim work
            work_item = claim_work(worker_id)
            
            if work_item is None:
                # No work available
                break
            
            domain = work_item['domain']
            attempt_count = work_item['attempt_count']
            
            # Apply retry delay if this is not the first attempt
            if attempt_count > 1:
                delay = CONFIG['RETRY_DELAYS'][attempt_count - 1]
                print(f"[Worker-{worker_id}] Retry {attempt_count} for {domain}, waiting {delay}s...")
                time.sleep(delay)
            
            # Process the domain
            success, error, log_messages = process_domain(domain, worker_id, attempt_count)
            
            if success:
                mark_completed(domain, worker_id)
                print(f"[Worker-{worker_id}] Successfully processed {domain}")
            else:
                mark_failed(domain, worker_id, error, attempt_count)
                if attempt_count < CONFIG['MAX_RETRIES']:
                    print(f"[Worker-{worker_id}] Failed {domain}, will retry (attempt {attempt_count}/{CONFIG['MAX_RETRIES']})")
                else:
                    print(f"[Worker-{worker_id}] Permanently failed {domain} after {attempt_count} attempts")
                
                # Write error logs
                if log_messages:
                    write_log(domain, log_messages)
        
        print(f"[Worker-{worker_id}] Finished (shutdown={shutdown_requested})")
        
    except Exception as e:
        print(f"[ERROR] Worker-{worker_id} crashed: {e}")
    finally:
        with threads_lock:
            active_threads -= 1


# -------------------- Monitoring Functions --------------------
def get_progress_stats():
    """Get current progress statistics."""
    try:
        pipeline = [
            {
                '$group': {
                    '_id': '$status',
                    'count': {'$sum': 1}
                }
            }
        ]
        
        results = list(status_collection.aggregate(pipeline))
        stats = {item['_id']: item['count'] for item in results}
        
        total = sum(stats.values())
        pending = stats.get('pending', 0)
        processing = stats.get('processing', 0)
        completed = stats.get('completed', 0)
        failed = stats.get('failed', 0)
        
        return {
            'total': total,
            'pending': pending,
            'processing': processing,
            'completed': completed,
            'failed': failed
        }
    except Exception as e:
        print(f"[ERROR] Failed to get progress stats: {e}")
        return None


def monitor_progress(interval=10):
    """Monitor and display progress at regular intervals."""
    global shutdown_requested
    
    print("[MONITOR] Progress monitoring started")
    start_time = time.time()
    
    while not shutdown_requested:
        time.sleep(interval)
        
        stats = get_progress_stats()
        if stats:
            elapsed = time.time() - start_time
            completed_total = stats['completed'] + stats['failed']
            
            print(f"\n[PROGRESS] Elapsed: {elapsed:.0f}s | "
                  f"Pending: {stats['pending']} | "
                  f"Processing: {stats['processing']} | "
                  f"Completed: {stats['completed']} | "
                  f"Failed: {stats['failed']} | "
                  f"Total: {stats['total']}")
            
            if completed_total > 0 and elapsed > 0:
                rate = completed_total / elapsed
                remaining = stats['pending'] + stats['processing']
                if rate > 0:
                    eta_seconds = remaining / rate
                    print(f"[PROGRESS] Rate: {rate:.2f} domains/sec | ETA: {eta_seconds:.0f}s ({eta_seconds/60:.1f}m)")
    
    print("[MONITOR] Progress monitoring stopped")


def check_completion():
    """Check if all domains have been processed."""
    try:
        stats = get_progress_stats()
        if stats:
            remaining = stats['pending'] + stats['processing']
            return remaining == 0
        return False
    except Exception as e:
        print(f"[ERROR] Failed to check completion: {e}")
        return False


# -------------------- Main Function --------------------
def main():
    global shutdown_requested
    
    print("=" * 60)
    print("SSL Certificate Crawler - Multi-threaded")
    print("=" * 60)
    
    # Initialize MongoDB
    if not init_mongodb():
        print("[FATAL] Cannot proceed without MongoDB connection")
        return
    
    # Check and initialize status table
    if not check_and_initialize_status_table():
        print("[FATAL] Failed to initialize status table")
        return
    
    # Display initial statistics
    stats = get_progress_stats()
    if stats:
        print(f"\n[STATS] Initial State:")
        print(f"  Total domains: {stats['total']}")
        print(f"  Pending: {stats['pending']}")
        print(f"  Processing: {stats['processing']}")
        print(f"  Completed: {stats['completed']}")
        print(f"  Failed: {stats['failed']}")
    
    # Check if already completed
    if check_completion():
        print("\n[INFO] All domains have already been processed!")
        print("[INFO] No work remaining. Exiting.")
        return
    
    print(f"\n[INFO] Starting {CONFIG['NUM_THREADS']} worker threads...")
    
    # Start progress monitor thread
    monitor_thread = threading.Thread(target=monitor_progress, args=(10,), daemon=True)
    monitor_thread.start()
    
    # Start worker threads
    start_time = time.time()
    workers = []
    
    for i in range(CONFIG['NUM_THREADS']):
        thread = threading.Thread(target=worker_thread, args=(i,))
        thread.start()
        workers.append(thread)
        time.sleep(0.01)  # Small delay to stagger thread starts
    
    print(f"[INFO] All {CONFIG['NUM_THREADS']} workers started")
    
    # Wait for all workers to complete
    print("[INFO] Waiting for workers to complete...")
    for thread in workers:
        thread.join()
    
    # Final statistics
    end_time = time.time()
    total_time = end_time - start_time
    
    print("\n" + "=" * 60)
    print("CRAWLING COMPLETED")
    print("=" * 60)
    
    final_stats = get_progress_stats()
    if final_stats:
        print(f"\nFinal Statistics:")
        print(f"  Total domains: {final_stats['total']}")
        print(f"  Completed: {final_stats['completed']}")
        print(f"  Failed: {final_stats['failed']}")
        print(f"  Pending: {final_stats['pending']}")
        print(f"  Processing: {final_stats['processing']}")
        print(f"\nTotal execution time: {total_time:.2f} seconds ({total_time/60:.2f} minutes)")
        
        completed_total = final_stats['completed'] + final_stats['failed']
        if completed_total > 0:
            print(f"Average rate: {completed_total/total_time:.2f} domains/second")
    
    if shutdown_requested:
        print("\n[INFO] Shutdown was requested. You can restart to continue processing.")
    
    print("\n[INFO] Check the log file for failed domains: " + CONFIG['LOG_FILE'])


if __name__ == "__main__":
    main()