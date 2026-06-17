import csv
import pymongo

# ==========================================
# CONFIGURATION
# ==========================================
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "go-server"
COLLECTION_NAME = "certificates"

INPUT_CSV = "renew-domains-name.csv"

# ==========================================
# UTILITY
# ==========================================
def get_variations(domain):
    """Return [domain, www.domain] (or reversed) in lowercase."""
    d = domain.strip().lower()
    if d.startswith("www."):
        return [d, d[4:]]
    else:
        return [d, f"www.{d}"]

# ==========================================
# MAIN
# ==========================================
def main():
    # 1. Connect to MongoDB
    client = pymongo.MongoClient(MONGO_URI)
    db = client[DB_NAME]
    collection = db[COLLECTION_NAME]

    # 2. Fetch domains grouped by found status
    print("🔍 Fetching domains from MongoDB...")
    found_true_set = set()
    found_false_set = set()

    # Query all documents, but only return domains and found
    cursor = collection.find({}, {"domains": 1, "found": 1, "_id": 0})
    for doc in cursor:
        domains = doc.get("domains", [])
        if doc.get("found") == True:
            found_true_set.update(d.strip().lower() for d in domains)
        else:
            found_false_set.update(d.strip().lower() for d in domains)

    print(f"✅ Found {len(found_true_set)} unique domain strings in found=true documents.")
    print(f"✅ Found {len(found_false_set)} unique domain strings in found=false documents.\n")

    # 3. Read CSV
    csv_domains = []
    try:
        with open(INPUT_CSV, mode='r', encoding='utf-8') as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                csv_domains.append(row)   # keep full row for later
    except FileNotFoundError:
        print(f"❌ Error: Could not find '{INPUT_CSV}'.")
        return

    total_csv = len(csv_domains)

    # 4. For each CSV domain, check status
    results = []
    for row in csv_domains:
        domain = row['domain'].strip().lower()
        variations = get_variations(domain)
        
        # Check against the two sets
        in_true = any(v in found_true_set for v in variations)
        in_false = any(v in found_false_set for v in variations)
        
        if in_true:
            status = "found=true"
        elif in_false:
            status = "found=false (unmarked)"
        else:
            status = "NOT FOUND in any document"
        
        results.append({
            "index": row['index'],
            "domain": domain,
            "status": status,
            "variations": variations
        })

    # 5. Summary
    print("=" * 70)
    print("📊 DIAGNOSTIC REPORT")
    print(f"Total CSV domains processed : {total_csv}")
    count_true = sum(1 for r in results if r['status'] == "found=true")
    count_false = sum(1 for r in results if r['status'] == "found=false (unmarked)")
    count_missing = sum(1 for r in results if r['status'] == "NOT FOUND in any document")
    print(f"  ✅ Found in found=true      : {count_true}")
    print(f"  ⏳ Found in found=false     : {count_false}")
    print(f"  ❌ Not found anywhere       : {count_missing}")
    print("=" * 70)

    # 6. List the ones that are NOT found=true (the 5 you care about)
    not_true = [r for r in results if r['status'] != "found=true"]
    if not_true:
        print("\n🔎 Domains that are NOT marked found=true (should be the missing 5):")
        for r in not_true:
            print(f"  Index {r['index']}: {r['domain']}  -> {r['status']}")
    else:
        print("\n✅ All CSV domains are already found=true!")

    # 7. Show all statuses (optional) – uncomment to see full list
    # print("\n📋 Full list:")
    # for r in results:
    #     print(f"{r['index']}: {r['domain']} -> {r['status']}")

if __name__ == "__main__":
    main()