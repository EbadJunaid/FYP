[
  // STEP 1: De-duplicate (Group by Fingerprint)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      "san_list": { $first: "$parsed.extensions.subject_alt_name.dns_names" },
      "Found_On_Websites": { $push: "$domain" }
    }
  },

  // STEP 2: The Pro Scanner (Classify Domains)
  {
    $addFields: {
      // 🛡️ High Security List
      prod_domains: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "(www|prod|production|main|portal|secure|bank|gov|auth|login|api|pay|shop)", options: "i" } }
        }
      },
      // ☣️ Low Security List
      dev_domains: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "(dev|test|stage|staging|uat|qa|beta|demo|sandbox|preprod|internal|local|preview)", options: "i" } }
        }
      }
    }
  },

  // STEP 3: The Filter (Strict Violation Check)
  // Only keep certs that have BOTH High and Low security domains
  {
    $match: {
      $expr: {
        $and: [
          { $gt: [{ $size: "$prod_domains" }, 0] },
          { $gt: [{ $size: "$dev_domains" }, 0] }
        ]
      }
    }
  },

  // STEP 4: The "Other" List Calculation & Reporting
  {
    $project: {
      _id: 0,
      "Certificate Fingerprint": "$_id",
      "Violation": "CRITICAL: Mixed Production & Dev Environment",
      "Detected On": "$Found_On_Websites",
      
      // Full Lists (No Limits)
      "High_Security_Domains": "$prod_domains",
      "Low_Security_Domains": "$dev_domains",
      
      // Calculate "Other" = All SANs - (Prod + Dev)
      "Unclassified_Domains": {
        $setDifference: [
          "$san_list", 
          { $setUnion: ["$prod_domains", "$dev_domains"] }
        ]
      }
    }
  }
]