import csv
import json
import os
import sys

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_CSV = "all-certificates.csv"       # Your Compass Export
OUTPUT_DIR = "CSV"      # Main output folder

# Increase CSV field limit for massive certificate data
csv.field_size_limit(sys.maxsize)

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def save_artifacts(folder_name, rows, fieldnames):
    """
    Saves a subset of rows to both CSV and JSON in a specific folder.
    """
    # Create Folder
    path = os.path.join(OUTPUT_DIR, folder_name)
    if not os.path.exists(path):
        os.makedirs(path)

    # 1. Save as CSV (The "Full" version you wanted)
    csv_path = os.path.join(path, "evidence_full.csv")
    try:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
    except Exception as e:
        print(f"   [!] Error saving CSV for {folder_name}: {e}")

    # 2. Save as JSON (Dump of the CSV rows)
    # json_path = os.path.join(path, "evidence_full.json")
    # try:
    #     with open(json_path, 'w', encoding='utf-8') as f:
    #         json.dump(rows, f, indent=4)
    # except Exception as e:
    #     print(f"   [!] Error saving JSON for {folder_name}: {e}")

    print(f"   -> Saved {len(rows)} certificates to: {folder_name}")

# ==========================================
# 3. MAIN LOGIC
# ==========================================
def main():
    print(f"Reading {INPUT_CSV}... (This might take a moment)")
    
    if not os.path.exists(INPUT_CSV):
        print(f"Error: File '{INPUT_CSV}' not found.")
        return

    # Dictionary to hold our buckets of data
    # format:findings["error_e_dnsname_bad"] = [row1, row2...]
    findings = {}
    
    try:
        with open(INPUT_CSV, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames
            
            # Identify which columns are ZLint results
            # They usually look like: "zlint.lints.e_sub_cert_aia...result"
            lint_columns = [h for h in headers if "zlint.lints" in h and "result" in h]
            
            print(f"Detected {len(lint_columns)} ZLint columns. Scanning rows...")

            row_count = 0
            for row in reader:
                row_count += 1
                
                # Check every ZLint column in this row
                for col_name in lint_columns:
                    val = row.get(col_name, "").lower().strip()
                    
                    if val in ["error", "warn"]:
                        # Extract a clean name from the column header
                        # Header example: "zlint.lints.e_sub_cert_aia_missing.result"
                        # We want: "e_sub_cert_aia_missing"
                        clean_name = col_name.replace("zlint.lints.", "").replace(".result", "")
                        
                        # Create a folder name like "error__e_sub_cert_aia_missing"
                        folder_key = f"{val}__{clean_name}"
                        
                        if folder_key not in findings:
                            findings[folder_key] = []
                        
                        findings[folder_key].append(row)

            print(f"Scanned {row_count} certificates.")

    except Exception as e:
        print(f"Critical Error reading CSV: {e}")
        return

    # ==========================================
    # 4. EXPORT RESULTS
    # ==========================================
    if not findings:
        print("Good news! No errors or warnings found.")
        return

    print(f"\nFound {len(findings)} unique issues. Generating artifacts...")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for folder, rows in findings.items():
        save_artifacts(folder, rows, headers)

    print(f"\n✅ Success! All evidence saved in '{OUTPUT_DIR}'")

if __name__ == "__main__":
    main()