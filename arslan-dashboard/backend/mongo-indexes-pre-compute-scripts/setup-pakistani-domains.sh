#!/bin/bash
# ============================================================================
# Complete Setup Script for Pakistani Domains Database
# ============================================================================
#
# This script:
# 1. Creates all necessary indexes on pakistani-domains database
# 2. Runs all pre-compute scripts to generate analytics collections
# 3. Creates pakistani-domains-results database with all required collections
#
# Usage: ./setup-pakistani-domains.sh
# ============================================================================

set -e  # Exit on any error

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}============================================================================${NC}"
echo -e "${BOLD}  PAKISTANI DOMAINS DATABASE SETUP${NC}"
echo -e "${BOLD}============================================================================${NC}"
echo ""

# ============================================================================
# STEP 1: Create Indexes
# ============================================================================

echo -e "${BLUE}${BOLD}[STEP 1/3]${NC} ${BLUE}Creating indexes on pakistani-domains database...${NC}"
echo ""

mongosh pakistani-domains create-indexes-pakistani.js

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Indexes created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create indexes${NC}"
    exit 1
fi

echo ""
echo -e "${BOLD}----------------------------------------------------------------------------${NC}"
echo ""

# ============================================================================
# STEP 2: Create Pre-Computed Collections
# ============================================================================

echo -e "${BLUE}${BOLD}[STEP 2/3]${NC} ${BLUE}Running pre-compute scripts...${NC}"
echo -e "${YELLOW}This will take approximately 15-20 minutes for ~7,700 certificates${NC}"
echo ""

# Activate Python environment
source ~/.pyenv/versions/SSL-crawler/bin/activate || pyenv activate SSL-crawler

# List of all pre-compute scripts (in order of dependency)
SCRIPTS=(
    "compute-ca-stats.py"
    "compute-ca-analytics.py"
    "compute-signature-stats.py"
    "compute-validity-stats.py"
    "compute-validity-distribution.py"
    "compute-geographic-distribution.py"
    "compute-hash-trends.py"
    "compute-issuance-timeline.py"
    "compute-issuer-algorithm-matrix.py"
    "compute-issuer-validation-matrix.py"
    "compute-san-stats.py"
    "compute-san-distribution.py"
    "compute-san-wildcard-breakdown.py"
    "compute-san-tld-breakdown.py"
    "compute-san-filtered-lists-v2.py"
    "compute-shared-keys.py"
)

FAILED_SCRIPTS=()
SUCCESS_COUNT=0

for script in "${SCRIPTS[@]}"; do
    echo -e "${BLUE}▶ Running: ${script}${NC}"
    
    # Create modified version for pakistani-domains
    TEMP_SCRIPT="temp_pk_${script}"
    
    # Replace database names in script
    sed -e "s/'tranco-latest-8-lakh'/'pakistani-domains'/g" \
        -e "s/'tranco-latest-8-lakh-results'/'pakistani-domains-results'/g" \
        -e "s/\"tranco-latest-8-lakh\"/\"pakistani-domains\"/g" \
        -e "s/\"tranco-latest-8-lakh-results\"/\"pakistani-domains-results\"/g" \
        -e "s/tranco-latest-8-lakh/pakistani-domains/g" \
        "${script}" > "${TEMP_SCRIPT}"
    
    # Run the modified script
    if timeout 600 python3 "${TEMP_SCRIPT}"; then
        echo -e "${GREEN}✅ Completed: ${script}${NC}"
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        rm "${TEMP_SCRIPT}"
    else
        echo -e "${RED}❌ Failed: ${script}${NC}"
        FAILED_SCRIPTS+=("${script}")
        rm "${TEMP_SCRIPT}"
    fi
    
    echo ""
done

echo ""
echo -e "${BOLD}----------------------------------------------------------------------------${NC}"
echo ""

# ============================================================================
# STEP 3: Verification
# ============================================================================

echo -e "${BLUE}${BOLD}[STEP 3/3]${NC} ${BLUE}Verifying setup...${NC}"
echo ""

# Create verification script
cat > verify_pakistani_setup.py << 'EOF'
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')

print("=" * 70)
print("VERIFICATION REPORT")
print("=" * 70)
print()

# Check main database
pk_db = client['pakistani-domains']
cert_count = pk_db.certificates.count_documents({})
pk_indexes = pk_db.certificates.list_indexes()
index_count = len(list(pk_indexes))

print(f"📊 pakistani-domains.certificates:")
print(f"   Certificates: {cert_count:,}")
print(f"   Indexes: {index_count}")
print()

# Check results database
results_db = client['pakistani-domains-results']
collections = sorted(results_db.list_collection_names())

print(f"📊 pakistani-domains-results:")
print(f"   Collections: {len(collections)}")
print()

if collections:
    print("Collections created:")
    for coll in collections:
        count = results_db[coll].count_documents({})
        print(f"   ✓ {coll.ljust(35)} - {count:,} documents")
else:
    print("   ⚠️  No collections found!")

print()
print("=" * 70)
EOF

python3 verify_pakistani_setup.py
rm verify_pakistani_setup.py

echo ""
echo -e "${BOLD}============================================================================${NC}"
echo -e "${BOLD}  SETUP SUMMARY${NC}"
echo -e "${BOLD}============================================================================${NC}"
echo ""
echo -e "${GREEN}✅ Successful scripts: ${SUCCESS_COUNT}/${#SCRIPTS[@]}${NC}"

if [ ${#FAILED_SCRIPTS[@]} -gt 0 ]; then
    echo -e "${RED}❌ Failed scripts: ${#FAILED_SCRIPTS[@]}${NC}"
    for script in "${FAILED_SCRIPTS[@]}"; do
        echo -e "   ${RED}• ${script}${NC}"
    done
    echo ""
    echo -e "${YELLOW}⚠️  Some scripts failed. You may need to run them manually.${NC}"
else
    echo -e "${GREEN}✅ All scripts completed successfully!${NC}"
fi

echo ""
echo -e "${BOLD}============================================================================${NC}"
echo -e "${GREEN}${BOLD}✅ Pakistani domains database setup complete!${NC}"
echo -e "${BOLD}============================================================================${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "  1. Update backend Django settings to use pakistani-domains"
echo -e "  2. Update frontend API endpoints if needed"
echo -e "  3. Test dashboard with new database"
echo ""
