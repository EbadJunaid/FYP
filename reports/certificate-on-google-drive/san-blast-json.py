import json
import os

# ==========================================
# 1. CONFIGURATION
# ==========================================
INPUT_FILE = "all-certificates.json"        # Your full dataset export
OUTPUT_FILE = "blast-radius-full-data.json" # The result file
SAN_THRESHOLD = 50                          # The "Sweet Spot" limit

# ==========================================
# 2. MAIN SCRIPT
# ==========================================
def main():
    print(f"Loading {INPUT_FILE}...")
    
    if not os.path.exists(INPUT_FILE):
        print(f"Error: '{INPUT_FILE}' not found. Please export your collection to JSON first.")
        return

    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            data = load_dataset(f)
            
        print(f"Scanning {len(data)} certificates for Blast Radius > {SAN_THRESHOLD}...")
        
        high_risk_certs = []
        
        for doc in data:
            # 1. Safely navigate to the SAN list
            try:
                # Path: parsed -> extensions -> subject_alt_name -> dns_names
                san_list = doc.get('parsed', {}).get('extensions', {}).get('subject_alt_name', {}).get('dns_names', [])
                
                # Handle cases where san_list might be None
                if san_list is None:
                    san_list = []
                
                # 2. The Logic Check
                if len(san_list) > SAN_THRESHOLD:
                    high_risk_certs.append(doc)
                    
            except Exception as e:
                # Skip malformed documents silently
                continue

        # ==========================================
        # 3. SAVE RESULTS
        # ==========================================
        print(f"Found {len(high_risk_certs)} domains involved in High Blast Radius clusters.")
        
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(high_risk_certs, f, indent=4)
            
        print(f"✅ Success! Full certificate data saved to: {OUTPUT_FILE}")

    except Exception as e:
        print(f"Critical Error: {e}")

# Helper to handle different JSON formats (List vs Line-delimited)
def load_dataset(file_handle):
    try:
        return json.load(file_handle)
    except json.JSONDecodeError:
        # If simple load fails, try reading line-by-line (common Mongo export format)
        file_handle.seek(0)
        return [json.loads(line) for line in file_handle]

if __name__ == "__main__":
    main()