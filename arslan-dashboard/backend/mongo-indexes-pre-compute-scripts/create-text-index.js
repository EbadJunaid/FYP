// Create text index for fast search on domain and common name
db = db.getSiblingDB('tranco-latest-8-lakh');

print('Creating text index for search optimization...');

// Create compound text index on domain and common_name fields
db.certificates.createIndex(
    {
        "domain": "text",
        "parsed.subject.common_name": "text"
    },
    {
        name: "idx_text_search",
        default_language: "english",
        weights: {
            "domain": 10,  // Domain matches are more important
            "parsed.subject.common_name": 5
        }
    }
);

print('✓ Text index created successfully!');
print('Index name: idx_text_search');
print('This index enables fast text search on domain and common_name fields');
