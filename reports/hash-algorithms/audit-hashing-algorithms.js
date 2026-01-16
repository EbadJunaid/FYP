[
  // 1. De-duplicate (One entry per unique file)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      "algorithm": { $first: "$parsed.signature_algorithm.name" },
      "oid": { $first: "$parsed.signature_algorithm.oid" },
      "domains_using_this": { $push: "$domain" } // Keep track of who is using it
    }
  },

  // 2. Classify the Algorithm (Weak vs. Strong)
  {
    $project: {
      _id: 0,
      "Certificate Fingerprint": "$_id",
      "Algorithm Name": "$algorithm",
      "Algorithm OID": "$oid",
      
      "Security Status": {
        $switch: {
          branches: [
            // ❌ CRITICAL: MD5 and SHA-1
            { 
              case: { $regexMatch: { input: "$algorithm", regex: "(md5|sha1|sha-1)", options: "i" } }, 
              then: "🔴 CRITICAL: Weak Hashing Algorithm" 
            },
            
            // ✅ SECURE: SHA-2 family (256, 384, 512)
            { 
              case: { $regexMatch: { input: "$algorithm", regex: "(sha256|sha-256|sha384|sha-384|sha512|sha-512)", options: "i" } }, 
              then: "🟢 Secure (Industry Standard)" 
            }
          ],
          // ⚠️ UNKNOWN: Anything else (like DSA or obscure algos)
          default: "🟡 Warning: Uncommon/Legacy Algorithm"
        }
      },
      
      "Impacted Domains": "$domains_using_this"
    }
  },

  // 3. Filter / Sort (Optional)
  // If you ONLY want to see the bad ones, uncomment the $match stage below.
  // Currently, it sorts "CRITICAL" to the top so you see them first.
  {
    $sort: { "Security Status": 1 } 
  }
  
  /* , {
    $match: { "Security Status": { $regex: "CRITICAL" } }
  }
  */
]