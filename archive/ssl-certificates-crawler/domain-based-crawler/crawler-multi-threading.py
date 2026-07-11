import csv
import socket, ssl
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import subprocess
import json
import time
from cryptography import x509
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------- MongoDB Setup ----------------
URL = "mongodb://localhost:27017"
DB_NAME = "Trunco_data_Multi"
client = MongoClient(URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
collection = db["certificates"]

LOG_FILE = "domain_errors_multi.log"

# Lock to prevent threads from writing logs at the same time
log_lock = threading.Lock()

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


def check_mongo_connection():
    try:
        client.admin.command('ping')
        return True
    except ServerSelectionTimeoutError:
        return False


def load_domains_from_csv(file_path):
    domain_list = []
    with open(file_path, newline='') as file:
        reader = csv.DictReader(file)
        for row in reader:
            domain = row.get("Websites URL")
            if domain:
                domain_list.append(domain.strip())
    return domain_list


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


def save_certificate_to_mongodb(parsed_data, domain, log_messages=None):
    if parsed_data is None:
        return
    try:
        parsed_data["domain"] = domain
        result = collection.insert_one(parsed_data)
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error inserting into MongoDB: {e}")


# ---------------- Multithreading Integration ----------------

def process_domain(domain, log_file):
    """Wrapper for single-domain processing, used by threads."""
    log_messages = []
    pem_data = connect_to_domain(domain, log_messages=log_messages)

    if pem_data is not None:
        parsed_json = run_zcertificate_on_pem(pem_data, log_messages=log_messages)
        save_certificate_to_mongodb(parsed_json, domain, log_messages=log_messages)

    if log_messages:
        write_log(domain, log_messages, log_file)


def main():
    start_time = time.time()

    if not check_mongo_connection():
        print("MongoDB not connected. Exiting.")
        return

    file_path = "Websites-Domains.csv"
    domain_list = load_domains_from_csv(file_path)

    # ---------- Multithreading starts here ----------
    MAX_THREADS = 50  # You can tune this (50–100 is good for I/O tasks)
    total_domains = len(domain_list)
    print(f"Processing {total_domains} domains using {MAX_THREADS} threads...")

    with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
        futures = []
        for domain in domain_list:
            futures.append(executor.submit(process_domain, domain, LOG_FILE))

        # Progress tracking (optional but helpful)
        for i, future in enumerate(as_completed(futures), start=1):
            try:
                future.result()  # re-raise exceptions if any occur inside the thread
            except Exception as e:
                print(f"Error in thread: {e}")
            if i % 100 == 0:
                print(f"Processed {i}/{total_domains} domains...")

    # ---------- End of multithreading section ----------

    end_time = time.time()
    total_time = end_time - start_time
    print(f"\nTotal execution time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()