#!/usr/bin/env python3
"""
Pre-compute Geographic Distribution with Certificate ID References
Stores country groups with certificate IDs for fast lookups
This script should be run periodically (e.g., every 6-12 hours via cron job)
"""

import sys
import os
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError

# ============================================================
# CONFIGURATION
# ============================================================
TESTING_MODE = False  # Set to False for full collection run
TESTING_LIMIT = 10000  # Number of docs to process in testing mode

# Color codes for terminal output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
BOLD = '\033[1m'
RESET = '\033[0m'

# Complete TLD to Country mapping (195+ countries)
# Generic/International TLDs (go to "Others" category)
GENERIC_TLDS = {
    'com', 'net', 'org', 'edu', 'gov', 'mil', 'int',  # Original generic TLDs
    'info', 'biz', 'name', 'pro', 'mobi', 'tel', 'travel',  # Early expansions
    'asia', 'cat', 'coop', 'jobs', 'museum', 'aero', 'post',  # Sponsored TLDs
    'io', 'ai', 'co', 'me', 'tv', 'cc', 'ws', 'tk', 'ml', 'ga', 'cf', 'gq',  # Popular ccTLDs used generically
    'dev', 'app', 'page', 'cloud', 'online', 'site', 'website', 'tech', 'store',  # New gTLDs
    'blog', 'shop', 'web', 'space', 'digital', 'network', 'systems', 'software',
    'email', 'host', 'domains', 'link', 'click', 'today', 'world', 'global',
    'xyz', 'top', 'club', 'vip', 'icu', 'live', 'fun', 'press', 'news',
}

# Country-specific TLDs (195 countries)
TLD_TO_COUNTRY = {
    # North America
    'us': 'United States', 'ca': 'Canada', 'mx': 'Mexico',
    
    # Central America & Caribbean
    'gt': 'Guatemala', 'bz': 'Belize', 'sv': 'El Salvador', 'hn': 'Honduras',
    'ni': 'Nicaragua', 'cr': 'Costa Rica', 'pa': 'Panama', 'cu': 'Cuba',
    'jm': 'Jamaica', 'ht': 'Haiti', 'do': 'Dominican Republic', 'tt': 'Trinidad and Tobago',
    'bb': 'Barbados', 'bs': 'Bahamas', 'ag': 'Antigua and Barbuda', 'dm': 'Dominica',
    'gd': 'Grenada', 'kn': 'Saint Kitts and Nevis', 'lc': 'Saint Lucia',
    'vc': 'Saint Vincent and the Grenadines',
    
    # South America
    'br': 'Brazil', 'ar': 'Argentina', 'co': 'Colombia', 'cl': 'Chile',
    'pe': 'Peru', 've': 'Venezuela', 'ec': 'Ecuador', 'bo': 'Bolivia',
    'py': 'Paraguay', 'uy': 'Uruguay', 'gy': 'Guyana', 'sr': 'Suriname',
    
    # Europe - Western
    'uk': 'United Kingdom', 'co.uk': 'United Kingdom', 'gb': 'United Kingdom',
    'ie': 'Ireland', 'fr': 'France', 'es': 'Spain', 'pt': 'Portugal',
    'de': 'Germany', 'nl': 'Netherlands', 'be': 'Belgium', 'lu': 'Luxembourg',
    'ch': 'Switzerland', 'at': 'Austria', 'it': 'Italy', 'gr': 'Greece',
    
    # Europe - Northern
    'se': 'Sweden', 'no': 'Norway', 'dk': 'Denmark', 'fi': 'Finland',
    'is': 'Iceland',
    
    # Europe - Eastern
    'pl': 'Poland', 'cz': 'Czech Republic', 'sk': 'Slovakia', 'hu': 'Hungary',
    'ro': 'Romania', 'bg': 'Bulgaria', 'si': 'Slovenia', 'hr': 'Croatia',
    'rs': 'Serbia', 'ba': 'Bosnia and Herzegovina', 'mk': 'North Macedonia',
    'al': 'Albania', 'me': 'Montenegro', 'xk': 'Kosovo',
    
    # Europe - Baltic
    'ee': 'Estonia', 'lv': 'Latvia', 'lt': 'Lithuania',
    
    # Europe - Eastern Europe & Caucasus
    'ru': 'Russia', 'ua': 'Ukraine', 'by': 'Belarus', 'md': 'Moldova',
    'ge': 'Georgia', 'am': 'Armenia', 'az': 'Azerbaijan',
    
    # Middle East
    'tr': 'Turkey', 'il': 'Israel', 'ps': 'Palestine', 'jo': 'Jordan',
    'lb': 'Lebanon', 'sy': 'Syria', 'iq': 'Iraq', 'ir': 'Iran',
    'sa': 'Saudi Arabia', 'ae': 'United Arab Emirates', 'kw': 'Kuwait',
    'qa': 'Qatar', 'bh': 'Bahrain', 'om': 'Oman', 'ye': 'Yemen',
    
    # Central Asia
    'kz': 'Kazakhstan', 'uz': 'Uzbekistan', 'tm': 'Turkmenistan',
    'kg': 'Kyrgyzstan', 'tj': 'Tajikistan', 'af': 'Afghanistan',
    
    # South Asia
    'in': 'India', 'pk': 'Pakistan', 'bd': 'Bangladesh', 'lk': 'Sri Lanka',
    'np': 'Nepal', 'bt': 'Bhutan', 'mv': 'Maldives',
    
    # Southeast Asia
    'th': 'Thailand', 'vn': 'Vietnam', 'sg': 'Singapore', 'my': 'Malaysia',
    'id': 'Indonesia', 'ph': 'Philippines', 'mm': 'Myanmar', 'kh': 'Cambodia',
    'la': 'Laos', 'bn': 'Brunei', 'tl': 'Timor-Leste',
    
    # East Asia
    'cn': 'China', 'jp': 'Japan', 'kr': 'South Korea', 'kp': 'North Korea',
    'mn': 'Mongolia', 'tw': 'Taiwan', 'hk': 'Hong Kong', 'mo': 'Macau',
    
    # Oceania
    'au': 'Australia', 'com.au': 'Australia', 'nz': 'New Zealand',
    'pg': 'Papua New Guinea', 'fj': 'Fiji', 'sb': 'Solomon Islands',
    'vu': 'Vanuatu', 'ws': 'Samoa', 'ki': 'Kiribati', 'to': 'Tonga',
    'fm': 'Micronesia', 'mh': 'Marshall Islands', 'pw': 'Palau',
    'nr': 'Nauru', 'tv': 'Tuvalu',
    
    # Africa - North
    'eg': 'Egypt', 'ly': 'Libya', 'tn': 'Tunisia', 'dz': 'Algeria',
    'ma': 'Morocco', 'sd': 'Sudan', 'ss': 'South Sudan',
    
    # Africa - West
    'ng': 'Nigeria', 'gh': 'Ghana', 'ci': "Côte d'Ivoire", 'sn': 'Senegal',
    'ml': 'Mali', 'bf': 'Burkina Faso', 'ne': 'Niger', 'gn': 'Guinea',
    'sl': 'Sierra Leone', 'lr': 'Liberia', 'tg': 'Togo', 'bj': 'Benin',
    'mr': 'Mauritania', 'gm': 'Gambia', 'gw': 'Guinea-Bissau',
    'cv': 'Cape Verde',
    
    # Africa - Central
    'cd': 'Democratic Republic of Congo', 'cg': 'Republic of Congo',
    'cm': 'Cameroon', 'cf': 'Central African Republic', 'td': 'Chad',
    'ga': 'Gabon', 'gq': 'Equatorial Guinea', 'st': 'São Tomé and Príncipe',
    
    # Africa - East
    'ke': 'Kenya', 'tz': 'Tanzania', 'ug': 'Uganda', 'rw': 'Rwanda',
    'bi': 'Burundi', 'et': 'Ethiopia', 'so': 'Somalia', 'dj': 'Djibouti',
    'er': 'Eritrea', 'sc': 'Seychelles', 'mu': 'Mauritius', 'km': 'Comoros',
    'mg': 'Madagascar',
    
    # Africa - Southern
    'za': 'South Africa', 'zw': 'Zimbabwe', 'zm': 'Zambia', 'mw': 'Malawi',
    'mz': 'Mozambique', 'bw': 'Botswana', 'na': 'Namibia', 'sz': 'Eswatini',
    'ls': 'Lesotho', 'ao': 'Angola',
}


def print_progress(message, color=BLUE):
    """Print colored progress message"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f"{color}{BOLD}[{timestamp}]{RESET} {color}{message}{RESET}")

def print_success(message):
    """Print success message"""
    print_progress(f"✓ {message}", GREEN)

def print_error(message):
    """Print error message"""
    print_progress(f"✗ {message}", RED)

def print_info(message):
    """Print info message"""
    print_progress(f"ℹ {message}", YELLOW)

def get_tld_country(domain: str) -> str:
    """Derive country from domain TLD or return 'Others' for generic TLDs"""
    if not domain:
        return 'Others'
    
    parts = domain.lower().split('.')
    if len(parts) >= 2:
        # Check for two-part TLDs first (e.g., co.uk, com.au)
        two_part_tld = '.'.join(parts[-2:])
        if two_part_tld in TLD_TO_COUNTRY:
            return TLD_TO_COUNTRY[two_part_tld]
        
        # Check single TLD
        tld = parts[-1]
        
        # Check if it's a generic TLD
        if tld in GENERIC_TLDS:
            return 'Others'
        
        # Check if it's a country TLD
        if tld in TLD_TO_COUNTRY:
            return TLD_TO_COUNTRY[tld]
        
        # Unknown TLD -> Others
        return 'Others'
    
    return 'Others'

def main():
    """Main execution function"""
    
    print_progress("=" * 70, BOLD)
    print_progress("GEOGRAPHIC DISTRIBUTION WITH CERTIFICATE IDS", BOLD)
    print_progress("=" * 70, BOLD)
    print()
    
    # Display configuration
    if TESTING_MODE:
        print_info(f"⚠️  TESTING MODE ENABLED - Processing {TESTING_LIMIT:,} documents")
        print_info("   Set TESTING_MODE = False for full collection")
    else:
        print_info("🚀 PRODUCTION MODE - Processing ALL documents")
    print()
    
    # Step 1: Connect to MongoDB
    print_progress("Step 1/7: Connecting to MongoDB...")
    try:
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print_success("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print_error("Failed to connect to MongoDB. Is it running?")
        sys.exit(1)
    
    # Step 2: Access databases and collections
    print_progress("Step 2/7: Accessing databases...")
    source_db = client['tranco-latest-8-lakh']
    source_collection = source_db['certificates']
    
    target_db = client['tranco-latest-8-lakh-results']
    target_collection_name = 'testing-geographic-distribution' if TESTING_MODE else 'geographic-distribution-1'
    target_collection = target_db[target_collection_name]
    
    # Get total document count
    if TESTING_MODE:
        total_to_process = TESTING_LIMIT
    else:
        total_to_process = source_collection.estimated_document_count()
    
    print_success(f"Source: tranco-latest-8-lakh.certificates")
    print_success(f"Target: tranco-latest-8-lakh-results.{target_collection_name}")
    print_success(f"Documents to process: {total_to_process:,}")
    
    # Step 3: Fetch documents with domain and extract countries
    print_progress("Step 3/7: Fetching documents and grouping by country...")
    print_info("This will take a few minutes...")
    print()
    
    start_time = datetime.now()
    
    # Build query
    query = {'domain': {'$exists': True, '$ne': None, '$ne': ''}}
    
    # Build cursor with limit if testing
    if TESTING_MODE:
        cursor = source_collection.find(query, {'_id': 1, 'domain': 1}).limit(TESTING_LIMIT)
    else:
        cursor = source_collection.find(query, {'_id': 1, 'domain': 1})
    
    # Group documents by country
    country_groups = {}  # {country: [cert_id1, cert_id2, ...]}
    processed_count = 0
    
    print_info("Processing documents...")
    for doc in cursor:
        cert_id = doc['_id']
        domain = doc.get('domain', '')
        
        # Derive country from domain
        country = get_tld_country(domain)
        
        # Add cert ID to country group
        if country not in country_groups:
            country_groups[country] = []
        country_groups[country].append(cert_id)
        
        processed_count += 1
        
        # Progress indicator
        if processed_count % 50000 == 0:
            print_info(f"  Processed {processed_count:,} documents...")
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print_success(f"Processing completed in {duration:.1f} seconds")
    print_success(f"Processed {processed_count:,} documents")
    print_success(f"Found {len(country_groups)} countries/groups")
    print()
    
    # Step 4: Calculate statistics
    print_progress("Step 4/7: Calculating statistics...")
    
    # Sort countries by count
    sorted_countries = sorted(
        country_groups.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    total_certificates = sum(len(ids) for ids in country_groups.values())
    max_count = len(sorted_countries[0][1]) if sorted_countries else 1
    
    print_success(f"Total certificates: {total_certificates:,}")
    print_success(f"Countries with data: {len(sorted_countries)}")
    
    # Display top 10 countries
    print()
    print_info("Top 10 Countries:")
    print()
    for i, (country, cert_ids) in enumerate(sorted_countries[:10], 1):
        count = len(cert_ids)
        percentage = (count / total_certificates) * 100
        bar_length = int((count / max_count) * 40)
        bar = '█' * bar_length
        print(f"  {i:2}. {country[:40]:<40} {bar} {count:>7,} ({percentage:>5.1f}%)")
    print()
    
    # Step 5: Prepare documents for storage
    print_progress("Step 5/7: Preparing documents for storage...")
    
    # Color palette
    colors = [
        '#3b82f6', '#10b981', '#8b5cf6', '#f59e0b', '#ef4444',
        '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16',
        '#f97316', '#a855f7', '#22c55e', '#0ea5e9', '#d946ef',
        '#eab308', '#6b7280'
    ]
    
    # Build country documents
    country_docs = []
    for i, (country, cert_ids) in enumerate(sorted_countries):
        count = len(cert_ids)
        percentage = round((count / total_certificates) * 100, 3)
        
        doc = {
            '_id': country,  # Use country name as _id for easy lookup
            'country': country,
            'count': count,
            'percentage': percentage,
            'color': colors[i % len(colors)],
            'rank': i + 1,
            'certificate_ids': cert_ids,  # Store all certificate IDs
            'computed_at': datetime.now(timezone.utc),
            'source_database': 'tranco-latest-8-lakh',
            'source_collection': 'certificates',
            'testing_mode': TESTING_MODE
        }
        country_docs.append(doc)
    
    print_success(f"Prepared {len(country_docs)} country documents")
    
    # Calculate storage size estimate
    avg_ids_per_country = total_certificates / len(country_docs) if country_docs else 0
    estimated_size_mb = (len(country_docs) * avg_ids_per_country * 12) / (1024 * 1024)
    print_info(f"Estimated storage size: ~{estimated_size_mb:.1f} MB")
    print()
    
    # Step 6: Store in target collection
    print_progress("Step 6/7: Storing results in database...")
    
    try:
        # Clear existing data
        deleted_count = target_collection.delete_many({}).deleted_count
        if deleted_count > 0:
            print_info(f"Cleared {deleted_count} old records")
        
        # Insert new data
        if country_docs:
            # Insert in batches for better performance
            batch_size = 100
            for i in range(0, len(country_docs), batch_size):
                batch = country_docs[i:i+batch_size]
                target_collection.insert_many(batch)
            print_success(f"Inserted {len(country_docs)} country documents")
        
        # Create indexes
        target_collection.create_index('rank')
        target_collection.create_index('count')
        target_collection.create_index('computed_at')
        print_success("Created indexes on target collection")
        
        # Store metadata document
        metadata = {
            '_id': 'metadata',
            'last_computed': datetime.now(timezone.utc),
            'computation_duration_seconds': duration,
            'total_countries': len(country_docs),
            'total_certificates': total_certificates,
            'source_database': 'tranco-latest-8-lakh',
            'source_collection': 'certificates',
            'target_database': 'tranco-latest-8-lakh-results',
            'target_collection': target_collection_name,
            'testing_mode': TESTING_MODE,
            'documents_processed': processed_count
        }
        target_collection.replace_one(
            {'_id': 'metadata'},
            metadata,
            upsert=True
        )
        print_success("Stored computation metadata")
        
    except Exception as e:
        print_error(f"Failed to store results: {str(e)}")
        sys.exit(1)
    
    # Step 7: Verify storage
    print_progress("Step 7/7: Verifying storage...")
    
    verify_count = target_collection.count_documents({'_id': {'$ne': 'metadata'}})
    print_success(f"Verified {verify_count} country documents in database")
    
    # Final summary
    print()
    print_progress("=" * 70, BOLD)
    print_success("GEOGRAPHIC DISTRIBUTION COMPUTATION COMPLETED!")
    print_progress("=" * 70, BOLD)
    print()
    print_info(f"Mode: {BOLD}{'TESTING' if TESTING_MODE else 'PRODUCTION'}{RESET}")
    print_info(f"Database: {BOLD}tranco-latest-8-lakh-results{RESET}")
    print_info(f"Collection: {BOLD}{target_collection_name}{RESET}")
    print_info(f"Total Countries: {BOLD}{len(country_docs):,}{RESET}")
    print_info(f"Total Certificates: {BOLD}{total_certificates:,}{RESET}")
    print_info(f"Computation Time: {BOLD}{duration:.1f}s{RESET}")
    print()
    
    if TESTING_MODE:
        print_info("⚠️  TESTING MODE - To process full collection:")
        print(f"   1. Set TESTING_MODE = False in the script")
        print(f"   2. Run the script again")
        print()
    else:
        print_info("Next steps:")
        print(f"  1. API will now use these pre-computed IDs for fast lookups")
        print(f"  2. Set up cron job to run this script every 6-12 hours")
        print(f"  3. Example: 0 */12 * * * /path/to/python compute-geographic-distribution.py")
        print()
    
    client.close()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print()
        print_error("Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print()
        print_error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

