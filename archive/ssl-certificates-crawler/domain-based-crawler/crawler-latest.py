import csv
import socket, ssl
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
import subprocess
import json
import time
from cryptography import x509
from datetime import datetime

# ---------------- MongoDB Setup ----------------
URL = "mongodb://localhost:27017"
DB_NAME = "my-pk-domains"
client = MongoClient(URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
collection = db["certificates"]

LOG_FILE = "crawler-latest.log"


def write_log(domain, log_messages, log_file):
    """Write log messages for a single domain to an already-open log file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_file.write(f"Processing {domain}\n")
    for message in log_messages:
        log_file.write(f"[{timestamp}] {message}\n")
    log_file.write("\n")
    log_file.flush()  # ensures logs are written even if program stops midway


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
            domain = row.get("domain")
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
            ["./zcertificate", "-format", "pem"],
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


def save_certificate_to_mongodb(parsed_data,domain, log_messages=None):
    if parsed_data is None:
        return
    try:
        parsed_data["domain"]=domain
        result = collection.insert_one(parsed_data)
    except Exception as e:
        if log_messages is not None:
            log_messages.append(f"Error inserting into MongoDB: {e}")


def main():
    start_time = time.time()

    if not check_mongo_connection():
        print("MongoDB not connected. Exiting.")
        return

    file_path = "Final-dataset-mine/merged-pk-tranco-rapid.csv"

    domain_list = load_domains_from_csv(file_path)

    # Open log file once
    with open(LOG_FILE, "a") as log_file:
        for domain in domain_list:
            log_messages = []
            print(f"Processing: {domain}")

            pem_data = connect_to_domain(domain, log_messages=log_messages)

            if pem_data is not None:
                parsed_json = run_zcertificate_on_pem(pem_data, log_messages=log_messages)
                save_certificate_to_mongodb(parsed_json, domain,log_messages=log_messages)
            if log_messages:
                write_log(domain, log_messages, log_file)

    end_time = time.time()
    total_time = end_time - start_time
    print(f"Total execution time: {total_time:.2f} seconds")


if __name__ == "__main__":
    main()
