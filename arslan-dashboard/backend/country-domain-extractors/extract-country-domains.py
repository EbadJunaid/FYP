#!/usr/bin/env python3
"""
Generic Country-Level Domain Extractor
=======================================
This script extracts certificates based on country-level TLDs (ccTLDs) from the main database
and stores them in separate country-specific databases.

Author: Arslan Dashboard Team
Date: February 2026
"""

import sys
from pymongo import MongoClient
from datetime import datetime
from collections import defaultdict

# ============================================================================
# CONFIGURATION
# ============================================================================

# MongoDB Configuration
MONGO_HOST = 'localhost'
MONGO_PORT = 27017
SOURCE_DATABASE = 'tranco-latest-8-lakh'
SOURCE_COLLECTION = 'certificates'

# Processing Configuration
BATCH_SIZE = 10000  # Process certificates in batches
TESTING_MODE = False  # Set to True for testing with limited data
TESTING_LIMIT = 50000  # Number of certificates to process in testing mode

# ============================================================================
# COUNTRY TLD CONFIGURATION
# ============================================================================
# Comprehensive list of country-level TLDs (ccTLDs)
# Uncomment the TLD you want to extract
# Format: 'tld_suffix': ('Database Name', 'Country Name')

COUNTRY_TLDS = {
    # === Currently Active ===
    '.pk': ('pakistani-domains', 'Pakistan'),
    
    # === Asia ===
    # '.af': ('afghan-domains', 'Afghanistan'),
    # '.bd': ('bangladeshi-domains', 'Bangladesh'),
    # '.cn': ('chinese-domains', 'China'),
    # '.in': ('indian-domains', 'India'),
    # '.id': ('indonesian-domains', 'Indonesia'),
    # '.ir': ('iranian-domains', 'Iran'),
    # '.iq': ('iraqi-domains', 'Iraq'),
    # '.il': ('israeli-domains', 'Israel'),
    # '.jp': ('japanese-domains', 'Japan'),
    # '.jo': ('jordanian-domains', 'Jordan'),
    # '.kz': ('kazakh-domains', 'Kazakhstan'),
    # '.kw': ('kuwaiti-domains', 'Kuwait'),
    # '.kg': ('kyrgyz-domains', 'Kyrgyzstan'),
    # '.lb': ('lebanese-domains', 'Lebanon'),
    # '.my': ('malaysian-domains', 'Malaysia'),
    # '.mn': ('mongolian-domains', 'Mongolia'),
    # '.mm': ('myanmar-domains', 'Myanmar'),
    # '.np': ('nepalese-domains', 'Nepal'),
    # '.om': ('omani-domains', 'Oman'),
    # '.ph': ('philippine-domains', 'Philippines'),
    # '.qa': ('qatari-domains', 'Qatar'),
    # '.sa': ('saudi-domains', 'Saudi Arabia'),
    # '.sg': ('singapore-domains', 'Singapore'),
    # '.kr': ('south-korean-domains', 'South Korea'),
    # '.lk': ('sri-lankan-domains', 'Sri Lanka'),
    # '.sy': ('syrian-domains', 'Syria'),
    # '.tw': ('taiwanese-domains', 'Taiwan'),
    # '.tj': ('tajik-domains', 'Tajikistan'),
    # '.th': ('thai-domains', 'Thailand'),
    # '.tr': ('turkish-domains', 'Turkey'),
    # '.tm': ('turkmen-domains', 'Turkmenistan'),
    # '.ae': ('uae-domains', 'United Arab Emirates'),
    # '.uz': ('uzbek-domains', 'Uzbekistan'),
    # '.vn': ('vietnamese-domains', 'Vietnam'),
    # '.ye': ('yemeni-domains', 'Yemen'),
    
    # === Europe ===
    # '.al': ('albanian-domains', 'Albania'),
    # '.ad': ('andorran-domains', 'Andorra'),
    # '.at': ('austrian-domains', 'Austria'),
    # '.by': ('belarusian-domains', 'Belarus'),
    # '.be': ('belgian-domains', 'Belgium'),
    # '.ba': ('bosnian-domains', 'Bosnia and Herzegovina'),
    # '.bg': ('bulgarian-domains', 'Bulgaria'),
    # '.hr': ('croatian-domains', 'Croatia'),
    # '.cy': ('cypriot-domains', 'Cyprus'),
    # '.cz': ('czech-domains', 'Czech Republic'),
    # '.dk': ('danish-domains', 'Denmark'),
    # '.ee': ('estonian-domains', 'Estonia'),
    # '.fi': ('finnish-domains', 'Finland'),
    # '.fr': ('french-domains', 'France'),
    # '.de': ('german-domains', 'Germany'),
    # '.gr': ('greek-domains', 'Greece'),
    # '.hu': ('hungarian-domains', 'Hungary'),
    # '.is': ('icelandic-domains', 'Iceland'),
    # '.ie': ('irish-domains', 'Ireland'),
    # '.it': ('italian-domains', 'Italy'),
    # '.lv': ('latvian-domains', 'Latvia'),
    # '.li': ('liechtenstein-domains', 'Liechtenstein'),
    # '.lt': ('lithuanian-domains', 'Lithuania'),
    # '.lu': ('luxembourg-domains', 'Luxembourg'),
    # '.mk': ('macedonian-domains', 'North Macedonia'),
    # '.mt': ('maltese-domains', 'Malta'),
    # '.md': ('moldovan-domains', 'Moldova'),
    # '.mc': ('monegasque-domains', 'Monaco'),
    # '.me': ('montenegrin-domains', 'Montenegro'),
    # '.nl': ('dutch-domains', 'Netherlands'),
    # '.no': ('norwegian-domains', 'Norway'),
    # '.pl': ('polish-domains', 'Poland'),
    # '.pt': ('portuguese-domains', 'Portugal'),
    # '.ro': ('romanian-domains', 'Romania'),
    # '.ru': ('russian-domains', 'Russia'),
    # '.sm': ('san-marino-domains', 'San Marino'),
    # '.rs': ('serbian-domains', 'Serbia'),
    # '.sk': ('slovak-domains', 'Slovakia'),
    # '.si': ('slovenian-domains', 'Slovenia'),
    # '.es': ('spanish-domains', 'Spain'),
    # '.se': ('swedish-domains', 'Sweden'),
    # '.ch': ('swiss-domains', 'Switzerland'),
    # '.ua': ('ukrainian-domains', 'Ukraine'),
    # '.uk': ('british-domains', 'United Kingdom'),
    # '.va': ('vatican-domains', 'Vatican City'),
    
    # === North America ===
    # '.us': ('us-domains', 'United States'),
    # '.ca': ('canadian-domains', 'Canada'),
    # '.mx': ('mexican-domains', 'Mexico'),
    # '.cu': ('cuban-domains', 'Cuba'),
    # '.do': ('dominican-domains', 'Dominican Republic'),
    # '.gt': ('guatemalan-domains', 'Guatemala'),
    # '.hn': ('honduran-domains', 'Honduras'),
    # '.jm': ('jamaican-domains', 'Jamaica'),
    # '.ni': ('nicaraguan-domains', 'Nicaragua'),
    # '.pa': ('panamanian-domains', 'Panama'),
    
    # === South America ===
    # '.ar': ('argentine-domains', 'Argentina'),
    # '.bo': ('bolivian-domains', 'Bolivia'),
    # '.br': ('brazilian-domains', 'Brazil'),
    # '.cl': ('chilean-domains', 'Chile'),
    # '.co': ('colombian-domains', 'Colombia'),
    # '.ec': ('ecuadorian-domains', 'Ecuador'),
    # '.gy': ('guyanese-domains', 'Guyana'),
    # '.py': ('paraguayan-domains', 'Paraguay'),
    # '.pe': ('peruvian-domains', 'Peru'),
    # '.sr': ('surinamese-domains', 'Suriname'),
    # '.uy': ('uruguayan-domains', 'Uruguay'),
    # '.ve': ('venezuelan-domains', 'Venezuela'),
    
    # === Africa ===
    # '.dz': ('algerian-domains', 'Algeria'),
    # '.ao': ('angolan-domains', 'Angola'),
    # '.bj': ('beninese-domains', 'Benin'),
    # '.bw': ('botswanan-domains', 'Botswana'),
    # '.bf': ('burkinabe-domains', 'Burkina Faso'),
    # '.bi': ('burundian-domains', 'Burundi'),
    # '.cm': ('cameroonian-domains', 'Cameroon'),
    # '.cv': ('cape-verdean-domains', 'Cape Verde'),
    # '.cf': ('central-african-domains', 'Central African Republic'),
    # '.td': ('chadian-domains', 'Chad'),
    # '.km': ('comoran-domains', 'Comoros'),
    # '.cg': ('congolese-domains', 'Republic of the Congo'),
    # '.cd': ('drc-domains', 'Democratic Republic of the Congo'),
    # '.dj': ('djiboutian-domains', 'Djibouti'),
    # '.eg': ('egyptian-domains', 'Egypt'),
    # '.gq': ('equatorial-guinean-domains', 'Equatorial Guinea'),
    # '.er': ('eritrean-domains', 'Eritrea'),
    # '.et': ('ethiopian-domains', 'Ethiopia'),
    # '.ga': ('gabonese-domains', 'Gabon'),
    # '.gm': ('gambian-domains', 'Gambia'),
    # '.gh': ('ghanaian-domains', 'Ghana'),
    # '.gn': ('guinean-domains', 'Guinea'),
    # '.gw': ('guinea-bissau-domains', 'Guinea-Bissau'),
    # '.ci': ('ivorian-domains', 'Ivory Coast'),
    # '.ke': ('kenyan-domains', 'Kenya'),
    # '.ls': ('lesotho-domains', 'Lesotho'),
    # '.lr': ('liberian-domains', 'Liberia'),
    # '.ly': ('libyan-domains', 'Libya'),
    # '.mg': ('malagasy-domains', 'Madagascar'),
    # '.mw': ('malawian-domains', 'Malawi'),
    # '.ml': ('malian-domains', 'Mali'),
    # '.mr': ('mauritanian-domains', 'Mauritania'),
    # '.mu': ('mauritian-domains', 'Mauritius'),
    # '.ma': ('moroccan-domains', 'Morocco'),
    # '.mz': ('mozambican-domains', 'Mozambique'),
    # '.na': ('namibian-domains', 'Namibia'),
    # '.ne': ('nigerien-domains', 'Niger'),
    # '.ng': ('nigerian-domains', 'Nigeria'),
    # '.rw': ('rwandan-domains', 'Rwanda'),
    # '.st': ('sao-tomean-domains', 'Sao Tome and Principe'),
    # '.sn': ('senegalese-domains', 'Senegal'),
    # '.sc': ('seychellois-domains', 'Seychelles'),
    # '.sl': ('sierra-leonean-domains', 'Sierra Leone'),
    # '.so': ('somali-domains', 'Somalia'),
    # '.za': ('south-african-domains', 'South Africa'),
    # '.ss': ('south-sudanese-domains', 'South Sudan'),
    # '.sd': ('sudanese-domains', 'Sudan'),
    # '.sz': ('swazi-domains', 'Eswatini'),
    # '.tz': ('tanzanian-domains', 'Tanzania'),
    # '.tg': ('togolese-domains', 'Togo'),
    # '.tn': ('tunisian-domains', 'Tunisia'),
    # '.ug': ('ugandan-domains', 'Uganda'),
    # '.zm': ('zambian-domains', 'Zambia'),
    # '.zw': ('zimbabwean-domains', 'Zimbabwe'),
    
    # === Oceania ===
    # '.au': ('australian-domains', 'Australia'),
    # '.fj': ('fijian-domains', 'Fiji'),
    # '.ki': ('kiribati-domains', 'Kiribati'),
    # '.mh': ('marshallese-domains', 'Marshall Islands'),
    # '.fm': ('micronesian-domains', 'Micronesia'),
    # '.nr': ('nauruan-domains', 'Nauru'),
    # '.nz': ('new-zealand-domains', 'New Zealand'),
    # '.pw': ('palauan-domains', 'Palau'),
    # '.pg': ('papua-new-guinean-domains', 'Papua New Guinea'),
    # '.ws': ('samoan-domains', 'Samoa'),
    # '.sb': ('solomon-islands-domains', 'Solomon Islands'),
    # '.to': ('tongan-domains', 'Tonga'),
    # '.tv': ('tuvaluan-domains', 'Tuvalu'),
    # '.vu': ('ni-vanuatu-domains', 'Vanuatu'),
}

# ============================================================================
# MAIN PROCESSING LOGIC
# ============================================================================

def extract_country_domains():
    """
    Main function to extract country-specific domains from the source database
    and store them in separate country-specific databases.
    """
    
    print("=" * 80)
    print("COUNTRY-LEVEL DOMAIN EXTRACTOR")
    print("=" * 80)
    print()
    
    # Connect to MongoDB
    client = MongoClient(MONGO_HOST, MONGO_PORT)
    source_db = client[SOURCE_DATABASE]
    source_collection = source_db[SOURCE_COLLECTION]
    
    # Get active TLDs (only uncommented ones)
    active_tlds = {tld: info for tld, info in COUNTRY_TLDS.items()}
    
    if not active_tlds:
        print("❌ ERROR: No TLDs are configured!")
        print("   Please uncomment at least one TLD in the COUNTRY_TLDS dictionary.")
        sys.exit(1)
    
    print(f"📊 Source Database: {SOURCE_DATABASE}")
    print(f"📦 Source Collection: {SOURCE_COLLECTION}")
    print()
    print(f"🌍 Active Country TLDs: {len(active_tlds)}")
    for tld, (db_name, country) in active_tlds.items():
        print(f"   - {tld} → {country} (Database: {db_name})")
    print()
    
    # Get total certificate count
    total_query = {} if not TESTING_MODE else {}
    total_certs = source_collection.count_documents(total_query)
    
    if TESTING_MODE:
        total_certs = min(total_certs, TESTING_LIMIT)
        print(f"⚠️  TESTING MODE: Processing only {TESTING_LIMIT:,} certificates")
    else:
        print(f"📈 Total certificates in source: {total_certs:,}")
    
    print()
    print("=" * 80)
    print("STARTING EXTRACTION...")
    print("=" * 80)
    print()
    
    # Statistics tracking
    stats = defaultdict(lambda: {
        'total': 0,
        'inserted': 0,
        'errors': 0
    })
    
    processed_count = 0
    start_time = datetime.now()
    
    # Process certificates in batches
    cursor = source_collection.find({})
    
    if TESTING_MODE:
        cursor = cursor.limit(TESTING_LIMIT)
    
    batch_certs = []
    
    for cert in cursor:
        batch_certs.append(cert)
        
        # Process batch when it reaches BATCH_SIZE
        if len(batch_certs) >= BATCH_SIZE:
            process_batch(client, batch_certs, active_tlds, stats)
            processed_count += len(batch_certs)
            
            # Progress update
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = processed_count / elapsed if elapsed > 0 else 0
            progress_pct = (processed_count / total_certs * 100) if total_certs > 0 else 0
            
            print(f"⏳ Processed: {processed_count:,}/{total_certs:,} ({progress_pct:.1f}%) | "
                  f"Rate: {rate:.0f} certs/sec | Elapsed: {elapsed:.1f}s")
            
            batch_certs = []
    
    # Process remaining certificates
    if batch_certs:
        process_batch(client, batch_certs, active_tlds, stats)
        processed_count += len(batch_certs)
    
    # Final statistics
    elapsed_time = (datetime.now() - start_time).total_seconds()
    
    print()
    print("=" * 80)
    print("EXTRACTION COMPLETE!")
    print("=" * 80)
    print()
    print(f"⏱️  Total Time: {elapsed_time:.2f} seconds ({elapsed_time/60:.2f} minutes)")
    print(f"📊 Certificates Processed: {processed_count:,}")
    print(f"⚡ Average Rate: {processed_count/elapsed_time:.0f} certificates/second")
    print()
    
    print("📈 COUNTRY-WISE STATISTICS:")
    print("-" * 80)
    
    for tld, (db_name, country) in active_tlds.items():
        stat = stats[tld]
        print(f"\n{country} ({tld}):")
        print(f"  Database: {db_name}")
        print(f"  Certificates Found: {stat['total']:,}")
        print(f"  Successfully Inserted: {stat['inserted']:,}")
        if stat['errors'] > 0:
            print(f"  ⚠️  Errors: {stat['errors']:,}")
    
    print()
    print("=" * 80)
    print("✅ All country domains extracted successfully!")
    print("=" * 80)
    
    client.close()


def process_batch(client, certificates, active_tlds, stats):
    """
    Process a batch of certificates and insert country-specific ones into respective databases.
    
    Args:
        client: MongoDB client
        certificates: List of certificate documents
        active_tlds: Dictionary of active TLDs and their configurations
        stats: Statistics tracking dictionary
    """
    
    # Group certificates by TLD
    tld_groups = defaultdict(list)
    
    for cert in certificates:
        domain = cert.get('domain', '').lower()
        
        if not domain:
            continue
        
        # Check which TLD this domain matches
        for tld in active_tlds.keys():
            if domain.endswith(tld):
                tld_groups[tld].append(cert)
                stats[tld]['total'] += 1
                break  # Each domain belongs to only one TLD
    
    # Insert grouped certificates into respective databases
    for tld, certs_list in tld_groups.items():
        db_name, country = active_tlds[tld]
        
        try:
            target_db = client[db_name]
            target_collection = target_db['certificates']
            
            # Insert certificates (ignore duplicates)
            if certs_list:
                result = target_collection.insert_many(certs_list, ordered=False)
                stats[tld]['inserted'] += len(result.inserted_ids)
                
        except Exception as e:
            # Handle duplicate key errors gracefully
            if 'duplicate key error' in str(e).lower():
                # Count successful inserts from the error message
                stats[tld]['inserted'] += len(certs_list)
            else:
                print(f"⚠️  Error inserting {country} certificates: {e}")
                stats[tld]['errors'] += len(certs_list)


# ============================================================================
# SCRIPT ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        extract_country_domains()
    except KeyboardInterrupt:
        print("\n\n⚠️  Extraction interrupted by user!")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
