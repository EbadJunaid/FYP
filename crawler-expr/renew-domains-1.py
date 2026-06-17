### This is the file which extracts the domains which the crawler needs to renew them 
### It does not handle the SAN thing means if my global dataset is below :
### arslan.com , ebad.com , cheema.com [all have same certificates] 
### then it enters all of certificates  

### I don't think I need this file because of the crawler and data-removal
## script and also the data renew logic 

import csv
import time
from pymongo import MongoClient

# ==========================================
# CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "go-server"
COLLECTION_NAME = "certificates"

INPUT_CSV = "global-dataset.csv"
OUTPUT_CSV = "renew-domains-name.csv"

BATCH_SIZE = 5000  

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def get_domain_variations(domain):
    """Generates the base and 'www.' variations."""
    domain = domain.strip().lower()
    if domain.startswith("www."):
        return [domain, domain[4:]]
    else:
        return [domain, f"www.{domain}"]

def debug_index_usage(query):
    print("\n🔍 DEBUG: Verifying MongoDB Index Usage...")
    try:
        explanation = collection.find(query).explain()
        winning_plan = explanation.get("queryPlanner", {}).get("winningPlan", {})
        
        index_name = "UNKNOWN"
        if "inputStage" in winning_plan and "indexName" in winning_plan["inputStage"]:
            index_name = winning_plan["inputStage"]["indexName"]
        elif "inputStages" in winning_plan:
             index_name = winning_plan["inputStages"][0].get("indexName", "UNKNOWN")

        if index_name != "UNKNOWN":
            print(f"✅ SUCCESS: Query is utilizing the index: '{index_name}'")
        else:
            print("⚠️ WARNING: COLLSCAN detected. Check your indexes!")
    except Exception as e:
        print(f"⚠️ Debug explain failed: {e}")
    print("-" * 70 + "\n")

# ==========================================
# MAIN EXECUTION
# ==========================================
def process_dataset():
    total_processed = 0
    total_found_written = 0
    
    # New Specific Counters
    total_variations_collapsed = 0
    total_shared_certs_written = 0
    
    start_time = time.time()
    first_batch = True
    output_index_counter = 1  
    
    session_found_ids = set()

    try:
        with open(INPUT_CSV, mode='r', encoding='utf-8') as infile, \
             open(OUTPUT_CSV, mode='w', encoding='utf-8', newline='') as outfile:
            
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            batch = []
            
            for row in reader:
                batch.append(row)
                
                if len(batch) >= BATCH_SIZE:
                    matched_rows, variations, shared_certs = process_batch(batch, first_batch, session_found_ids)
                    
                    for r in matched_rows:
                        r['index'] = output_index_counter
                        writer.writerow(r)
                        output_index_counter += 1
                        
                    total_processed += len(batch)
                    total_found_written += len(matched_rows)
                    total_variations_collapsed += variations
                    total_shared_certs_written += shared_certs
                    
                    first_batch = False
                    batch = [] 
                    
                    print(f"📊 Progress: Scanned {total_processed:,} | Written to CSV: {total_found_written:,}")

            if batch:
                matched_rows, variations, shared_certs = process_batch(batch, first_batch, session_found_ids)
                for r in matched_rows:
                    r['index'] = output_index_counter
                    writer.writerow(r)
                    output_index_counter += 1
                    
                total_processed += len(batch)
                total_found_written += len(matched_rows)
                total_variations_collapsed += variations
                total_shared_certs_written += shared_certs
                
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{INPUT_CSV}'.")
        return

    elapsed = time.time() - start_time
    print("\n" + "="*80)
    print("🚀 CROSS-REFERENCING COMPLETE")
    print(f"Total CSV Rows Scanned      : {total_processed:,}")
    print(f"Total Matches Written to CSV: {total_found_written:,}")
    print("-" * 80)
    print(f"🔄 Counter 1: Variations Collapsed (e.g., domain + www)  : {total_variations_collapsed:,}")
    print(f"🔗 Counter 2: Shared Certs Written (Distinct CSV domains): {total_shared_certs_written:,}")
    print("-" * 80)
    print(f"Time Elapsed                : {elapsed:.2f} seconds")
    print("="*80)

def process_batch(batch, is_first_batch, session_found_ids):
    variation_map = {}
    for row in batch:
        for variation in get_domain_variations(row['domain']):
            variation_map[variation] = row
            
    query_domain_list = list(variation_map.keys())
    db_query = {"domains": {"$in": query_domain_list}}
    
    if is_first_batch:
        debug_index_usage(db_query)
        
    cursor = collection.find(db_query, {"_id": 1, "domains": 1, "found": 1})
    
    matched_rows_for_csv = []
    docs_to_update = []
    
    batch_variations = 0
    batch_shared_certs = 0
    
    for doc in cursor:
        doc_id = doc["_id"]
        is_found_in_db = doc.get("found", False)
        is_found_in_session = doc_id in session_found_ids
        is_already_processed = is_found_in_db or is_found_in_session
        
        # 1. Map raw database array hits back to their original CSV rows
        raw_hits = 0
        unique_csv_rows = {}
        for db_domain in doc.get("domains", []):
            if db_domain in variation_map:
                raw_hits += 1
                row = variation_map[db_domain]
                unique_csv_rows[row['domain']] = row
                
        if not unique_csv_rows:
            continue
            
        # COUNTER 1 LOGIC: E.g., if array had 'domain' and 'www.domain', raw_hits is 2, 
        # but unique_csv_rows length is 1. The difference is the collapsed variations.
        batch_variations += (raw_hits - len(unique_csv_rows))
        
        # Convert distinct dictionary values to a list we can loop through
        matching_csv_rows = list(unique_csv_rows.values())

        if is_already_processed:
            # If the cert was already marked found, ALL of these are shared piggybackers.
            for r in matching_csv_rows:
                print(f"🔗 DEBUG: '{r['domain']}' maps to a cert marked 'found' earlier. Writing to CSV.")
                matched_rows_for_csv.append(r)
                batch_shared_certs += 1
        else:
            # Brand New Find for the database!
            session_found_ids.add(doc_id)
            docs_to_update.append(doc_id)
            
            # The FIRST distinct domain represents the main find
            first_match = matching_csv_rows[0]
            matched_rows_for_csv.append(first_match)
            
            # COUNTER 2 LOGIC: Any additional distinct domains share this new cert
            for r in matching_csv_rows[1:]:
                print(f"🔗 DEBUG: '{r['domain']}' shares a certificate with '{first_match['domain']}'. Writing to CSV.")
                matched_rows_for_csv.append(r)
                batch_shared_certs += 1
            
    # Bulk update the freshly found documents to True
    if docs_to_update:
        collection.update_many(
            {"_id": {"$in": docs_to_update}}, 
            {"$set": {"found": True}}
        )
        
    return matched_rows_for_csv, batch_variations, batch_shared_certs

if __name__ == "__main__":
    print("Initializing Database Connections...")
    
    existing_indexes = collection.index_information()
    TARGET_INDEX_NAME = "domains_1"
    
    if TARGET_INDEX_NAME not in existing_indexes:
        print(f"⚙️ Index '{TARGET_INDEX_NAME}' not found. Creating it now...")
        collection.create_index("domains", name=TARGET_INDEX_NAME, unique=True)
    else:
        print(f"✅ Index '{TARGET_INDEX_NAME}' verified.")
        
    process_dataset()