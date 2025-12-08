[
  {
    $match: {
      $or: [
        { "zlint.errors_present": true },
        { "zlint.warnings_present": true }
      ]
    }
  },
  {
    $project: {
      domain: 1,
      lints_array: { $objectToArray: "$zlint.lints" }
    }
  },
  {
    $addFields: {
      found_errors: {
        $filter: {
          input: "$lints_array",
          as: "item",
          cond: { $eq: ["$$item.v.result", "error"] }
        }
      },
      found_warnings: {
        $filter: {
          input: "$lints_array",
          as: "item",
          cond: { $eq: ["$$item.v.result", "warn"] }
        }
      }
    }
  },
  {
    $project: {
      _id: 0,
      Domain: "$domain",
      "Error Count": { $size: "$found_errors" },
      "Warning Count": { $size: "$found_warnings" },
      "Error Details": "$found_errors.k",
      "Warning Details": "$found_warnings.k"
    }
  }
]
