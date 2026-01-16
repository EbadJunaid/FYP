import csv
import socket, ssl
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import subprocess
import json
import time
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import os

# ---------------- MongoDB Setup ----------------
URL = "mongodb://localhost:27017"
DB_NAME = "Tranco_data_Multi"
client = MongoClient(URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
collection = db["certificates"]

# ---------------- File Names ----------------
LOG_FILE = "domain_errors_multi.log"
PROGRESS_FILE = "progress.txt"
COMPLETED_FILE = "completed.txt"
FAILED_FILE = "failed.txt"

# Locks for thread safety
log_lock = threading.Lock()
file_lock = threading.Lock()

# ---------------- Logging ----------------
def write_log(domain, log_messages, log_file):
    """Write log messages for a single domain to a shared log file safely."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with log_lock:
        with open(log_file, "a") as f:
            f.write(f"Processing {domain}\n")
            for message in log_messages:
                f.write(f"[{timestamp}] {message}\n")
            f.write("\n")
            f.flush()

# ---------------- Mongo Connection Check ----------------
def check_mongo_connection():
    try:
        client.admin.command('ping')
        return True
    except ServerSelectionTimeoutError:
        return False

# ---------------- Domain Loader ----------------
def load_domains_from_csv(file_path):
    domain_list = []
    with open(file_path, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            domain = row.get("Websites URL")
            if domain:
                domain_list.append(domain.strip())
    return domain_list

# ---------------- Network & SSL ----------------
def connect_to_domain(domain, timeout=5, log_messages=None):
    try:
        sock = socket.create_connection((domain, 443), timeout=timeout)
    except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
        if log_messages is not None:
            log_messages.append(f"Cannot connect to {domain} due to: {e}")
        return None

    try:
        ssl_context = ssl.create_default_context()
        ssl_sock = ssl_context.wrap_socket(sock, server_hostname=domain)
        cert_bin = ssl_sock.getpeercert(binary_form=True)
        pem_data = ssl.DER_cert_to_PEM_cert(cert_bin)
        ssl_sock.close()
        sock.close()
        return pem_data

    except ssl.SSLError as e:
        if log_messages is not None:
            log_messages.append(f"SSL handshake failed for {domain}: {e}")
        sock.close()
        return None

    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Unexpected error for {domain}: {e}")
        sock.close()
        return None

# ---------------- zCertificate Parsing ----------------
def run_zcertificate_on_pem(pem_data, log_messages=None):
    try:
        process = subprocess.Popen(
            ["zcertificate.exe", "-format", "pem"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=pem_data.encode())
        parsed_json = json.loads(stdout)
        return parsed_json
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error running zcertificate: {e}")
        return None

# ---------------- Mongo Save ----------------
def save_certificate_to_mongodb(parsed_data, domain, log_messages=None):
    if parsed_data is None:
        return
    try:
        parsed_data["domain"] = domain
        collection.insert_one(parsed_data)
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error inserting into MongoDB: {e}")

# ---------------- File Helpers ----------------
def mark_domain_completed(domain):
    """Mark a domain as completed safely."""
    with file_lock:
        with open(COMPLETED_FILE, "a") as f:
            f.write(domain + "\n")
            f.flush()

def mark_domain_in_progress(domain):
    """Record a domain currently being processed (for restart recovery)."""
    with file_lock:
        with open(PROGRESS_FILE, "a") as f:
            f.write(domain + "\n")
            f.flush()

def mark_domain_failed(domain):
    """Record domains that failed to connect or process."""
    with file_lock:
        with open(FAILED_FILE, "a") as f:
            f.write(domain + "\n")
            f.flush()

# ---------------- Thread Worker ----------------
def process_domain(domain, log_file):
    log_messages = []
    mark_domain_in_progress(domain)

    pem_data = connect_to_domain(domain, log_messages=log_messages)
    if pem_data is not None:
        parsed_json = run_zcertificate_on_pem(pem_data, log_messages=log_messages)
        if parsed_json:
            save_certificate_to_mongodb(parsed_json, domain, log_messages=log_messages)
            mark_domain_completed(domain)
        else:
            mark_domain_failed(domain)
    else:
        mark_domain_failed(domain)

    if log_messages:
        write_log(domain, log_messages, log_file)

# ---------------- Main Execution ----------------
def main():
    start_time = time.time()

    if not check_mongo_connection():
        print("MongoDB not connected. Exiting.")
        return

    file_path = "Websites-Domains.csv"
    all_domains = load_domains_from_csv(file_path)
    print(f"Total domains loaded: {len(all_domains)}")

    # ---------- Load already processed domains from MongoDB ----------
    print("Fetching already processed domains from MongoDB...")
    processed_domains = set()
    try:
        for doc in collection.find({}, {"domain": 1, "_id": 0}):
            processed_domains.add(doc["domain"])
    except Exception as e:
        print(f"Error fetching processed domains: {e}")

    print(f"Already processed domains: {len(processed_domains)}")

    # ---------- Load failed domains ----------
    failed_domains = set()
    if os.path.exists(FAILED_FILE):
        with open(FAILED_FILE, "r") as f:
            failed_domains = set(line.strip() for line in f if line.strip())

    print(f"Previously failed domains: {len(failed_domains)}")

    # ---------- Filter domains ----------
    remaining_domains = [d for d in all_domains if d not in processed_domains and d not in failed_domains]
    print(f"Domains remaining to process: {len(remaining_domains)}")

    if not remaining_domains:
        print("All domains already processed or failed. Exiting.")
        return

    # ---------- Multithreading ----------
    MAX_THREADS = 50
    total_domains = len(remaining_domains)
    print(f"Starting multithreaded processing with {MAX_THREADS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for domain in remaining_domains:
            futures.append(executor.submit(process_domain, domain, LOG_FILE))

        for i, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()
            except Exception as e:
                print(f"Error in thread: {e}")
            if i % 100 == 0:
                print(f"Processed {i}/{total_domains} domains...")
                t_now = time.time()
                print(f"Elapsed time: {t_now - start_time:.2f} seconds")

    end_time = time.time()
    print(f"\n✅ Total execution time: {end_time - start_time:.2f} seconds")

# ---------------- Entry Point ----------------
if __name__ == "__main__":
    main()