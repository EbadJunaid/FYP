[
  // 1. Group by Unique Certificate (Fingerprint)
  {
    $group: {
      _id: "$parsed.fingerprint_sha256",
      
      // The SAN list (Content of the Cert) - We just need one copy
      "SAN_List": { $first: "$parsed.extensions.subject_alt_name.dns_names" },
      
      // NEW: Collect ALL the domains from your database that use this specific file
      "Found_On_Websites": { $push: "$domain" }
    }
  },
  // 2. Add a count so we can sort by the biggest "Blast Radius"
  {
    $addFields: {
      "SAN_Count": { $size: { $ifNull: ["$SAN_List", []] } }
    }
  },
  // 3. Sort (Biggest SAN lists first)
  {
    $sort: { "SAN_Count": -1 }
  },
  // 4. Formatting for readability
  {
    $project: {
      _id: 0,
      "Certificate Fingerprint(ID)": "$_id",
      "Total SANs count ": "$SAN_Count",
      "Websites [our-dataset]": "$Found_On_Websites", // <--- Your new list
      "SAN Members lists": "$SAN_List"
    }
  }
]