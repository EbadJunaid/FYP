// ================================================================
// Complete MongoDB Index Creation for Pakistani Domains
// Creates ALL indexes from tranco-latest-8-lakh for compatibility
// 
// Run: mongosh pakistani-domains create-all-indexes-pakistani.js
// ================================================================

print("\n" + "=".repeat(70));
print("  CREATING ALL INDEXES FOR PAKISTANI-DOMAINS");
print("=".repeat(70) + "\n");

db = db.getSiblingDB('pakistani-domains');

// 1. Validity end (expiration queries)
print("1️⃣  idx_validity_end");
db.certificates.createIndex(
    { "parsed.validity.end": 1 },
    { name: "idx_validity_end", background: true }
);

// 2. Zlint errors (vulnerability count)
print("2️⃣  idx_zlint_errors");
db.certificates.createIndex(
    { "zlint.errors_present": 1 },
    { name: "idx_zlint_errors", background: true }
);

// 3. Domain (search queries)
print("3️⃣  idx_domain");
db.certificates.createIndex(
    { "domain": 1 },
    { name: "idx_domain", background: true }
);

// 4. Issuer organization (CA analytics)
print("4️⃣  idx_issuer_org");
db.certificates.createIndex(
    { "parsed.issuer.organization": 1 },
    { name: "idx_issuer_org", background: true }
);

// 5. Signature algorithm
print("5️⃣  idx_signature_algo");
db.certificates.createIndex(
    { "parsed.signature_algorithm.name": 1 },
    { name: "idx_signature_algo", background: true }
);

// 6. Validity start
print("6️⃣  idx_validity_start");
db.certificates.createIndex(
    { "parsed.validity.start": 1 },
    { name: "idx_validity_start", background: true }
);

// 7. Self-signed (CRITICAL - used by compute-ca-stats.py)
print("7️⃣  idx_self_signed");
db.certificates.createIndex(
    { "parsed.signature.self_signed": 1 },
    { name: "idx_self_signed", background: true }
);

// 8. SAN DNS names
print("8️⃣  idx_san_dns_names");
db.certificates.createIndex(
    { "parsed.extensions.subject_alt_name.dns_names": 1 },
    { name: "idx_san_dns_names", background: true }
);

// 9. Common name
print("9️⃣  idx_common_name");
db.certificates.createIndex(
    { "parsed.subject.common_name": 1 },
    { name: "idx_common_name", background: true }
);

// 10. RSA key algorithm + length
print("🔟 idx_algo_rsa_length");
db.certificates.createIndex(
    {
        "parsed.subject_key_info.key_algorithm.name": 1,
        "parsed.subject_key_info.rsa_public_key.length": 1
    },
    { name: "idx_algo_rsa_length", background: true }
);

// 11. ECDSA key algorithm + length
print("1️⃣1️⃣  idx_algo_ecdsa_length");
db.certificates.createIndex(
    {
        "parsed.subject_key_info.key_algorithm.name": 1,
        "parsed.subject_key_info.ecdsa_public_key.length": 1
    },
    { name: "idx_algo_ecdsa_length", background: true }
);

// 12. Issuer org primary
print("1️⃣2️⃣  idx_issuer_org_primary");
db.certificates.createIndex(
    { "parsed.issuer_org_primary": 1 },
    { name: "idx_issuer_org_primary", background: true }
);

// 13. Issuer country
print("1️⃣3️⃣  idx_issuer_country");
db.certificates.createIndex(
    { "parsed.issuer.country": 1 },
    { name: "idx_issuer_country", background: true }
);

// 14. Validation level
print("1️⃣4️⃣  idx_validation_level");
db.certificates.createIndex(
    { "parsed.validation_level": 1 },
    { name: "idx_validation_level", background: true }
);

// 15. Key algorithm
print("1️⃣5️⃣  idx_key_algo");
db.certificates.createIndex(
    { "parsed.subject_key_info.key_algorithm.name": 1 },
    { name: "idx_key_algo", background: true }
);

// 16. Text search (domain + common name)
print("1️⃣6️⃣  idx_text_search");
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

// 17. Validity length
print("1️⃣7️⃣  idx_validity_length");
db.certificates.createIndex(
    { "parsed.validity.length": 1 },
    { name: "idx_validity_length", background: true }
);

// 18. Public key fingerprint
print("1️⃣8️⃣  idx_public_key_fingerprint");
db.certificates.createIndex(
    { "parsed.subject_key_info.fingerprint_sha256": 1 },
    { name: "idx_public_key_fingerprint", background: true }
);

print("\n" + "=".repeat(70));
print("✅ All 18 indexes created successfully!");
print("=".repeat(70) + "\n");

print("Verifying indexes...\n");
var indexes = db.certificates.getIndexes();
print("Total indexes: " + indexes.length + " (including _id)\n");

indexes.forEach(function(idx) {
    var stats = db.certificates.stats();
    var sizeInfo = stats.indexSizes ? stats.indexSizes[idx.name] : null;
    var sizeMB = sizeInfo ? (sizeInfo / 1024 / 1024).toFixed(2) : "0.00";
    print("  ✓ " + idx.name.padEnd(30) + sizeMB.padStart(8) + " MB");
});

print("\n" + "=".repeat(70));
