#!/usr/bin/env python3
"""
SSL Certificate Crawler for Pakistan IP Ranges
Scans IPs from CIDR blocks (or a plain IP list) and stores SSL certificates in MongoDB
Uses zcertificate for certificate parsing

NOTE ON THE SNI OPTION:
This script can optionally send "example.com" as the SNI value during the
TLS handshake instead of sending no SNI at all. Be aware that on many
servers, especially shared hosting and CDN setups, sending an SNI value
the server doesn't recognize causes the TLS handshake to fail outright
(no certificate at all), rather than returning a certificate. Other
servers will fall back to a default/unrelated certificate. Either way,
a certificate returned under a fake SNI is not necessarily the
certificate for any real site hosted on that IP. This option is provided
as requested for experimentation/comparison, not because it's guaranteed
to produce more or better results than no-SNI mode.
"""

import ssl
import socket
import csv
import ipaddress
import json
import subprocess
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymongo import MongoClient
import sys
import time

# ==================== CONFIGURATION ====================
MONGODB_URI = "mongodb://localhost:27017/"
DATABASE_NAME = "ip-based-crawler-interactive"
COLLECTION_NAME = "pk-certificates"

CSV_FILE = "pk-ip-ranges-mini.csv"  # Hardcoded CSV file path
ZCERTIFICATE_PATH = "../../binaries/zcertificate"

SCAN_TIMEOUT = 3  # seconds
HTTPS_PORT = 443
MAX_WORKERS = 40  # Parallel scanning threads

DUMMY_SNI_HOSTNAME = "example.com"

# All possible status values a scan result can have. Used to initialize
# every stats dict consistently so per-block and global totals can never
# drift out of sync with each other.
STATUS_KEYS = [
    "has_ssl",
    "no_service_port_443",
    "timeout",
    "tls_timeout",
    "ssl_error",
    "zcert_error",
    "error",
]


def empty_stats():
    """Return a fresh stats dict with every known status key set to 0."""
    return {key: 0 for key in STATUS_KEYS}


# ==================== Pre-flight Checks ====================
def check_zcertificate():
    """Check if zcertificate binary exists and is executable"""
    if not os.path.isfile(ZCERTIFICATE_PATH):
        print(f"❌ Error: zcertificate binary not found at '{ZCERTIFICATE_PATH}'")
        print("   Please ensure the zcertificate binary is in the current directory")
        sys.exit(1)

    # Check if it's executable
    if not os.access(ZCERTIFICATE_PATH, os.X_OK):
        print(f"❌ Error: zcertificate binary is not executable")
        print(f"   Run: chmod +x {ZCERTIFICATE_PATH}")
        sys.exit(1)

    print(f"✓ zcertificate binary found at '{ZCERTIFICATE_PATH}'")


def check_csv_file():
    """Check if CSV file exists"""
    if not os.path.isfile(CSV_FILE):
        print(f"❌ Error: CSV file not found at '{CSV_FILE}'")
        print("   Please ensure the CIDR CSV file exists in the current directory")
        sys.exit(1)

    print(f"✓ CSV file found at '{CSV_FILE}'")


# ==================== User Input Prompts ====================
def prompt_scan_mode():
    """
    Ask the user whether the CSV contains CIDR blocks or plain individual IPs.
    Returns: "cidr" or "ip"
    """
    print("\n" + "=" * 80)
    print("   SCAN MODE SELECTION")
    print("=" * 80)
    print("   The CSV file can contain either:")
    print("     1) CIDR notation blocks   (e.g. 103.255.0.0/24)")
    print("     2) Plain individual IPs   (e.g. 103.255.0.1)")
    print("=" * 80)

    while True:
        choice = input("\n👉 Does your CSV contain CIDR blocks or plain IPs? [cidr/ip]: ").strip().lower()
        if choice in ("cidr", "c"):
            return "cidr"
        elif choice in ("ip", "i"):
            return "ip"
        else:
            print("   ⚠️  Please type 'cidr' or 'ip'.")


def prompt_sni_mode():
    """
    Ask the user whether to send a dummy SNI (example.com) during the TLS
    handshake, or connect with no SNI at all.
    Returns: True if dummy SNI should be used, False for no SNI.
    """
    print("\n" + "=" * 80)
    print("   SNI MODE SELECTION")
    print("=" * 80)
    print(f"   Option 1: Send '{DUMMY_SNI_HOSTNAME}' as the SNI field during the TLS handshake")
    print("             ⚠️  Note: many servers (shared hosting / CDNs) will reject an")
    print("                 unrecognized SNI outright, resulting in a handshake failure")
    print("                 rather than a certificate. Others may return a default or")
    print("                 unrelated certificate. Results under this mode should be")
    print("                 interpreted with that caveat in mind.")
    print("   Option 2: Connect with no SNI field at all (server picks its default cert)")
    print("=" * 80)

    while True:
        choice = input(f"\n👉 Use '{DUMMY_SNI_HOSTNAME}' as SNI? [yes/no]: ").strip().lower()
        if choice in ("yes", "y"):
            return True
        elif choice in ("no", "n"):
            return False
        else:
            print("   ⚠️  Please type 'yes' or 'no'.")


# ==================== MongoDB Setup ====================
def setup_mongodb():
    """Initialize MongoDB connection and create indexes"""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.admin.command('ping')

        db = client[DATABASE_NAME]
        collection = db[COLLECTION_NAME]

        # Create index on IP for faster lookups
        collection.create_index("ip", unique=True)

        print(f"✓ Connected to MongoDB: {MONGODB_URI}")
        print(f"✓ Database: {DATABASE_NAME}, Collection: {COLLECTION_NAME}")
        return collection

    except Exception as e:
        print(f"❌ MongoDB Connection Failed: {e}")
        print("   Make sure MongoDB is running on localhost:27017")
        sys.exit(1)


# ==================== SSL Certificate Functions ====================
def get_ssl_certificate_pem(ip, use_dummy_sni, port=HTTPS_PORT, timeout=SCAN_TIMEOUT):
    """
    Attempt to retrieve SSL certificate from an IP address in PEM format.
    If use_dummy_sni is True, sends DUMMY_SNI_HOSTNAME as the SNI value.
    Otherwise, connects with no SNI field (server_hostname=None).

    This function distinguishes between the TCP layer and the TLS layer,
    since a failure at each layer means something different:

      TCP layer:
        - timeout        -> no reply at all (SYN sent, nothing comes back).
                             Most consistent with "host is unreachable/dead".
        - no_service_port_443 -> got a TCP RST. Host is alive and reachable,
                             but nothing is listening on port 443.

      TLS layer (only reached if the TCP handshake succeeded, i.e. the
      host IS alive and port 443 IS open/listening):
        - tls_timeout     -> TCP connected fine, but nothing came back during
                             the TLS handshake itself. Status is reported
                             neutrally because a timeout at this stage has
                             several possible causes that look identical
                             from the outside (overloaded/slow server,
                             unrelated network packet loss, or a WAF/firewall
                             silently dropping the handshake, possibly
                             triggered by the missing/dummy SNI or by
                             fingerprintable characteristics of Python's TLS
                             ClientHello). We cannot tell these apart from a
                             timeout alone, so the suspected cause is recorded
                             separately in a "note" field rather than baked
                             into the status itself.
        - ssl_error       -> TLS handshake completed an exchange but failed
                             with a protocol-level SSL error (e.g. handshake
                             alert, unsupported protocol/cipher mismatch).
        - has_ssl         -> TLS handshake succeeded, certificate retrieved.

    Returns: (status, pem_data, error_message, note)
    """
    try:
        # ---- TCP LAYER ----
        sock = socket.create_connection((ip, port), timeout=timeout)

    except socket.timeout:
        # No response at all at the TCP layer -> host appears dead/unreachable.
        return ("timeout", None, "No response to TCP handshake (connection timed out)", None)

    except ConnectionRefusedError:
        # TCP RST received -> host is alive, but port 443 has nothing listening.
        return ("no_service_port_443", None, "TCP RST received - host alive but port 443 not listening", None)

    except OSError as e:
        # Other TCP-layer failures (e.g. network unreachable, no route to host).
        return ("error", None, f"TCP connection error: {str(e)}", None)

    except Exception as e:
        return ("error", None, f"Unexpected error during TCP connect: {str(e)}", None)

    # ---- TLS LAYER ---- (only reached if TCP connect succeeded above)
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        # server_hostname controls the SNI field sent in the handshake.
        # Passing None disables SNI entirely.
        sni_value = DUMMY_SNI_HOSTNAME if use_dummy_sni else None
        ssl_sock = context.wrap_socket(sock, server_hostname=sni_value)

        # Get certificate in DER format and convert to PEM
        cert_der = ssl_sock.getpeercert(binary_form=True)
        pem_data = ssl.DER_cert_to_PEM_cert(cert_der)

        ssl_sock.close()
        sock.close()

        return ("has_ssl", pem_data, None, None)

    except socket.timeout:
        sock.close()
        note = (
            "TCP handshake succeeded (port 443 is open) but the TLS handshake "
            "itself received no response. Possible causes include an "
            "overloaded/slow server, unrelated network packet loss, or a "
            "WAF/firewall silently dropping the handshake (potentially "
            "triggered by the missing/dummy SNI or by fingerprintable "
            "characteristics of this script's TLS ClientHello). This cannot "
            "be determined from a timeout alone."
        )
        return ("tls_timeout", None, "TLS handshake timed out after TCP connect succeeded", note)

    except ssl.SSLError as e:
        sock.close()
        return ("ssl_error", None, f"SSL Error: {str(e)}", None)

    except OSError as e:
        sock.close()
        return ("error", None, f"Connection error during TLS handshake: {str(e)}", None)

    except Exception as e:
        sock.close()
        return ("error", None, f"Unexpected error during TLS handshake: {str(e)}", None)


def run_zcertificate_on_pem(pem_data):
    """Run zcertificate tool on PEM data and return parsed JSON."""
    try:
        process = subprocess.Popen(
            [ZCERTIFICATE_PATH, "-format", "pem"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(input=pem_data.encode())

        if process.returncode != 0:
            return None, f"zcertificate failed with return code {process.returncode}"

        parsed_json = json.loads(stdout)
        return parsed_json, None

    except json.JSONDecodeError as e:
        return None, f"Failed to parse zcertificate output: {e}"
    except Exception as e:
        return None, f"Error running zcertificate: {e}"


def strip_raw_fields(obj):
    """
    Recursively remove any key literally named 'raw' from a parsed
    certificate JSON structure (dict or list, at any nesting depth),
    since the user does not want raw certificate bytes stored in MongoDB.
    """
    if isinstance(obj, dict):
        return {
            key: strip_raw_fields(value)
            for key, value in obj.items()
            if key != "raw"
        }
    elif isinstance(obj, list):
        return [strip_raw_fields(item) for item in obj]
    else:
        return obj


# ==================== Scanning Functions ====================
def scan_single_ip(ip_str, collection, use_dummy_sni):
    """Scan a single IP and store result in MongoDB"""

    status, pem_data, error_msg, note = get_ssl_certificate_pem(ip_str, use_dummy_sni)

    # Prepare document for MongoDB
    document = {
        "ip": ip_str,
        "scan_date": datetime.utcnow(),
        "status": status,
        "sni_mode": DUMMY_SNI_HOSTNAME if use_dummy_sni else "none"
    }

    if note:
        document["note"] = note

    if status == "has_ssl" and pem_data:
        # Run zcertificate to parse the certificate
        parsed_cert, zcert_error = run_zcertificate_on_pem(pem_data)

        if parsed_cert:
            # Strip any 'raw' fields (at any nesting depth) before storing
            document["certificate"] = strip_raw_fields(parsed_cert)
        else:
            # zcertificate failed, update status
            document["status"] = "zcert_error"
            document["error"] = zcert_error

    if error_msg:
        document["error"] = error_msg

    # Insert or update in MongoDB
    try:
        collection.update_one(
            {"ip": ip_str},
            {"$set": document},
            upsert=True
        )
    except Exception as e:
        pass  # Silently handle MongoDB errors to not clutter output

    return {
        "ip": ip_str,
        "status": document["status"],
        "has_cert": "certificate" in document
    }


def load_entries_from_csv():
    """Load entries (CIDR blocks or plain IPs) from CSV file. Format-agnostic."""
    entries = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if row:
                    entry = row[0].strip()
                    if entry:
                        entries.append(entry)

        print(f"✓ Loaded {len(entries)} entries from {CSV_FILE}")
        return entries

    except Exception as e:
        print(f"❌ Error reading CSV: {e}")
        sys.exit(1)


def get_ips_from_cidr(cidr):
    """Get list of IPs from a single CIDR block"""
    try:
        network = ipaddress.IPv4Network(cidr, strict=False)
        return [str(ip) for ip in network.hosts()]
    except ValueError as e:
        print(f"   ⚠️  Invalid CIDR '{cidr}': {e}")
        return []


def get_cidr_ip_count(cidr):
    """Get the number of usable IPs in a CIDR block"""
    try:
        network = ipaddress.IPv4Network(cidr, strict=False)
        # num_addresses - 2 for network and broadcast, but hosts() handles this
        return max(0, network.num_addresses - 2)
    except ValueError:
        return 0


def validate_plain_ip(ip_str):
    """Validate a plain IP entry. Returns the IP string if valid, else None."""
    try:
        ipaddress.IPv4Address(ip_str)
        return ip_str
    except ValueError:
        print(f"   ⚠️  Invalid IP '{ip_str}', skipping...")
        return None


# ==================== Main Scanning Logic ====================
def scan_block(ips, label, block_num, total_blocks, collection, use_dummy_sni, max_workers=MAX_WORKERS):
    """Scan all IPs belonging to a single CIDR block (or a single plain IP, treated as a block of 1)"""

    total_ips = len(ips)

    if total_ips == 0:
        print(f"\n⚠️  [{block_num}/{total_blocks}] {label} - No valid IPs, skipping...")
        stats = empty_stats()
        stats["total_ips"] = 0
        return stats

    print(f"\n{'='*80}")
    print(f"📡 [{block_num}/{total_blocks}] {label}")
    print(f"   Total IPs to scan: {total_ips:,}")
    print(f"{'='*80}")

    # Statistics for this block
    stats = empty_stats()

    completed = 0
    start_time = time.time()

    # Parallel scanning with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ip = {
            executor.submit(scan_single_ip, ip, collection, use_dummy_sni): ip
            for ip in ips
        }

        # Process completed tasks
        for future in as_completed(future_to_ip):
            completed += 1
            result = future.result()

            # Update statistics
            status = result['status']
            if status in stats:
                stats[status] += 1

            # Progress indicator every 50 IPs or at completion
            if completed % 50 == 0 or completed == total_ips:
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                eta_seconds = (total_ips - completed) / rate if rate > 0 else 0

                # Format ETA nicely
                if eta_seconds > 60:
                    eta_str = f"{eta_seconds/60:.1f}m"
                else:
                    eta_str = f"{eta_seconds:.0f}s"

                # Progress bar
                progress_pct = completed * 100 / total_ips
                bar_width = 20
                filled = int(bar_width * completed / total_ips)
                bar = "█" * filled + "░" * (bar_width - filled)

                print(f"\r   [{bar}] {completed:,}/{total_ips:,} ({progress_pct:.1f}%) | "
                      f"Rate: {rate:.1f}/s | ETA: {eta_str} | "
                      f"✓SSL: {stats['has_ssl']} | ✗NoSvc443: {stats['no_service_port_443']} | "
                      f"⏱TO: {stats['timeout']} | ⏱TLS-TO: {stats['tls_timeout']}", end='', flush=True)

    # Print final stats for this block
    elapsed = time.time() - start_time
    print(f"\n\n   ✅ {label} completed in {elapsed:.1f}s")
    print(f"   ├─ SSL Certificates:      {stats['has_ssl']}")
    print(f"   ├─ No Service (Port 443): {stats['no_service_port_443']}")
    print(f"   ├─ TCP Timeouts (Dead):   {stats['timeout']}")
    print(f"   ├─ TLS Timeouts:          {stats['tls_timeout']}")
    print(f"   ├─ SSL Errors:            {stats['ssl_error']}")
    print(f"   ├─ ZCert Errors:          {stats['zcert_error']}")
    print(f"   └─ Other Errors:          {stats['error']}")

    stats["total_ips"] = total_ips
    return stats


def scan_all(entries, scan_mode, collection, use_dummy_sni, max_workers=MAX_WORKERS):
    """Scan all entries (CIDR blocks or plain IPs) one by one"""

    total_blocks = len(entries)

    # Calculate total IPs across all entries, and build per-block label/IP lists
    print(f"\n⏳ Calculating total IPs to scan...")

    blocks = []  # list of (label, [ips])
    total_ips_all = 0

    if scan_mode == "cidr":
        for cidr in entries:
            count = get_cidr_ip_count(cidr)
            total_ips_all += count
            blocks.append(("cidr", cidr))
    else:  # scan_mode == "ip"
        for ip_str in entries:
            valid_ip = validate_plain_ip(ip_str)
            if valid_ip:
                total_ips_all += 1
                blocks.append(("ip", valid_ip))

    print(f"\n{'='*80}")
    print(f"🚀 SSL CERTIFICATE SCAN - STARTING")
    print(f"{'='*80}")
    print(f"   Scan mode:               {'CIDR blocks' if scan_mode == 'cidr' else 'Plain IPs'}")
    print(f"   SNI mode:                {DUMMY_SNI_HOSTNAME if use_dummy_sni else 'None (no SNI sent)'}")
    print(f"   Total entries to process: {total_blocks}")
    print(f"   Total IPs to scan:       {total_ips_all:,}")
    print(f"   Parallel workers:        {max_workers}")
    print(f"   Timeout per IP:          {SCAN_TIMEOUT}s")
    print(f"{'='*80}")

    # Global statistics
    global_stats = empty_stats()
    global_stats["total_ips"] = 0

    global_start_time = time.time()

    # Process each block. In CIDR mode each block is one CIDR's full IP list.
    # In plain-IP mode, each block is just that single IP (so the existing
    # per-block progress/summary printing still works unchanged either way).
    for idx, (kind, value) in enumerate(blocks, 1):
        if kind == "cidr":
            ips = get_ips_from_cidr(value)
            label = value
        else:
            ips = [value]
            label = value

        block_stats = scan_block(ips, label, idx, total_blocks, collection, use_dummy_sni, max_workers)

        # Accumulate global stats
        for key in global_stats:
            global_stats[key] += block_stats.get(key, 0)

        # Show running totals
        elapsed = time.time() - global_start_time
        print(f"\n   📊 Running Total: SSL Found: {global_stats['has_ssl']} | "
              f"Elapsed: {elapsed/60:.1f}m")

    # Final global report
    total_elapsed = time.time() - global_start_time

    print(f"\n{'='*80}")
    print(f"🏁 ALL SCANS COMPLETED")
    print(f"{'='*80}")
    print(f"\n⏱️  Total Time: {total_elapsed/60:.2f} minutes ({total_elapsed:.0f} seconds)")
    print(f"📋 Total Entries Processed: {total_blocks}")
    print(f"🔍 Total IPs Scanned: {global_stats['total_ips']:,}")

    if total_elapsed > 0:
        avg_rate = global_stats['total_ips'] / total_elapsed
        print(f"⚡ Average Rate: {avg_rate:.1f} IPs/second")

    print(f"\n📊 FINAL RESULTS SUMMARY:")
    print(f"   ┌{'─'*44}┐")
    print(f"   │ ✓ SSL Certificates Found:   {global_stats['has_ssl']:>10,} │")
    print(f"   │ ✗ No Service (Port 443):    {global_stats['no_service_port_443']:>10,} │")
    print(f"   │ ⏱ TCP Timeouts (Dead IPs):  {global_stats['timeout']:>10,} │")
    print(f"   │ ⏱ TLS Timeouts:             {global_stats['tls_timeout']:>10,} │")
    print(f"   │ ⚠ SSL Handshake Errors:     {global_stats['ssl_error']:>10,} │")
    print(f"   │ ⚠ ZCertificate Errors:      {global_stats['zcert_error']:>10,} │")
    print(f"   │ ❌ Other Errors:             {global_stats['error']:>10,} │")
    print(f"   └{'─'*44}┘")
    print(f"{'='*80}\n")


# ==================== Main Entry Point ====================
def main():
    """Main function"""

    print("\n" + "="*80)
    print("   SSL CERTIFICATE CRAWLER FOR PAKISTAN IP RANGES")
    print("   Using zcertificate for certificate parsing")
    print("="*80 + "\n")

    # Pre-flight checks
    print("🔍 Running pre-flight checks...\n")
    check_zcertificate()
    check_csv_file()

    # Setup MongoDB
    collection = setup_mongodb()

    # Load entries from hardcoded CSV file (format-agnostic: CIDR or plain IP)
    entries = load_entries_from_csv()

    if len(entries) == 0:
        print("❌ No entries found in CSV file!")
        sys.exit(1)

    # Ask user what kind of entries the CSV contains
    scan_mode = prompt_scan_mode()

    # Show total IP count up front, before any scanning starts
    print(f"\n⏳ Calculating total IP count for your CSV ({scan_mode} mode)...")
    if scan_mode == "cidr":
        total_preview = sum(get_cidr_ip_count(e) for e in entries)
    else:
        total_preview = sum(1 for e in entries if validate_plain_ip(e) is not None)

    print(f"✓ Total IPs that will be scanned: {total_preview:,}")

    # Ask user whether to use the dummy SNI or no SNI at all
    use_dummy_sni = prompt_sni_mode()

    # Confirm settings before starting
    print("\n" + "=" * 80)
    print("   READY TO SCAN")
    print("=" * 80)
    print(f"   Mode:        {'CIDR blocks' if scan_mode == 'cidr' else 'Plain IPs'}")
    print(f"   Total IPs:   {total_preview:,}")
    print(f"   SNI:         {DUMMY_SNI_HOSTNAME if use_dummy_sni else 'None'}")
    print("=" * 80)
    input("\n👉 Press Enter to start scanning, or Ctrl+C to cancel...")

    # Start scanning
    scan_all(entries, scan_mode, collection, use_dummy_sni)

    # Final statistics from MongoDB
    total_docs = collection.count_documents({})
    ssl_certs = collection.count_documents({"status": "has_ssl"})

    print(f"📁 MONGODB STATUS:")
    print(f"   Total documents in collection: {total_docs:,}")
    print(f"   SSL certificates stored:       {ssl_certs:,}")
    print(f"\n✅ All data saved to MongoDB")
    print(f"   Database:   {DATABASE_NAME}")
    print(f"   Collection: {COLLECTION_NAME}")
    print(f"\n{'='*80}")
    print("   SCAN COMPLETE - Thank you for using SSL Certificate Crawler!")
    print("="*80 + "\n")


if __name__ == "__main__":
    main()