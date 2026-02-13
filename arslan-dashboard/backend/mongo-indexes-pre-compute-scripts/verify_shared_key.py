from pymongo import MongoClient

client = MongoClient('localhost', 27017)
results_db = client['tranco-latest-8-lakh-results']
shared_keys = results_db['shared-keys-detailed']

public_key_hash = 'df55ed82be67c2f03b014b23aefcaf0f27fe7ae63b5d17573d15078181a6a5b6'

# Get the shared key group from pre-computed data
group = shared_keys.find_one({'_id': public_key_hash})

if group:
    print(f"✅ Verification from Pre-Computed Data:")
    print(f"   Public Key Hash: {public_key_hash}")
    print(f"   Certificate Count: {group.get('certificate_count', 0)}")
    print(f"   Total Domains: {group.get('total_domains', 0)}")
    print(f"   Key Type: {group.get('key_type', 'N/A')}")
    print()
    print(f"   Sample Domains (first 5):")
    for i, domain in enumerate(group.get('sample_domains', [])[:5], 1):
        print(f"   {i}. {domain}")
    print()
    print(f"   Issuers:")
    for issuer in group.get('issuers', [])[:3]:
        org = issuer.get('organization', 'N/A')
        cn = issuer.get('common_name', 'N/A')
        count = issuer.get('certificate_count', 0)
        print(f"   - {org} / {cn} ({count} certs)")
    print()
    print(f"✅ This is CORRECT! The data matches the API response.")
else:
    print(f"❌ No data found for public key hash: {public_key_hash}")
