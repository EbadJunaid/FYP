// ==============================================================================
// FINAL FIX: Use $sample or LIMIT to avoid processing all 878K docs
// ==============================================================================

print("\n" + "=".repeat(80))
print("🚀 FINAL SOLUTION TEST - Using Sampling")
print("=".repeat(80))

// ==============================================================================
// APPROACH 1: Use $sample for approximate results (FASTEST)
// ==============================================================================
print("\n1️⃣  APPROACH 1: Sample-based (10,000 docs)")

var sample1Start = Date.now()

var sampleResult = db.certificates.aggregate([
  { $sample: { size: 10000 } },  // Sample 10K random docs
  { 
    $group: {
      _id: "$parsed.issuer.organization",
      count: { $sum: 1 }
    }
  },
  { $sort: { count: -1 } },
  { $limit: 10 }
]).toArray()

var sample1Time = (Date.now() - sample1Start) / 1000
print("   Time: " + sample1Time.toFixed(2) + "s")
print("   Top CA: " + (sampleResult[0]._id[0] || 'Unknown'))


// ==============================================================================
// APPROACH 2: Use distinct() for unique count (VERY FAST)
// ==============================================================================
print("\n2️⃣  APPROACH 2: Use distinct() for unique CAs")

var distinct1Start = Date.now()

var uniqueCAs = db.certificates.distinct("parsed.issuer.organization")

var distinct1Time = (Date.now() - distinct1Start) / 1000
print("   Time: " + distinct1Time.toFixed(2) + "s")
print("   Unique CAs: " + uniqueCAs.length)


// ==============================================================================
// APPROACH 3: Pre-filter with $match to reduce dataset
// ==============================================================================
print("\n3️⃣  APPROACH 3: Filter by recent certs only (last 90 days)")

var filter1Start = Date.now()

var now = new Date()
var ninetyDaysAgo = new Date(now - 90*24*60*60*1000)
var dateStr = ninetyDaysAgo.toISOString()

var filteredResult = db.certificates.aggregate([
  { 
    $match: { 
      "parsed.validity.end": { $gte: dateStr }  // Only active/recent certs
    }
  },
  { 
    $group: {
      _id: "$parsed.issuer.organization",
      count: { $sum: 1 }
    }
  },
  { $sort: { count: -1 } },
  { $limit: 10 }
], { hint: "idx_validity_end", allowDiskUse: true }).toArray()

var filter1Time = (Date.now() - filter1Start) / 1000
print("   Time: " + filter1Time.toFixed(2) + "s")
print("   Top CA: " + (filteredResult[0]._id[0] || 'Unknown'))


// ==============================================================================
// APPROACH 4: Hybrid - Sample THEN full aggregation
// ==============================================================================
print("\n4️⃣  APPROACH 4: Two-phase (sample for top CAs, then precise count)")

var hybrid1Start = Date.now()

// Phase 1: Sample to find top CAs
var topCAs = db.certificates.aggregate([
  { $sample: { size: 50000 } },
  { 
    $group: {
      _id: "$parsed.issuer.organization",
      count: { $sum: 1 }
    }
  },
  { $sort: { count: -1 } },
  { $limit: 10 }
]).toArray()

// Extract top CA names
var topCANames = topCAs.map(ca => ca._id)

// Phase 2: Get exact counts for only the top CAs
var exactCounts = db.certificates.aggregate([
  {
    $match: {
      "parsed.issuer.organization": { $in: topCANames }
    }
  },
  {
    $group: {
      _id: "$parsed.issuer.organization",
      count: { $sum: 1 }
    }
  },
  { $sort: { count: -1 } }
], { hint: "idx_issuer_org", allowDiskUse: true }).toArray()

var hybrid1Time = (Date.now() - hybrid1Start) / 1000
print("   Time: " + hybrid1Time.toFixed(2) + "s")
print("   Top CA (precise): " + (exactCounts[0]._id[0] || 'Unknown') + " (" + exactCounts[0].count + ")")


// ==============================================================================
// RESULTS COMPARISON
// ==============================================================================
print("\n" + "=".repeat(80))
print("📊 PERFORMANCE COMPARISON:")
print("=".repeat(80))
print("Sample-based (10K):        " + sample1Time.toFixed(2) + "s  ✅ FASTEST")
print("Distinct for unique:       " + distinct1Time.toFixed(2) + "s  ✅ FAST")
print("Filter by date:            " + filter1Time.toFixed(2) + "s  ✅ GOOD")
print("Hybrid (sample + precise): " + hybrid1Time.toFixed(2) + "s  ✅ BALANCED")
print("Full aggregation:          ~220s  ❌ TOO SLOW")
print("=".repeat(80))

print("\n💡 RECOMMENDATION:")
print("Use APPROACH 4 (Hybrid) for CA Analytics:")
print("- Quick sample to identify top CAs (~2-5s)")
print("- Precise counts for only top 10 CAs (~3-10s)")
print("- Total time: ~5-15s instead of 220s")
print("=".repeat(80) + "\n")