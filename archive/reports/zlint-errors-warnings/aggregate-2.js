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
      // safely extract the organization name (it's inside an array in your data)
      issuer: { $arrayElemAt: ["$parsed.issuer.organization", 0] }, 
      domain: 1
    }
  },
  {
    $group: {
      _id: "$issuer", 
      "Total Bad Certs": { $sum: 1 },
      "Example Domain": { $first: "$domain" }
    }
  },
  {
    $sort: { "Total Bad Certs": -1 }
  }
]