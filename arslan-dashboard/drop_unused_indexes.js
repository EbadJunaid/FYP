// ================================================================
// Drop Unused MongoDB Indexes
// Run this with: mongosh tranco-latest-8-lakh drop_unused_indexes.js
//
// This removes indexes that are not used by the API and waste space:
// - idx_zlint_compound (14.4 GB, never used)
// - idx_validity_range (compound index, idx_validity_end is enough)
// ================================================================

print("\n" + "=".repeat(70));
print("  DROPPING UNUSED MONGODB INDEXES");
print("=".repeat(70) + "\n");

// Get current index stats
print("📊 Current Index Statistics:\n");
var stats = db.certificates.stats();
var indexes = db.certificates.getIndexes();

indexes.forEach(function(idx) {
    var sizeBytes = stats.indexSizes[idx.name] || 0;
    var sizeMB = (sizeBytes / 1024 / 1024).toFixed(2);
    var sizeGB = (sizeBytes / 1024 / 1024 / 1024).toFixed(2);
    
    var sizeStr = sizeGB > 1 ? sizeGB + " GB" : sizeMB + " MB";
    print("  " + idx.name.padEnd(30) + " - " + sizeStr);
});

print("\n" + "=".repeat(70));
print("Dropping unused indexes...\n");

// ================================================================
// Drop idx_zlint_compound (14.4 GB, never used)
// ================================================================
try {
    print("1️⃣  Dropping idx_zlint_compound...");
    var result1 = db.certificates.dropIndex("idx_zlint_compound");
    if (result1.ok === 1) {
        print("   ✅ Dropped successfully (was 14.4 GB)\n");
    }
} catch (e) {
    if (e.code === 27) {
        print("   ⚠️  Index doesn't exist (already dropped)\n");
    } else {
        print("   ❌ Error: " + e.message + "\n");
    }
}

// ================================================================
// Drop idx_validity_range (compound, not needed)
// ================================================================
try {
    print("2️⃣  Dropping idx_validity_range...");
    var result2 = db.certificates.dropIndex("idx_validity_range");
    if (result2.ok === 1) {
        print("   ✅ Dropped successfully (idx_validity_end is enough)\n");
    }
} catch (e) {
    if (e.code === 27) {
        print("   ⚠️  Index doesn't exist (already dropped)\n");
    } else {
        print("   ❌ Error: " + e.message + "\n");
    }
}

print("=".repeat(70));
print("\n✅ Cleanup complete!\n");
print("=".repeat(70));

// Show updated stats
print("\n📊 Updated Index Statistics:\n");
stats = db.certificates.stats();
indexes = db.certificates.getIndexes();

var totalSize = 0;
indexes.forEach(function(idx) {
    var sizeBytes = stats.indexSizes[idx.name] || 0;
    totalSize += sizeBytes;
    var sizeMB = (sizeBytes / 1024 / 1024).toFixed(2);
    print("  ✓ " + idx.name.padEnd(30) + " - " + sizeMB + " MB");
});

var totalMB = (totalSize / 1024 / 1024).toFixed(2);
var totalGB = (totalSize / 1024 / 1024 / 1024).toFixed(2);
var totalStr = totalGB > 1 ? totalGB + " GB" : totalMB + " MB";

print("\n" + "=".repeat(70));
print("📦 Total Index Size: " + totalStr);
print("=".repeat(70) + "\n");
