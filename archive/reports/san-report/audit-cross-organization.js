[
  // STEP 1: De-duplicate (Group by Fingerprint)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      "san_list": { $first: "$parsed.extensions.subject_alt_name.dns_names" },
      "Found_On_Websites": { $push: "$domain" }
    }
  },

  // STEP 2: The Tier Scanner (Classify EVERYTHING)
  {
    $addFields: {
      // Tier 1: Military (Critical Defense)
      tier_1_mil: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "\\.mil\\.pk$", options: "i" } }
        }
      },
      // Tier 2: Civil Government (Sovereign)
      tier_2_gov: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "(\\.gov\\.pk|\\.gop\\.pk|\\.gos\\.pk|\\.gkp\\.pk|\\.gob\\.pk|\\.gqk\\.pk)$", options: "i" } }
        }
      },
      // Tier 3: Education (Variable Trust)
      tier_3_edu: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "\\.edu\\.pk$", options: "i" } }
        }
      },
      // Tier 4: Public/Commercial (Untrusted)
      tier_4_com: {
        $filter: {
          input: "$san_list",
          as: "d",
          cond: { $regexMatch: { input: "$$d", regex: "(\\.com\\.pk|\\.net\\.pk|\\.org\\.pk|\\.biz\\.pk|\\.web\\.pk|\\.fam\\.pk)$", options: "i" } }
        }
      }
    }
  },

  // STEP 3: The Violation Filter (Check for ANY Mixing)
  {
    $addFields: {
      // Create simple boolean flags (1 = Exists, 0 = Empty)
      has_mil: { $cond: [{ $gt: [{ $size: "$tier_1_mil" }, 0] }, 1, 0] },
      has_gov: { $cond: [{ $gt: [{ $size: "$tier_2_gov" }, 0] }, 1, 0] },
      has_edu: { $cond: [{ $gt: [{ $size: "$tier_3_edu" }, 0] }, 1, 0] },
      has_com: { $cond: [{ $gt: [{ $size: "$tier_4_com" }, 0] }, 1, 0] }
    }
  },
  {
    $addFields: {
      // Sum the types found. If > 1, they are mixing tiers.
      distinct_tiers_found: { $add: ["$has_mil", "$has_gov", "$has_edu", "$has_com"] }
    }
  },
  {
    $match: {
      // KEEP ONLY if they mix 2 or more tiers
      distinct_tiers_found: { $gt: 1 }
    }
  },

  // STEP 4: The Report (Categorize the Severity)
  {
    $project: {
      _id: 0,
      "Certificate Fingerprint": "$_id",
      
      // Dynamic Severity Label
      "Risk Severity": {
        $switch: {
          branches: [
            // If Military is involved with ANYONE else -> CRITICAL
            { case: { $eq: ["$has_mil", 1] }, then: "CRITICAL: Military Domain Leaked" },
            // If Gov mixed with Com/Edu -> HIGH
            { case: { $and: [{ $eq: ["$has_gov", 1] }, { $eq: ["$has_com", 1] }] }, then: "HIGH: Government mixed with Commercial" },
            { case: { $and: [{ $eq: ["$has_gov", 1] }, { $eq: ["$has_edu", 1] }] }, then: "HIGH: Government mixed with Education" }
          ],
          default: "MEDIUM: Education/Commercial Mix"
        }
      },
      
      "Detected On": "$Found_On_Websites",
      "Military_Domains": "$tier_1_mil",
      "Government_Domains": "$tier_2_gov",
      "Education_Domains": "$tier_3_edu",
      "Commercial_Domains": "$tier_4_com"
    }
  },
  // Put the worst violations at the top
  {
    $sort: { "Risk Severity": 1 } 
  }
]