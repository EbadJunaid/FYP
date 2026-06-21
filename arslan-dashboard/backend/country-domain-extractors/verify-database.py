#!/usr/bin/env python3
"""
Verify Pakistani Domains Database
"""

from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
db = client['pakistani-domains']
coll = db['certificates']

print('=' * 70)
print('PAKISTANI DOMAINS DATABASE VERIFICATION')
print('=' * 70)
print()
print(f'📊 Total Pakistani certificates: {coll.count_documents({}):,}')
print()
print('📋 Sample domains:')
for i, cert in enumerate(coll.find({}, {'domain': 1}).limit(10), 1):
    print(f'   {i}. {cert.get("domain")}')
print()
print('🔍 Verify all domains end with .pk:')
non_pk = coll.count_documents({'domain': {'$not': {'$regex': r'\.pk$', '$options': 'i'}}})
print(f'   Non-.pk domains: {non_pk} (should be 0)')
print()
print('✅ Sample document structure:')
sample = coll.find_one()
if sample:
    print(f'   Keys: {list(sample.keys())}')
    print(f'   Has zlint: {"zlint" in sample}')
    print(f'   Has parsed: {"parsed" in sample}')
    print(f'   Has raw: {"raw" in sample}')
    print(f'   Domain: {sample.get("domain")}')
print()
print('=' * 70)
print('✅ VERIFICATION COMPLETE!')
print('=' * 70)
