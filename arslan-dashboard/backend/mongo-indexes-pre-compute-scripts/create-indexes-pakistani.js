// ================================================================
// MongoDB Index Creation Script for Pakistani Domains Database
// Run this with: mongosh pakistani-domains create-indexes-pakistani.js
// 
// Creates the same indexes as tranco-latest-8-lakh for consistency
// ================================================================

print("\n" + "=".repeat(70));
print("  CREATING INDEXES FOR PAKISTANI-DOMAINS DATABASE");
print("=".repeat(70) + "\n");

// Switch to pakistani-domains database
db = db.getSiblingDB('pakistani-domains');

// ================================================================
// CRITICAL INDEXES (Used by /api/dashboard/global-health/)
// ================================================================

// 1. Index on validity.end for expiration queries
print("1️⃣  Creating idx_validity_end...");
db.certificates.createIndex(
    { "parsed.validity.end": 1 },
    { name: "idx_validity_end", background: true }
);
print("   ✅ Created (used for expiration queries)\n");

// 2. Index on zlint.errors_present for vulnerability counts
print("2️⃣  Creating idx_zlint_errors...");
db.certificates.createIndex(
    { "zlint.errors_present": 1 },
    { name: "idx_zlint_errors", background: true }
);
print("   ✅ Created (used for vulnerability count)\n");

// 3. Index on domain for search queries
print("3️⃣  Creating idx_domain...");
db.certificates.createIndex(
    { "domain": 1 },
    { name: "idx_domain", background: true }
);
print("   ✅ Created (used for domain search)\n");

// 4. Index on issuer organization for CA analytics
print("4️⃣  Creating idx_issuer_org...");
db.certificates.createIndex(
    { "parsed.issuer.organization": 1 },
    { name: "idx_issuer_org", background: true }
);
print("   ✅ Created (used for CA analytics)\n");

// 5. Index on signature algorithm for signature analytics
print("5️⃣  Creating idx_signature_algo...");
db.certificates.createIndex(
    { "parsed.signature_algorithm.name": 1 },
    { name: "idx_signature_algo", background: true }
);
print("   ✅ Created (used for signature analytics)\n");

// 6. Index on key algorithm for encryption analytics
print("6️⃣  Creating idx_key_algo...");
db.certificates.createIndex(
    { "parsed.subject_key_info.key_algorithm.name": 1 },
    { name: "idx_key_algo", background: true }
);
print("   ✅ Created (used for encryption analytics)\n");

// 7. Text index for fast domain and common name search
print("7️⃣  Creating idx_text_search...");
db.certificates.createIndex(
    {
        "domain": "text",
        "parsed.subject.common_name": "text"
    },
    {
        name: "idx_text_search",
        default_language: "english",
        weights: {
            "domain": 10,
            "parsed.subject.common_name": 5
        }
    }
);
print("   ✅ Created (text search index)\n");

// 8. Index on validity.length for validity bucket filtering
print("8️⃣  Creating idx_validity_length...");
db.certificates.createIndex(
    { "parsed.validity.length": 1 },
    { 
        name: "idx_validity_length",
        background: true
    }
);
print("   ✅ Created (used for validity bucket filters)\n");

print("=".repeat(70));
print("\n✅ All 8 indexes created successfully!\n");
print("=".repeat(70));

print("\nVerifying indexes...");
var indexes = db.certificates.getIndexes();
print("Found " + indexes.length + " indexes (including default _id):\n");

indexes.forEach(function(idx) {
    var stats = db.certificates.stats();
    var sizeInfo = stats.indexSizes ? stats.indexSizes[idx.name] : null;
    var sizeMB = sizeInfo ? (sizeInfo / 1024 / 1024).toFixed(2) : "N/A";
    print("  ✓ " + idx.name.padEnd(25) + " - " + sizeMB + " MB");
});

print("\n" + "=".repeat(70));
print("✅ Index creation complete for pakistani-domains!");
print("=".repeat(70) + "\n");
