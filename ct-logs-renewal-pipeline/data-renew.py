### This is the file which extracts the domains which the crawler needs to renew them 
### It is handling the SAN thing means if my global dataset is below :
### arslan.com , yasir.com , cheema.com [all have same certificates] 
### then it just enters arslan.com into the output csv and skip the other two 
### because they have same certificate 


### remember domains which have same certficates is not present now because of the crawler and data-removal
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
OUTPUT_CSV = "data-renew.csv"

BATCH_SIZE = 5000  

client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# ==========================================
# UTILITY FUNCTIONS
# ==========================================
def get_domain_variations(domain):
    """Generates the base and 'www.' variations to solve the mismatch."""
    domain = domain.strip().lower()
    if domain.startswith("www."):
        return [domain, domain[4:]]
    else:
        return [domain, f"www.{domain}"]

def debug_index_usage(query):
    """Proves MongoDB is using the index for lightning-fast queries."""
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
    total_found_unique = 0
    total_duplicates = 0  # Initialize main counter
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
                    matched_rows, batch_dupes = process_batch(batch, first_batch, session_found_ids)
                    
                    for r in matched_rows:
                        r['index'] = output_index_counter
                        writer.writerow(r)
                        output_index_counter += 1
                        
                    total_processed += len(batch)
                    total_found_unique += len(matched_rows)
                    total_duplicates += batch_dupes
                    first_batch = False
                    batch = [] 
                    
                    print(f"📊 Progress: Scanned {total_processed:,} | Unique Certs Found: {total_found_unique:,} | Dupes Skipped: {total_duplicates:,}")

            if batch:
                matched_rows, batch_dupes = process_batch(batch, first_batch, session_found_ids)
                for r in matched_rows:
                    r['index'] = output_index_counter
                    writer.writerow(r)
                    output_index_counter += 1
                    
                total_processed += len(batch)
                total_found_unique += len(matched_rows)
                total_duplicates += batch_dupes
                
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{INPUT_CSV}'.")
        return

    elapsed = time.time() - start_time
    print("\n" + "="*70)
    print("🚀 CROSS-REFERENCING COMPLETE")
    print(f"Total CSV Rows Scanned : {total_processed:,}")
    print(f"Unique DB Certs Found  : {total_found_unique:,}")
    print(f"Total Dupes Skipped    : {total_duplicates:,}")
    print(f"Time Elapsed           : {elapsed:.2f} seconds")
    print("="*70)

def process_batch(batch, is_first_batch, session_found_ids):
    """Queries DB, checks for duplicates, updates DB, and returns rows to write."""
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
    batch_duplicate_count = 0  # Track duplicates just for this batch
    
    for doc in cursor:
        doc_id = doc["_id"]
        is_found_in_db = doc.get("found", False)
        is_found_in_session = doc_id in session_found_ids
        
        # Identify WHICH unique CSV domains matched this specific database document
        unique_csv_rows = {}
        for db_domain in doc.get("domains", []):
            if db_domain in variation_map:
                row = variation_map[db_domain]
                unique_csv_rows[row['domain']] = row
                
        matching_csv_rows = list(unique_csv_rows.values())
                
        if not matching_csv_rows:
            continue

        # Duplicate Catching Logic 1: Already marked as found in DB or Session
        if is_found_in_db or is_found_in_session:
            for r in matching_csv_rows:
                print(f"⚠️  DEBUG: '{r['domain']}' maps to a certificate already marked as found. Skipping CSV write.")
                batch_duplicate_count += 1
            continue
            
        # Brand New Find!
        session_found_ids.add(doc_id)
        docs_to_update.append(doc_id)
        
        # We only take the FIRST matching domain to represent this certificate in the new CSV
        first_match = matching_csv_rows[0]
        matched_rows_for_csv.append(first_match)
        
        # Duplicate Catching Logic 2: Multiple CSV domains share this exact same cert
        for r in matching_csv_rows[1:]:
            print(f"⚠️  DEBUG: '{r['domain']}' shares a certificate with '{first_match['domain']}'. Skipping CSV write.")
            batch_duplicate_count += 1
            
    # Bulk update the freshly found documents
    if docs_to_update:
        collection.update_many(
            {"_id": {"$in": docs_to_update}}, 
            {"$set": {"found": True}}
        )
        
    return matched_rows_for_csv, batch_duplicate_count

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