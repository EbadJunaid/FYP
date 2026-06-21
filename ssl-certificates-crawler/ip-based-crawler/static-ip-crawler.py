#!/usr/bin/env python3
"""
SSL Certificate Crawler for Pakistan IP Ranges
Scans IPs from CIDR blocks and stores SSL certificates in MongoDB
Uses zcertificate for certificate parsing
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
DATABASE_NAME = "ssl-certificates-4"
COLLECTION_NAME = "pk-certificates"

CSV_FILE = "ip-ranges-1.csv"  # Hardcoded CSV file path
ZCERTIFICATE_PATH = "./zcertificate"

SCAN_TIMEOUT = 3  # seconds
HTTPS_PORT = 443
MAX_WORKERS = 20  # Parallel scanning threads


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
def get_ssl_certificate_pem(ip, port=HTTPS_PORT, timeout=SCAN_TIMEOUT):
    """
    Attempt to retrieve SSL certificate from an IP address in PEM format
    Returns: (status, pem_data, error_message)
    """
    try:
        # Create socket with timeout
        sock = socket.create_connection((ip, port), timeout=timeout)
        
        try:
            # Create SSL context
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            # Wrap socket with SSL
            ssl_sock = context.wrap_socket(sock, server_hostname=ip)
            
            # Get certificate in DER format and convert to PEM
            cert_der = ssl_sock.getpeercert(binary_form=True)
            pem_data = ssl.DER_cert_to_PEM_cert(cert_der)
            
            ssl_sock.close()
            sock.close()
            
            return ("has_ssl", pem_data, None)
        
        except ssl.SSLError as e:
            sock.close()
            return ("ssl_error", None, f"SSL Error: {str(e)}")
    
    except socket.timeout:
        return ("timeout", None, "Connection timed out")
    
    except ConnectionRefusedError:
        return ("no_service", None, "Connection refused - No service on port 443")
    
    except OSError as e:
        return ("error", None, f"Connection error: {str(e)}")
    
    except Exception as e:
        return ("error", None, f"Unexpected error: {str(e)}")


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


# ==================== Scanning Functions ====================
def scan_single_ip(ip_str, collection):
    """Scan a single IP and store result in MongoDB"""
    
    status, pem_data, error_msg = get_ssl_certificate_pem(ip_str)
    
    # Prepare document for MongoDB
    document = {
        "ip": ip_str,
        "scan_date": datetime.utcnow(),
        "status": status
    }
    
    if status == "has_ssl" and pem_data:
        # Run zcertificate to parse the certificate
        parsed_cert, zcert_error = run_zcertificate_on_pem(pem_data)
        
        if parsed_cert:
            document["certificate"] = parsed_cert
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


def load_cidrs_from_csv():
    """Load CIDR blocks from CSV file"""
    cidrs = []
    try:
        with open(CSV_FILE, 'r', encoding='utf-8') as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                if row:
                    cidr = row[0].strip()
                    if cidr:
                        cidrs.append(cidr)
        
        print(f"✓ Loaded {len(cidrs)} CIDR blocks from {CSV_FILE}")
        return cidrs
    
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


# ==================== Main Scanning Logic ====================
def scan_cidr(cidr, cidr_num, total_cidrs, collection, max_workers=MAX_WORKERS):
    """Scan all IPs in a single CIDR block"""
    
    ips = get_ips_from_cidr(cidr)
    total_ips = len(ips)
    
    if total_ips == 0:
        print(f"\n⚠️  [CIDR {cidr_num}/{total_cidrs}] {cidr} - No valid IPs, skipping...")
        return {
            "has_ssl": 0,
            "no_service": 0,
            "timeout": 0,
            "ssl_error": 0,
            "zcert_error": 0,
            "error": 0,
            "total_ips": 0
        }
    
    print(f"\n{'='*80}")
    print(f"📡 CIDR {cidr_num}/{total_cidrs}: {cidr}")
    print(f"   Total IPs to scan: {total_ips:,}")
    print(f"{'='*80}")
    
    # Statistics for this CIDR
    stats = {
        "has_ssl": 0,
        "no_service": 0,
        "timeout": 0,
        "ssl_error": 0,
        "zcert_error": 0,
        "error": 0
    }
    
    completed = 0
    start_time = time.time()
    
    # Parallel scanning with thread pool
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ip = {
            executor.submit(scan_single_ip, ip, collection): ip 
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
                      f"✓SSL: {stats['has_ssl']} | ✗NoSvc: {stats['no_service']} | "
                      f"⏱TO: {stats['timeout']}", end='', flush=True)
    
    # Print final stats for this CIDR
    elapsed = time.time() - start_time
    print(f"\n\n   ✅ CIDR {cidr} completed in {elapsed:.1f}s")
    print(f"   ├─ SSL Certificates: {stats['has_ssl']}")
    print(f"   ├─ No Service:       {stats['no_service']}")
    print(f"   ├─ Timeouts:         {stats['timeout']}")
    print(f"   ├─ SSL Errors:       {stats['ssl_error']}")
    print(f"   ├─ ZCert Errors:     {stats['zcert_error']}")
    print(f"   └─ Other Errors:     {stats['error']}")
    
    stats["total_ips"] = total_ips
    return stats


def scan_all_cidrs(cidrs, collection, max_workers=MAX_WORKERS):
    """Scan all CIDRs one by one"""
    
    total_cidrs = len(cidrs)
    
    # Calculate total IPs across all CIDRs
    print(f"\n⏳ Calculating total IPs across all CIDRs...")
    total_ips_all = 0
    for cidr in cidrs:
        total_ips_all += get_cidr_ip_count(cidr)
    
    print(f"\n{'='*80}")
    print(f"🚀 SSL CERTIFICATE SCAN - STARTING")
    print(f"{'='*80}")
    print(f"   Total CIDRs to process: {total_cidrs}")
    print(f"   Total IPs to scan:      {total_ips_all:,}")
    print(f"   Parallel workers:       {max_workers}")
    print(f"   Timeout per IP:         {SCAN_TIMEOUT}s")
    print(f"{'='*80}")
    
    # Global statistics
    global_stats = {
        "has_ssl": 0,
        "no_service": 0,
        "timeout": 0,
        "ssl_error": 0,
        "zcert_error": 0,
        "error": 0,
        "total_ips": 0
    }
    
    global_start_time = time.time()
    
    # Process each CIDR
    for idx, cidr in enumerate(cidrs, 1):
        cidr_stats = scan_cidr(cidr, idx, total_cidrs, collection, max_workers)
        
        # Accumulate global stats
        for key in global_stats:
            global_stats[key] += cidr_stats.get(key, 0)
        
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
    print(f"📋 Total CIDRs Processed: {total_cidrs}")
    print(f"🔍 Total IPs Scanned: {global_stats['total_ips']:,}")
    
    if total_elapsed > 0:
        avg_rate = global_stats['total_ips'] / total_elapsed
        print(f"⚡ Average Rate: {avg_rate:.1f} IPs/second")
    
    print(f"\n📊 FINAL RESULTS SUMMARY:")
    print(f"   ┌{'─'*40}┐")
    print(f"   │ ✓ SSL Certificates Found: {global_stats['has_ssl']:>10,} │")
    print(f"   │ ✗ No Service (Port 443):  {global_stats['no_service']:>10,} │")
    print(f"   │ ⏱ Connection Timeouts:    {global_stats['timeout']:>10,} │")
    print(f"   │ ⚠ SSL Handshake Errors:   {global_stats['ssl_error']:>10,} │")
    print(f"   │ ⚠ ZCertificate Errors:    {global_stats['zcert_error']:>10,} │")
    print(f"   │ ❌ Other Errors:           {global_stats['error']:>10,} │")
    print(f"   └{'─'*40}┘")
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
    
    # Load CIDRs from hardcoded CSV file
    cidrs = load_cidrs_from_csv()
    
    if len(cidrs) == 0:
        print("❌ No CIDRs found in CSV file!")
        sys.exit(1)
    
    # Start scanning (no confirmation needed)
    scan_all_cidrs(cidrs, collection)
    
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