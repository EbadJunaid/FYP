[
  {
    $addFields: {
      // Convert the string date to a real Date object for math
      expiryDateObj: { $toDate: "$parsed.validity.end" }
    }
  },
  {
    $addFields: {
      // Calculate milliseconds difference, then convert to days
      daysLeft: {
        $divide: [
          { $subtract: ["$expiryDateObj", "$$NOW"] },
          1000 * 60 * 60 * 24
        ]
      }
    }
  },
  {
    $match: {
      // LOGIC: Greater than 0 (not expired yet) AND Less/Equal to 30
      daysLeft: { $gt: 0, $lte: 30 }
    }
  },
  {
    $project: {
      _id: 0,
      Domain: "$domain",
      "Common Name": { $arrayElemAt: ["$parsed.subject.common_name", 0] },
      "Validation Level": "$parsed.validation_level",
      "Expiration Date": "$parsed.validity.end",
      "Days Left": { $ceil: "$daysLeft" } // Round up (e.g., 0.5 days = 1 day left)
    }
  },
  {
    $sort: { "Days Left": 1 } // Show most urgent first
  }
]