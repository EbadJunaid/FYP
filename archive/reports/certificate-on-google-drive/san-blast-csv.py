import csv
import sys

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_CSV = "all-certificates.csv"       # Your actual filename
OUTPUT_CSV = "blast-radius-evidence.csv" # The output file
SAN_THRESHOLD = 50                       # The "Sweet Spot"

# Increase CSV limit for massive certificate data
csv.field_size_limit(sys.maxsize)

# ==========================================
# 2. MAIN LOGIC
# ==========================================
def main():
    print(f"Reading {INPUT_CSV}...")

    if not os.path.exists(INPUT_CSV):
        print(f"Error: File '{INPUT_CSV}' not found.")
        return

    try:
        with open(INPUT_CSV, 'r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            headers = reader.fieldnames
            
            # 1. INTELLIGENT COLUMN DETECTION
            # We find ALL columns that look like "...dns_names[0]", "...dns_names[1]", etc.
            san_columns = [h for h in headers if "parsed.extensions.subject_alt_name.dns_names" in h]
            
            print(f"Detected {len(san_columns)} 'dns_names' columns (Flattened format).")
            print(f"Scanning for certificates with > {SAN_THRESHOLD} domains...")

            high_risk_rows = []
            row_count = 0

            for row in reader:
                row_count += 1
                
                # 2. COUNTING LOGIC
                # We count how many of these specific columns have actual text in them
                domain_count = 0
                for col in san_columns:
                    if row.get(col, "").strip(): # If the cell is not empty
                        domain_count += 1
                
                # 3. FILTER LOGIC
                if domain_count > SAN_THRESHOLD:
                    high_risk_rows.append(row)

            # ==========================================
            # 3. SAVE RESULTS
            # ==========================================
            print(f"Scanned {row_count} rows.")
            print(f"Found {len(high_risk_rows)} high-risk certificates.")
            
            if high_risk_rows:
                with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as outfile:
                    writer = csv.DictWriter(outfile, fieldnames=headers)
                    writer.writeheader()
                    writer.writerows(high_risk_rows)
                print(f"✅ Success! Evidence saved to: {OUTPUT_CSV}")
            else:
                print("No certificates found exceeding the threshold.")

    except Exception as e:
        print(f"Critical Error: {e}")

# Need 'os' module for file checking
import os

if __name__ == "__main__":
    main()