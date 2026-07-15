[
  // 1. De-duplicate (One entry per file)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      "domain": { $first: "$domain" },
      "validity_start": { $first: "$parsed.validity.start" },
      "validity_end": { $first: "$parsed.validity.end" },
      "issuer": { $first: { $arrayElemAt: ["$parsed.issuer.organization", 0] } }
    }
  },
  
  // 2. Calculate Duration in Days
  {
    $addFields: {
      "validity_days": {
        $divide: [
          { $subtract: [ { $toDate: "$validity_end" }, { $toDate: "$validity_start" } ] },
          1000 * 60 * 60 * 24 // Convert ms to days
        ]
      }
    }
  },
  
  // 3. Categorize Risk (The "Switch" Statement)
  {
    $project: {
      _id: 0,
      "Domain": "$domain",
      "Issuer": "$issuer",
      "Validity Period (Days)": { $ceil: "$validity_days" },
      "Agility Status": {
        $switch: {
          branches: [
            // Automated / High Agility (Let's Encrypt style)
            { case: { $lte: ["$validity_days", 95] }, then: "🟢 Excellent (Automated/Agile)" },
            
            // Standard Commercial (1 Year)
            { case: { $lte: ["$validity_days", 397] }, then: "🟡 Standard (1 Year)" },
            
            // Non-Compliant (Apple/Google Ban)
            { case: { $gt: ["$validity_days", 398] }, then: "🔴 CRITICAL: Non-Compliant (>398 Days)" }
          ],
          default: "Unknown"
        }
      }
    }
  },
  
  // 4. Sort by Worst Offenders
  {
    $sort: { "Validity Period (Days)": -1 }
  }
]