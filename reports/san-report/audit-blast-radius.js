[
  // 1. Group by Unique Certificate (De-duplicate)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      "san_list": { $first: "$parsed.extensions.subject_alt_name.dns_names" },
      // Collect the domains from YOUR dataset that use this file
      "my_websites": { $push: "$domain" }
    }
  },
  // 2. Calculate the Count
  {
    $addFields: {
      "count": { $size: { $ifNull: ["$san_list", []] } }
    }
  },
  // 3. FILTER: The "Sweet Spot" Rule (Only show if > 50)
  {
    $match: {
      "count": { $gt: 50 } 
    }
  },
  // 4. SORT: Biggest risks first
  {
    $sort: { "count": -1 }
  },
  // 5. FORMAT: Exactly as you requested
  {
    $project: {
      _id: 0,
      "Certificate Fingerprint(ID)": "$_id",
      "Total SANs count ": "$count",
      "Websites [our-dataset]": "$my_websites",
      "SAN Members lists": "$san_list"
    }
  }
]