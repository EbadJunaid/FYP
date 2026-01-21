#!/bin/bash
# Test all optimized APIs and verify performance

echo "========================================================================"
echo "🚀 SSL DASHBOARD API PERFORMANCE TEST"
echo "========================================================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

BASE_URL="http://localhost:8000"

test_api() {
    local endpoint=$1
    local name=$2
    local threshold=$3
    
    echo -e "${BLUE}Testing:${NC} $name"
    echo -e "${BLUE}Endpoint:${NC} $endpoint"
    
    # Get response time
    response_time=$(curl -s -w "%{time_total}" -o /dev/null "$BASE_URL$endpoint")
    
    # Convert to milliseconds for comparison
    response_ms=$(echo "$response_time * 1000" | bc)
    threshold_ms=$(echo "$threshold * 1000" | bc)
    
    # Compare
    if (( $(echo "$response_ms < $threshold_ms" | bc -l) )); then
        echo -e "${GREEN}✓ PASS${NC} - Response time: ${response_time}s (< ${threshold}s)"
    else
        echo -e "${RED}✗ FAIL${NC} - Response time: ${response_time}s (>= ${threshold}s)"
    fi
    echo ""
}

echo "Testing API performance..."
echo ""

# Test each API with threshold
test_api "/api/global-health/" "Global Health API" "0.5"
test_api "/api/encryption-strength/" "Encryption Strength API" "0.5"
test_api "/api/certificates/" "Certificates API" "0.5"
test_api "/api/ca-analytics/" "CA Analytics API (Materialized)" "0.1"
test_api "/api/geographic-distribution/" "Geographic Distribution API (Materialized)" "0.1"

echo "========================================================================"
echo "✅ Performance test complete!"
echo "========================================================================"
echo ""
echo "Expected performance:"
echo "  - Indexed APIs: < 0.2s"
echo "  - Materialized View APIs: < 0.1s"
echo ""
echo "If any test failed, check:"
echo "  1. Django server is running"
echo "  2. MongoDB is running"
echo "  3. Pre-computed data exists (run compute_*.py scripts)"
echo "  4. No filters are being applied (materialized views don't support filters)"
