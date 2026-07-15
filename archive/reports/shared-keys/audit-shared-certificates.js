[
  // 1. Group by the Key Fingerprint (The "Shared Secret")
  {
    $group: {
      _id: "$parsed.spki_subject_fingerprint",
      
      // Collect ALL Serial Numbers found for this key
      "all_serials": { $addToSet: "$parsed.serial_number" },
      
      // Just for context, grab the domain names
      "domains": { $addToSet: "$domain" }
    }
  },
  
  // 2. Count the Unique Serial Numbers
  {
    $addFields: {
      "unique_file_count": { $size: "$all_serials" }
    }
  },
  
  // 3. THE LOGIC: If count > 1, it means Key Reuse exists.
  {
    $match: {
      "unique_file_count": { $gt: 1 }
    }
  },
  
  // 4. Output
  {
    $project: {
      _id: 0,
      "Key Fingerprint": "$_id",
      "Files Using This Key": "$unique_file_count",
      "Domains Involved": "$domains"
    }
  }
]


// there is no shared certificates found in our dataset 