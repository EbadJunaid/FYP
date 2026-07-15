[
  {
    $addFields: {
      expiryDateObj: { $toDate: "$parsed.validity.end" }
    }
  },
  {
    $addFields: {
      // Calculate difference (this will be negative for expired certs)
      daysDiff: {
        $divide: [
          { $subtract: ["$expiryDateObj", "$$NOW"] },
          1000 * 60 * 60 * 24
        ]
      }
    }
  },
  {
    $match: {
      // LOGIC: Negative days means it is already in the past
      daysDiff: { $lte: 0 }
    }
  },
  {
    $project: {
      _id: 0,
      Domain: "$domain",
      "Common Name": { $arrayElemAt: ["$parsed.subject.common_name", 0] },
      "Validation Level": "$parsed.validation_level",
      "Expiration Date": "$parsed.validity.end",
      // Convert negative number to positive "Days Gone"
      "Days Gone": { $ceil: { $abs: "$daysDiff" } } 
    }
  },
  {
    $sort: { "Days Gone": 1 } // Show recently expired first
  }
]