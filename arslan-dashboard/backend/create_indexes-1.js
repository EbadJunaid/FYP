    // ================================================================
// MongoDB Index Creation Script for SSL Dashboard
// Run this with: mongosh tranco-latest-8-lakh create_indexes.js
// 
// This creates ONLY the indexes that are actually used by the API.
// Removed huge unused indexes to save disk space.
// ================================================================

print("\n" + "=".repeat(70));
print("  CREATING MONGODB INDEXES FOR SSL DASHBOARD");
print("=".repeat(70) + "\n");

// ================================================================
// CRITICAL INDEXES (Used by /api/dashboard/global-health/)
// ================================================================

// 1. Index on validity.end for expiration queries
// Used by: Expired count, Expiring soon count
// Query: {"parsed.validity.end": {$lt: "date"}}
print("1️⃣  Creating idx_validity_end...");
db.certificates.createIndex(
    { "parsed.validity.end": 1 },
    { name: "idx_validity_end", background: true }
);
print("   ✅ Created (used for expiration queries)\n");

// 2. Index on zlint.errors_present for vulnerability counts
// Used by: Vulnerability count
// Query: {"zlint.errors_present": true}
print("2️⃣  Creating idx_zlint_errors...");
db.certificates.createIndex(
    { "zlint.errors_present": 1 },
    { name: "idx_zlint_errors", background: true }
);
print("   ✅ Created (used for vulnerability count)\n");

// ================================================================
// ADDITIONAL INDEXES (Used by other APIs)
// ================================================================

// 3. Index on domain for search queries
// Used by: /api/certificates/?search=domain
print("3️⃣  Creating idx_domain...");
db.certificates.createIndex(
    { "domain": 1 },
    { name: "idx_domain", background: true }
);
print("   ✅ Created (used for domain search)\n");

// 4. Index on issuer organization for CA analytics
// Used by: /api/ca-analytics/
print("4️⃣  Creating idx_issuer_org...");
db.certificates.createIndex(
    { "parsed.issuer.organization": 1 },
    { name: "idx_issuer_org", background: true }
);
print("   ✅ Created (used for CA analytics)\n");

// 5. Index on signature algorithm for signature analytics
// Used by: /api/signature-stats/
print("5️⃣  Creating idx_signature_algo...");
db.certificates.createIndex(
    { "parsed.signature_algorithm.name": 1 },
    { name: "idx_signature_algo", background: true }
);
print("   ✅ Created (used for signature analytics)\n");

// 6. Index on key algorithm for encryption analytics
// Used by: /api/encryption-strength/
print("6️⃣  Creating idx_key_algo...");
db.certificates.createIndex(
    { "parsed.subject_key_info.key_algorithm.name": 1 },
    { name: "idx_key_algo", background: true }
);
print("   ✅ Created (used for encryption analytics)\n");

// ================================================================
// REMOVED INDEXES (Not used, waste space)
// ================================================================
// ❌ idx_zlint_compound - 14.4 GB, never used (removed)
// ❌ idx_validity_range - Compound index, idx_validity_end is enough

print("=".repeat(70));
print("\n✅ All 6 indexes created successfully!\n");
print("=".repeat(70));

print("\nVerifying indexes...");
var indexes = db.certificates.getIndexes();
print("Found " + indexes.length + " indexes:\n");

indexes.forEach(function(idx) {
    var sizeInfo = db.certificates.stats().indexSizes[idx.name];
    var sizeMB = sizeInfo ? (sizeInfo / 1024 / 1024).toFixed(2) : "N/A";
    print("  ✓ " + idx.name.padEnd(25) + " - " + sizeMB + " MB");
});

print("\n" + "=".repeat(70));
print("✅ Index creation complete!");
print("=".repeat(70) + "\n");
