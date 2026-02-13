#!/usr/bin/env python3
"""
Complete Setup for Pakistani Domains Database
==============================================
This script:
1. Creates all necessary indexes
2. Runs all pre-compute scripts with pakistani-domains configuration
3. Verifies the setup

Usage: python3 setup-pakistani-domains-complete.py
"""

import subprocess
import sys
import os
from pymongo import MongoClient
from datetime import datetime
import time

# Colors
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(message):
    print(f"\n{BOLD}{'=' * 76}{RESET}")
    print(f"{BOLD}  {message}{RESET}")
    print(f"{BOLD}{'=' * 76}{RESET}\n")

def print_step(step, message):
    print(f"{BLUE}{BOLD}[STEP {step}]{RESET} {BLUE}{message}{RESET}\n")

def print_success(message):
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    print(f"{RED}❌ {message}{RESET}")

def print_info(message):
    print(f"{YELLOW}ℹ️  {message}{RESET}")

def run_command(command, description):
    """Run a shell command and return success status"""
    print(f"{BLUE}▶ {description}{RESET}")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=False,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Command failed with exit code {e.returncode}")
        return False

def create_indexes():
    """Create indexes on pakistani-domains database"""
    print_step("1/3", "Creating indexes on pakistani-domains database...")
    
    success = run_command(
        "mongosh pakistani-domains create-indexes-pakistani.js",
        "Running index creation script"
    )
    
    if success:
        print_success("Indexes created successfully\n")
    else:
        print_error("Failed to create indexes\n")
        return False
    
    return True

def run_precompute_scripts():
    """Run all pre-compute scripts for pakistani-domains"""
    print_step("2/3", "Running pre-compute scripts...")
    print_info("This will take approximately 15-20 minutes for ~7,700 certificates\n")
    
    # List of scripts in dependency order
    scripts = [
        ("compute-ca-stats.py", "CA Statistics"),
        ("compute-ca-analytics.py", "CA Analytics"),
        ("compute-signature-stats.py", "Signature Statistics"),
        ("compute-validity-stats.py", "Validity Statistics"),
        ("compute-validity-distribution.py", "Validity Distribution"),
        ("compute-geographic-distribution.py", "Geographic Distribution"),
        ("compute-hash-trends.py", "Hash Trends"),
        ("compute-issuance-timeline.py", "Issuance Timeline"),
        ("compute-issuer-algorithm-matrix.py", "Issuer-Algorithm Matrix"),
        ("compute-issuer-validation-matrix.py", "Issuer-Validation Matrix"),
        ("compute-san-stats.py", "SAN Statistics"),
        ("compute-san-distribution.py", "SAN Distribution"),
        ("compute-san-wildcard-breakdown.py", "SAN Wildcard Breakdown"),
        ("compute-san-tld-breakdown.py", "SAN TLD Breakdown"),
        ("compute-san-filtered-lists-v2.py", "SAN Filtered Lists"),
        ("compute-shared-keys.py", "Shared Keys Analysis"),
    ]
    
    successful = []
    failed = []
    
    for script_file, description in scripts:
        print(f"\n{BLUE}{'─' * 76}{RESET}")
        print(f"{BLUE}▶ Running: {description} ({script_file}){RESET}\n")
        
        # Read original script
        try:
            with open(script_file, 'r') as f:
                content = f.read()
        except FileNotFoundError:
            print_error(f"Script not found: {script_file}")
            failed.append((script_file, "File not found"))
            continue
        
        # Replace database names
        modified_content = content.replace(
            "'tranco-latest-8-lakh'", "'pakistani-domains'"
        ).replace(
            "'tranco-latest-8-lakh-results'", "'pakistani-domains-results'"
        ).replace(
            '"tranco-latest-8-lakh"', '"pakistani-domains"'
        ).replace(
            '"tranco-latest-8-lakh-results"', '"pakistani-domains-results"'
        )
        
        # Write temporary script
        temp_file = f"temp_pk_{script_file}"
        with open(temp_file, 'w') as f:
            f.write(modified_content)
        
        # Run the script
        start_time = time.time()
        success = run_command(
            f"python3 {temp_file}",
            f"Executing {description}"
        )
        elapsed = time.time() - start_time
        
        # Cleanup
        os.remove(temp_file)
        
        if success:
            print_success(f"Completed in {elapsed:.1f}s: {description}")
            successful.append(script_file)
        else:
            print_error(f"Failed: {description}")
            failed.append((script_file, "Execution error"))
    
    print(f"\n{BLUE}{'─' * 76}{RESET}\n")
    print_success(f"Successful: {len(successful)}/{len(scripts)}")
    
    if failed:
        print_error(f"Failed: {len(failed)}/{len(scripts)}")
        for script, reason in failed:
            print(f"  {RED}• {script} - {reason}{RESET}")
    
    return len(failed) == 0

def verify_setup():
    """Verify the setup"""
    print_step("3/3", "Verifying setup...")
    
    client = MongoClient('mongodb://localhost:27017/')
    
    print("=" * 76)
    print("VERIFICATION REPORT")
    print("=" * 76)
    print()
    
    # Check main database
    pk_db = client['pakistani-domains']
    cert_count = pk_db.certificates.count_documents({})
    indexes = list(pk_db.certificates.list_indexes())
    index_count = len(indexes)
    
    print(f"📊 pakistani-domains.certificates:")
    print(f"   Certificates: {cert_count:,}")
    print(f"   Indexes: {index_count}")
    
    if index_count >= 8:
        print_success(f"   All {index_count} indexes present")
    else:
        print_error(f"   Expected 8+ indexes, found {index_count}")
    print()
    
    # Check results database
    results_db = client['pakistani-domains-results']
    collections = sorted(results_db.list_collection_names())
    
    print(f"📊 pakistani-domains-results:")
    print(f"   Collections: {len(collections)}")
    print()
    
    if collections:
        print("Collections created:")
        for coll in collections:
            count = results_db[coll].count_documents({})
            print(f"   ✓ {coll.ljust(35)} - {count:,} documents")
    else:
        print_error("   No collections found!")
    
    print()
    print("=" * 76)
    
    return len(collections) > 0

def main():
    """Main setup function"""
    print_header("PAKISTANI DOMAINS DATABASE COMPLETE SETUP")
    
    start_time = datetime.now()
    
    # Step 1: Create indexes
    if not create_indexes():
        print_error("Setup failed at index creation")
        sys.exit(1)
    
    print(f"\n{BOLD}{'─' * 76}{RESET}\n")
    
    # Step 2: Run pre-compute scripts
    precompute_success = run_precompute_scripts()
    
    print(f"\n{BOLD}{'─' * 76}{RESET}\n")
    
    # Step 3: Verify
    verify_success = verify_setup()
    
    # Summary
    duration = (datetime.now() - start_time).total_seconds()
    
    print_header("SETUP SUMMARY")
    
    print(f"⏱️  Total Duration: {duration:.1f}s ({duration/60:.1f} minutes)")
    print()
    
    if precompute_success and verify_success:
        print_success("✅ All steps completed successfully!")
        print()
        print(f"{BLUE}Next steps:{RESET}")
        print("  1. Update Django settings to use pakistani-domains")
        print("  2. Update frontend API configurations")
        print("  3. Test dashboard with new database")
    else:
        print_error("⚠️  Setup completed with warnings")
        print()
        print("Some scripts may have failed. Check logs above.")
    
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n" + RED + "❌ Setup interrupted by user" + RESET)
        sys.exit(1)
    except Exception as e:
        print("\n\n" + RED + f"❌ Error: {e}" + RESET)
        import traceback
        traceback.print_exc()
        sys.exit(1)
