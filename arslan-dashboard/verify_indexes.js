// ================================================================
// INDEX VERIFICATION AND PERFORMANCE DIAGNOSIS
// Run this script to diagnose why queries are slow
// Usage: mongosh tranco-latest-8-lakh verify_indexes.js
// ================================================================

print("\n" + "=".repeat(70));
print("  INDEX VERIFICATION & PERFORMANCE DIAGNOSIS");
print("=".repeat(70) + "\n");

// ================================================================
// STEP 1: List all indexes
// ================================================================
print("📋 STEP 1: Checking existing indexes...\n");
var indexes = db.certificates.getIndexes();
print("Found " + indexes.length + " indexes:\n");

indexes.forEach(function(idx) {
    print("  ✓ " + idx.name);
    print("    Keys: " + JSON.stringify(idx.key));
    if (idx.unique) print("    Type: UNIQUE");
    print("");
});

// ================================================================
// STEP 2: Check if critical indexes exist
// ================================================================
print("\n" + "=".repeat(70));
print("📋 STEP 2: Verifying critical indexes...\n");

var requiredIndexes = [
    "idx_validity_end",
    "idx_zlint_errors"
];

var missingIndexes = [];
requiredIndexes.forEach(function(name) {
    var found = indexes.some(function(idx) { return idx.name === name; });
    if (found) {
        print("  ✅ " + name + " - EXISTS");
    } else {
        print("  ❌ " + name + " - MISSING!");
        missingIndexes.push(name);
    }
});

if (missingIndexes.length > 0) {
    print("\n⚠️  WARNING: Missing " + missingIndexes.length + " critical indexes!");
    print("   Run create_indexes.js to create them.\n");
}

// ================================================================
// STEP 3: Test if indexes are being USED in queries
// ================================================================
print("\n" + "=".repeat(70));
print("📋 STEP 3: Testing if indexes are being used...\n");

// Get current date for testing
var now = new Date().toISOString().replace('.000Z', 'Z');
print("Using current date for tests: " + now + "\n");

// Test 1: Validity query
print("Test 1: Checking validity.end query...");
var explainValidityEnd = db.certificates.find({
    "parsed.validity.end": {$lt: now}
}).limit(1).explain("executionStats");

if (explainValidityEnd.executionStats.executionStages.stage === "IXSCAN" || 
    (explainValidityEnd.executionStats.executionStages.inputStage && 
     explainValidityEnd.executionStats.executionStages.inputStage.stage === "IXSCAN")) {
    print("  ✅ USING INDEX: " + 
          (explainValidityEnd.executionStats.executionStages.indexName || 
           explainValidityEnd.executionStats.executionStages.inputStage.indexName));
} else {
    print("  ❌ NOT USING INDEX - doing COLLECTION SCAN!");
    print("     Stage: " + explainValidityEnd.executionStats.executionStages.stage);
}
print("");

// Test 2: Zlint errors query
print("Test 2: Checking zlint.errors_present query...");
var explainZlint = db.certificates.find({
    "zlint.errors_present": true
}).limit(1).explain("executionStats");

if (explainZlint.executionStats.executionStages.stage === "IXSCAN" ||
    (explainZlint.executionStats.executionStages.inputStage && 
     explainZlint.executionStats.executionStages.inputStage.stage === "IXSCAN")) {
    print("  ✅ USING INDEX: " + 
          (explainZlint.executionStats.executionStages.indexName || 
           explainZlint.executionStats.executionStages.inputStage.indexName));
} else {
    print("  ❌ NOT USING INDEX - doing COLLECTION SCAN!");
    print("     Stage: " + explainZlint.executionStats.executionStages.stage);
}
print("");

// ================================================================
// STEP 4: Performance benchmark
// ================================================================
print("\n" + "=".repeat(70));
print("📋 STEP 4: Running performance benchmark...\n");
print("⏱️  Testing query speed with index hints...\n");

// Benchmark 1: Estimated count
var start = new Date();
var totalCount = db.certificates.estimatedDocumentCount();
var t1 = (new Date() - start);
print("Query 1: Total count (estimated)");
print("  Result: " + totalCount + " documents");
print("  Time: " + t1 + "ms");
print("  Expected: < 10ms");
if (t1 < 100) {
    print("  ✅ FAST");
} else {
    print("  ⚠️  SLOW");
}
print("");

// Benchmark 2: Expired count with hint
start = new Date();
var expiredCount = db.certificates.count(
    {"parsed.validity.end": {$lt: now}},
    {hint: "idx_validity_end"}
);
var t2 = (new Date() - start);
print("Query 2: Expired count (with index hint)");
print("  Result: " + expiredCount + " documents");
print("  Time: " + t2 + "ms");
print("  Expected: < 1000ms");
if (t2 < 2000) {
    print("  ✅ FAST");
} else {
    print("  ⚠️  SLOW");
}
print("");

// Benchmark 3: Vulnerabilities with hint
start = new Date();
var vulnCount = db.certificates.count(
    {"zlint.errors_present": true},
    {hint: "idx_zlint_errors"}
);
var t3 = (new Date() - start);
print("Query 3: Vulnerabilities count (with index hint)");
print("  Result: " + vulnCount + " documents");
print("  Time: " + t3 + "ms");
print("  Expected: < 1000ms");
if (t3 < 2000) {
    print("  ✅ FAST");
} else {
    print("  ⚠️  SLOW");
}
print("");

var totalTime = t1 + t2 + t3;
print("⏱️  Total time for all queries: " + totalTime + "ms (" + (totalTime/1000).toFixed(2) + "s)");
print("   Expected total: < 3 seconds\n");

// ================================================================
// STEP 5: Database statistics
// ================================================================
print("\n" + "=".repeat(70));
print("📋 STEP 5: Database statistics...\n");

var stats = db.certificates.stats();
print("Collection statistics:");
print("  Documents: " + stats.count.toLocaleString());
print("  Data size: " + (stats.size / 1024 / 1024).toFixed(2) + " MB");
print("  Index size: " + (stats.totalIndexSize / 1024 / 1024).toFixed(2) + " MB");
print("  Average document size: " + stats.avgObjSize + " bytes");
print("");

// Check if indexes fit in RAM
var memStats = db.serverStatus().mem;
print("Memory statistics:");
print("  Resident: " + memStats.resident + " MB");
print("  Virtual: " + memStats.virtual + " MB");
print("");

var indexSizeMB = stats.totalIndexSize / 1024 / 1024;
if (indexSizeMB < memStats.resident * 0.5) {
    print("  ✅ Indexes likely fit in RAM (good performance)");
} else {
    print("  ⚠️  Indexes may not fit in RAM (potential performance issue)");
}
print("");

// ================================================================
// STEP 6: Recommendations
// ================================================================
print("\n" + "=".repeat(70));
print("📋 STEP 6: Recommendations...\n");

if (totalTime < 3000) {
    print("✅ PERFORMANCE: Excellent! Queries are fast.");
    print("   API should respond in < 5 seconds.");
} else if (totalTime < 10000) {
    print("⚠️  PERFORMANCE: Acceptable but could be better.");
    print("   Consider these optimizations:");
    print("   1. Ensure MongoDB has enough RAM");
    print("   2. Check for concurrent operations: db.currentOp()");
    print("   3. Consider using estimated counts instead of exact counts");
} else {
    print("❌ PERFORMANCE: SLOW! Queries are taking too long.");
    print("   Possible issues:");
    print("   1. Indexes not being used (check STEP 3 above)");
    print("   2. Insufficient RAM for indexes");
    print("   3. Database under heavy load");
    print("   4. Disk I/O bottleneck");
    print("\n   Run these commands to diagnose:");
    print("   - db.currentOp() // Check for blocking operations");
    print("   - db.serverStatus() // Check server health");
}

print("\n" + "=".repeat(70));
print("✅ Diagnosis complete!");
print("=".repeat(70) + "\n");
