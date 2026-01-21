// Create index on validity.length for fast validity bucket filtering
// This enables fast queries like: validity_bucket=90-365

db.certificates.createIndex(
    { "parsed.validity.length": 1 },
    { 
        name: "idx_validity_length",
        background: true
    }
);

print("✅ Index idx_validity_length created on parsed.validity.length");
