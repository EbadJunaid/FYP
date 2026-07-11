import csv
import os
import socket
import ssl
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, DuplicateKeyError
import subprocess
import json
import time
from cryptography import x509
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# ---------------- MongoDB Setup ----------------
URL = "mongodb://localhost:27017"
DB_NAME = "Cloudflare_top-100"
client = MongoClient(URL, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
db = client[DB_NAME]
collection = db["certificates"]

# ---------------- Config ----------------
LOG_FILE = "Cloudflare_urls.log"
FAILURE_FILE = "Cloudflare_urls_failures.txt"   # tracks domains that always fail
MAX_WORKERS = 5
CONNECT_TIMEOUT = 3
ZCERT_TIMEOUT = 5
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 1.2

# Locks for file thread safety
log_lock = Lock()
failure_lock = Lock()

# ============= Utility Functions =============

def write_log(domain, log_messages):
    """Write log messages for a single domain to a shared log file safely."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        with open(LOG_FILE, "a") as f:
            f.write(f"Processing {domain}\n")
            for message in log_messages:
                f.write(f"[{timestamp}] {message}\n")
            f.write("\n")
            f.flush()

def check_mongo_connection():
    try:
        client.admin.command('ping')
        return True
    except ServerSelectionTimeoutError:
        return False

def init_mongo_indexes():
    """Ensure uniqueness by domain (idempotency and deduplication)."""
    collection.create_index("domain", unique=True)

def load_domains_from_csv(file_path):
    domain_list = []
    with open(file_path, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            domain = row.get("Websites URL")
            if domain:
                domain_list.append(domain.strip())
    return domain_list

def load_failed_domains(file_path):
    failed_set = set()
    if os.path.exists(file_path):
        with open(file_path) as f:
            for line in f:
                failed_set.add(line.strip())
    return failed_set

def mark_domain_failed(domain, log_messages):
    """Record a permanent failure (thread-safe append to failure.txt)."""
    with failure_lock:
        with open(FAILURE_FILE, "a") as f:
            fail_log = f"{domain}"
            # if log_messages:
            #     fail_log += " | " + " ; ".join(log_messages)
            f.write(fail_log + "\n")
            f.flush()

# ============= Network and Certificate =============

def connect_to_domain(domain, timeout=CONNECT_TIMEOUT, log_messages=None):
    sock = None
    ssl_sock = None
    try:
        sock = socket.create_connection((domain, 443), timeout=timeout)
        sock.settimeout(timeout)
        ssl_context = ssl.create_default_context()
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname=domain)
        ssl_sock.settimeout(timeout)
        cert_bin = ssl_sock.getpeercert(binary_form=True)
        pem_data = ssl.DER_cert_to_PEM_cert(cert_bin)
        return pem_data
    except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
        if log_messages is not None:
            log_messages.append(f"Cannot connect to {domain} due to: {e}")
        return None
    except ssl.SSLError as e:
        if log_messages is not None:
            log_messages.append(f"SSL handshake failed for {domain}: {e}")
        return None
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Unexpected error for {domain}: {e}")
        return None
    finally:
        try:
            if ssl_sock:
                ssl_sock.close()
        finally:
            if sock:
                sock.close()

def run_zcertificate_on_pem(pem_data, log_messages=None):
    try:
        result = subprocess.run(
            ["zcertificate.exe", "-format", "pem"],
            input=pem_data.encode("utf-8"),
            capture_output=True,
            timeout=ZCERT_TIMEOUT,
            check=False
        )
        if result.returncode != 0:
            if log_messages is not None:
                stderr = (result.stderr or b"").decode(errors="replace").strip()
                log_messages.append(f"zcertificate exited with code {result.returncode}: {stderr}")
            return None

        stdout_text = (result.stdout or b"").decode("utf-8", errors="replace")
        if not stdout_text.strip():
            if log_messages is not None:
                log_messages.append("zcertificate produced no output")
            return None

        parsed_json = json.loads(stdout_text)
        return parsed_json

    except subprocess.TimeoutExpired:
        if log_messages is not None:
            log_messages.append(f"zcertificate timed out after {ZCERT_TIMEOUT}s")
        return None
    except json.JSONDecodeError as e:
        if log_messages is not None:
            log_messages.append(f"Failed to parse zcertificate JSON: {e}")
        return None
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error running zcertificate: {e}")
        return None

def save_certificate_to_mongodb(parsed_data, domain, log_messages=None):
    if parsed_data is None:
        return
    try:
        parsed_data["domain"] = domain
        collection.update_one(
            {"domain": domain},
            {"$set": parsed_data},
            upsert=True
        )
    except DuplicateKeyError:
        if log_messages is not None:
            log_messages.append("Duplicate domain on insert; already stored")
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error inserting/upserting into MongoDB: {e}")

def domain_already_processed(domain):
    """Check if domain already exists (success or attempted) in DB."""
    try:
        return collection.count_documents({"domain": domain}, limit=1) > 0
    except Exception:
        return False

# ============= Worker Logic =============

def process_domain_worker(domain):
    """Thread worker routine for one domain. Returns (domain, log_messages, success)."""
    log_messages = []

    if domain_already_processed(domain):
        log_messages.append("Already present in DB, skipping")
        return domain, log_messages, True

    pem_data = None
    for attempt in range(1 + MAX_RETRIES):
        pem_data = connect_to_domain(domain, timeout=CONNECT_TIMEOUT, log_messages=log_messages)
        if pem_data is not None:
            break
        if attempt < MAX_RETRIES:
            backoff = (RETRY_BACKOFF_BASE ** (attempt + 1))
            # log_messages.append(f"Retrying in {backoff:.1f}s")
            time.sleep(backoff)

    if pem_data is None:
        # All attempts failed: consider permanent failure for now, mark in file
        return domain, log_messages, False

    parsed_json = run_zcertificate_on_pem(pem_data, log_messages=log_messages)
    if parsed_json is None:
        # Could not parse cert: permanent failure
        return domain, log_messages, False

    save_certificate_to_mongodb(parsed_json, domain, log_messages=log_messages)
    return domain, log_messages, True

# ============= Main Execution =============

def main():
    start_time = time.time()

    if not check_mongo_connection():
        print("MongoDB not connected. Exiting.")
        return

    init_mongo_indexes()

    file_path = "datasets\cloudflare-radar_top-100-domains_pk_20251023-20251030.csv"
    all_domains = load_domains_from_csv(file_path)
    print(f"Total domains loaded: {len(all_domains)}")

    # Get domains already successful (from DB)
    print("Fetching already processed domains from MongoDB...")
    processed_domains = set()
    try:
        for doc in collection.find({}, {"domain": 1, "_id": 0}):
            processed_domains.add(doc["domain"])
    except Exception as e:
        print(f"Error fetching processed domains: {e}")

    # Get permanently failed domains (from failure.txt file)
    failed_domains = load_failed_domains(FAILURE_FILE)
    print(f"Loaded {len(failed_domains)} failed domains from {FAILURE_FILE}")

    # Build list to run
    remaining_domains = [d for d in all_domains if d not in processed_domains and d not in failed_domains]
    total_domains = len(remaining_domains)
    print(f"Domains remaining to process: {total_domains}")

    if total_domains == 0:
        print("All domains processed or failed. Exiting.")
        return

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = {executor.submit(process_domain_worker, domain): domain for domain in remaining_domains}

        for i, future in enumerate(as_completed(futures), start=1):
            domain = futures[future]
            try:
                dom, log_messages, success = future.result()
                # Always log what happened to this domain
                write_log(dom, log_messages)
                if not success:
                    mark_domain_failed(dom, log_messages)
            except Exception as e:
                # Catch Future exceptions to keep the pool running
                write_log(domain, [f"Future error: {e}"])
            if i % 100 == 0:
                t_now = time.time()
                print(f"Processed {i}/{total_domains} domains... Elapsed: {t_now - start_time:.2f}s")

    end_time = time.time()
    print(f"\n Total execution time: {end_time - start_time:.2f} seconds")

if __name__ == "__main__":
    main()
