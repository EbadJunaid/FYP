from pymongo import MongoClient

client = MongoClient('localhost', 27017)
results_db = client['tranco-latest-8-lakh-results']
detailed_collection = results_db['shared-keys-detailed']

# Get existing metadata
metadata = detailed_collection.find_one({'_id': 'metadata'})

if metadata:
    total_certs = metadata.get('total_certificates_scanned', 0)
    certs_at_risk = metadata.get('total_certs_at_risk', 0)
    shared_groups = metadata.get('total_shared_groups', 0)
    
    # Calculate both metrics
    total_public_keys = total_certs - certs_at_risk + shared_groups
    unique_public_keys = total_certs - certs_at_risk
    
    # Update metadata with both values
    metadata['total_public_keys'] = total_public_keys
    metadata['unique_public_keys'] = unique_public_keys
    
    detailed_collection.replace_one({'_id': 'metadata'}, metadata)
    
    print(f"✅ Updated metadata with both key metrics:")
    print(f"   Total Certificates: {total_certs:,}")
    print(f"   Certificates at Risk: {certs_at_risk:,}")
    print(f"   Shared Key Groups: {shared_groups:,}")
    print(f"   ")
    print(f"   Total Public Keys (distinct): {total_public_keys:,}")
    print(f"   Unique Public Keys (non-shared): {unique_public_keys:,}")
    print(f"   Shared Public Keys: {shared_groups:,}")
else:
    print("❌ No metadata found")
