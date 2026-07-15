import json
import os
import csv

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_FILE = "all-certificates.json"   # Your exported MongoDB data
OUTPUT_DIR = "JSON"     # The main folder to create

# ==========================================
# 2. HELPER FUNCTIONS
# ==========================================
def load_json(filename):
    print(f"Loading {filename}...")
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading file: {e}")
        return []

def flatten_for_csv(doc):
    """
    Creates a simple summary row for CSV reports.
    """
    parsed = doc.get('parsed', {})
    
    return {
        "Domain": doc.get('domain', 'N/A'),
        "Common Name": parsed.get('subject', {}).get('common_name', ['N/A'])[0],
        "Issuer": parsed.get('issuer', {}).get('organization', ['N/A'])[0],
        "Valid To": parsed.get('validity', {}).get('end', 'N/A'),
        "Fingerprint": parsed.get('fingerprint_sha256', 'N/A')
    }

# ==========================================
# 3. MAIN LOGIC
# ==========================================
def main():
    data = load_json(INPUT_FILE)
    if not data:
        return

    # Dictionary to hold buckets of data
    # Structure: findings["error_e_dnsname_bad"] = [doc1, doc2, ...]
    findings = {}

    print(f"Scanning {len(data)} certificates for ALL errors and warnings...")

    for doc in data:
        # 1. Get the ZLint report section
        zlint_report = doc.get('zlint', {}).get('lints', {})
        
        # 2. Iterate through EVERY lint in the report
        for lint_name, lint_data in zlint_report.items():
            result = lint_data.get('result')
            
            # 3. Check if it's relevant (Error or Warn)
            if result in ['error', 'warn']:
                # Create a dynamic folder name, e.g., "error__e_dnsname_not_valid_tld"
                folder_name = f"{result}__{lint_name}"
                
                # Initialize list if new
                if folder_name not in findings:
                    findings[folder_name] = []
                
                # Add this certificate to the bucket
                findings[folder_name].append(doc)

    # ==========================================
    # 4. SAVE RESULTS
    # ==========================================
    if not findings:
        print("Good news! No errors or warnings found in any certificate.")
        return

    print(f"\nFound {len(findings)} unique types of issues. Creating folders...")

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    for folder_name, docs in findings.items():
        # Create the sub-folder (e.g., "ZLint_Auto_Evidence/error__e_dnsname...")
        path = os.path.join(OUTPUT_DIR, folder_name)
        if not os.path.exists(path):
            os.makedirs(path)

        # A. Save Full JSON (Evidence)
        json_path = os.path.join(path, "full_evidence.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(docs, f, indent=4)

        # B. Save CSV (Summary)
        # csv_path = os.path.join(path, "summary_evidence.csv")
        # csv_data = [flatten_for_csv(d) for d in docs]
        
        # if csv_data:
        #     keys = csv_data[0].keys()
        #     with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        #         writer = csv.DictWriter(f, fieldnames=keys)
        #         writer.writeheader()
        #         writer.writerows(csv_data)

        print(f" -> Saved {len(docs)} certificates to: {folder_name}")

    print(f"\n✅ Completed! Open the '{OUTPUT_DIR}' folder to see your artifacts.")

if __name__ == "__main__":
    main()