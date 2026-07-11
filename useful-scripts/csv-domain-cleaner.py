### this file removes duplicate domains from a CSV file 
### and also remove domains that do not match a specific TLD (if user chooses to do so) 
### like removing other TLDs from a CSV file and just keeping one TLD like .pk 


import csv
import re
from collections import Counter

# --- 1. Read domains from CSV ---
domains = []
with open("../../ct-logs-renewal-pipeline/global-dataset.csv", "r") as f:
    reader = csv.reader(f)
    next(reader)  # skip header
    for row in reader:
        if row:  # avoid empty lines
            domains.append(row[1].strip())  # ← .strip() removes \r and spaces

# --- 2. Duplicate analysis ---
unique = set(domains)
total = len(domains)
unique_count = len(unique)
duplicate_count = total - unique_count

if duplicate_count == 0:
    print("✓ All domains are unique.")
else:
    print("✗ Duplicates found.")
    print(f"Total domains: {total}")
    print(f"Unique domains: {unique_count}")
    print(f"Duplicate count: {duplicate_count}")

    counter = Counter(domains)
    duplicates = [d for d, count in counter.items() if count > 1]
    print("\nDuplicate values:")
    for dup in duplicates:
        print(f"  {dup} (appears {counter[dup]} times)")

# --- 3. Ask to remove duplicates and save new CSV (only if duplicates exist) ---
final_domains = domains  # will hold whatever list we work with going forward

if duplicate_count > 0:
    answer = input("\nDo you want to remove duplicates and save a new CSV? (y/n): ").strip().lower()
    if answer in ('y', 'yes'):
        # Preserve order of first occurrence
        seen = set()
        unique_domains = []
        for d in domains:
            if d not in seen:
                seen.add(d)
                unique_domains.append(d)

        # ✅ FIX: lineterminator='\n' prevents \r\n Windows line endings
        output_file = "unique-domains.csv"
        with open(output_file, "w", newline='', encoding='utf-8') as f_out:
            writer = csv.writer(f_out, lineterminator='\n')  # ← FIX HERE
            writer.writerow(["index", "domain"])
            for idx, domain in enumerate(unique_domains, start=1):
                writer.writerow([idx, domain])

        print(f"\n✅ New CSV saved as '{output_file}' with {len(unique_domains)} unique domains (renumbered).")

        # Update final_domains to the deduplicated list for next step
        final_domains = unique_domains
    else:
        print("No changes made.")
else:
    print("No duplicates to remove.")


# ─────────────────────────────────────────────────────────────────────────────
# --- 4. TLD Filtering Feature ---
# ─────────────────────────────────────────────────────────────────────────────

print("\n" + "─" * 60)
tld_answer = input("\n🧹 Do you want to keep your CSV clean with only ONE TLD? (y/n): ").strip().lower()

if tld_answer in ('y', 'yes'):

    # --- 4a. Get desired TLD from user ---
    desired_tld = input("\nEnter the TLD you want to KEEP (e.g. pk, com, net): ").strip().lower()

    # Remove leading dot if user typed it (e.g. ".pk" → "pk")
    desired_tld = desired_tld.lstrip('.')

    print(f"\n🔍 Scanning for domains that do NOT end with '.{desired_tld}' ...\n")

    # --- 4b. Separate matching and non-matching domains ---
    pattern = re.compile(rf'\.{re.escape(desired_tld)}$', re.IGNORECASE)

    matching_domains     = [d for d in final_domains if pattern.search(d)]
    non_matching_domains = [d for d in final_domains if not pattern.search(d)]

    # --- 4c. Show non-matching domains ---
    if not non_matching_domains:
        print(f"✅ Great! All domains already end with '.{desired_tld}'. No action needed.")
    else:
        print(f"Found {len(non_matching_domains)} domain(s) that do NOT end with '.{desired_tld}':\n")
        for d in non_matching_domains:
            print(f"  ✗  {d}")

        print(f"\n  Total matching  '.{desired_tld}' domains : {len(matching_domains)}")
        print(f"  Total NON-matching domains             : {len(non_matching_domains)}")

        # --- 4d. Ask user to remove non-matching domains ---
        print("\n" + "─" * 60)
        remove_answer = input(f"\n🗑️  Remove all non '.{desired_tld}' domains and create a clean CSV? (y/n): ").strip().lower()

        if remove_answer in ('y', 'yes'):

            # ✅ FIX: lineterminator='\n' prevents \r\n Windows line endings
            clean_output_file = f"clean-{desired_tld}-domains.csv"
            with open(clean_output_file, "w", newline='', encoding='utf-8') as f_out:
                writer = csv.writer(f_out, lineterminator='\n')  # ← FIX HERE
                writer.writerow(["index", "domain"])
                for idx, domain in enumerate(matching_domains, start=1):
                    writer.writerow([idx, domain])

            print(f"\n✅ Clean CSV saved as '{clean_output_file}'")
            print(f"   → Contains {len(matching_domains)} domains ending with '.{desired_tld}' (renumbered from 1)")
            print(f"   → {len(non_matching_domains)} non-matching domains were removed.")

        else:
            print("\n⚠️  No changes made. Non-matching domains were NOT removed.")

else:
    print("\n⚠️  TLD filtering skipped. Your CSV remains as-is.")

print("\n" + "─" * 60)
print("✅ Script finished successfully.")
print("─" * 60)