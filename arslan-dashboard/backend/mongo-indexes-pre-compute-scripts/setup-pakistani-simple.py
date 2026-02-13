#!/usr/bin/env python3
"""
Setup Pakistani Domains Database - Simple Orchestrator
======================================================
This script:
1. Creates ALL necessary indexes (matching main database)
2. Runs original compute scripts with database name replacement
3. Verifies the setup

No modifications to original scripts - just database name replacement!

IMPORTANT: Run this from mongo-indexes-pre-compute-scripts directory
"""

import subprocess
import time
import os
import sys
from pymongo import MongoClient
from datetime import datetime

# Ensure we're in the right directory
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(script_dir)
os.chdir(script_dir)  # mongo-indexes-pre-compute-scripts directory

# Colors
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(msg):
    print(f"\n{BOLD}{'=' * 76}{RESET}")
    print(f"{BOLD}  {msg}{RESET}")
    print(f"{BOLD}{'=' * 76}{RESET}\n")

def print_step(step, msg):
    print(f"\n{BLUE}{BOLD}[STEP {step}]{RESET} {BLUE}{msg}{RESET}\n")

def run_command(cmd):
    """Run shell command and return success status"""
    try:
        subprocess.run(cmd, shell=True, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

print_header("PAKISTANI DOMAINS DATABASE SETUP")
print(f"{YELLOW}Database: pakistani-domains (7,724 certificates){RESET}")
print(f"{YELLOW}Results: pakistani-domains-results (pre-computed collections){RESET}\n")

start_time = time.time()

# ============================================================================
# STEP 1: Create ALL Indexes
# ============================================================================

print_step("1/3", "Creating ALL indexes (matching main database)...")

print(f"{BLUE}▶ Running: create-all-indexes-pakistani.js{RESET}\n")

if run_command("mongosh pakistani-domains create-all-indexes-pakistani.js"):
    print(f"\n{GREEN}✅ All 18 indexes created successfully!{RESET}")
else:
    print(f"\n{RED}❌ Index creation failed!{RESET}")
    exit(1)

print(f"\n{BOLD}{'─' * 76}{RESET}")

# ============================================================================
# STEP 2: Run Pre-Compute Scripts
# ============================================================================

print_step("2/3", "Running pre-compute scripts...")
print(f"{YELLOW}This will take ~15-20 minutes for 7,724 certificates{RESET}\n")

# List of compute scripts (in order)
scripts = [
    "compute-ca-stats.py",
    "compute-ca-analytics.py",
    "compute-signature-stats.py",
    "compute-validity-stats.py",
    "compute-validity-distribution.py",
    "compute-geographic-distribution.py",
    "compute-hash-trends.py",
    "compute-issuance-timeline.py",
    "compute-issuer-algorithm-matrix.py",
    "compute-issuer-validation-matrix.py",
    "compute-san-wildcard-breakdown.py",
    "compute-san-tld-breakdown.py",
    "compute-san-filtered-lists.py",  # Creates all 8 SAN collections at once
    "compute-shared-keys.py",
]

successful = []
failed = []

for i, script in enumerate(scripts, 1):
    print(f"\n{BLUE}{'─' * 76}{RESET}")
    print(f"{BLUE}{BOLD}[{i}/{len(scripts)}] {script}{RESET}\n")
    
    # Read original script
    if not os.path.exists(script):
        print(f"{RED}❌ Script not found: {script}{RESET}")
        failed.append(script)
        continue
    
    with open(script, 'r') as f:
        content = f.read()
    
    # Check if script needs Django environment
    needs_django = ('import django' in content or 'django.setup()' in content)
    
    # Replace database names - that's it, simple!
    modified = content.replace(
        "'tranco-latest-8-lakh'", "'pakistani-domains'"
    ).replace(
        "'tranco-latest-8-lakh-results'", "'pakistani-domains-results'"
    ).replace(
        '"tranco-latest-8-lakh"', '"pakistani-domains"'
    ).replace(
        '"tranco-latest-8-lakh-results"', '"pakistani-domains-results"'
    )
    
    # Write temp script
    temp_script = f"temp_pk_{script}"
    with open(temp_script, 'w') as f:
        f.write(modified)
    
    # Run script
    start = time.time()
    
    if needs_django:
        # For Django scripts: Add backend to PYTHONPATH and run from backend dir
        env_pythonpath = f"PYTHONPATH={backend_dir}:$PYTHONPATH"
        cmd = f"cd {backend_dir} && {env_pythonpath} python3 mongo-indexes-pre-compute-scripts/{temp_script}"
    else:
        # Regular scripts: Run from current directory
        cmd = f"python3 {temp_script}"
    
    success = run_command(cmd)
    elapsed = time.time() - start
    
    # Cleanup
    os.remove(temp_script)
    
    if success:
        print(f"\n{GREEN}✅ Completed in {elapsed:.1f}s{RESET}")
        successful.append(script)
    else:
        print(f"\n{RED}❌ Failed after {elapsed:.1f}s{RESET}")
        failed.append(script)

print(f"\n{BOLD}{'─' * 76}{RESET}")

# ============================================================================
# STEP 3: Verification
# ============================================================================

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

print(f"📊 pakistani-domains.certificates:")
print(f"   Certificates: {cert_count:,}")
print(f"   Indexes: {len(indexes)}")

if len(indexes) >= 19:
    print(f"{GREEN}   ✅ All indexes present{RESET}")
else:
    print(f"{YELLOW}   ⚠️  Expected 19, found {len(indexes)}{RESET}")
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
        print(f"   ✓ {coll.ljust(35)} {str(count).rjust(6)} docs")
else:
    print(f"{RED}   ❌ No collections found!{RESET}")

print()
print("=" * 76)

# ============================================================================
# Summary
# ============================================================================

total_time = time.time() - start_time

print_header("SETUP SUMMARY")

print(f"⏱️  Total Time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
print()
print(f"{GREEN}✅ Successful: {len(successful)}/{len(scripts)}{RESET}")

if failed:
    print(f"{RED}❌ Failed: {len(failed)}/{len(scripts)}{RESET}")
    for script in failed:
        print(f"   {RED}• {script}{RESET}")
    print()
    print(f"{YELLOW}⚠️  Some scripts failed - you may need to run them manually{RESET}")
else:
    print(f"{GREEN}✅ All scripts completed successfully!{RESET}")

print()
print(f"{BOLD}{'=' * 76}{RESET}")
print(f"{GREEN}{BOLD}✅ Pakistani domains database is ready!{RESET}")
print(f"{BOLD}{'=' * 76}{RESET}")
print()
print(f"{BLUE}Next steps:{RESET}")
print("  1. Update Django settings: settings.py")
print("  2. Change MONGODB_DB = 'pakistani-domains'")
print("  3. Change RESULTS_DB = 'pakistani-domains-results'")
print("  4. Restart backend server")
print()
