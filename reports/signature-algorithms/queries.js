// Extract those domains where algorithm used is RSA and its length is 2048. choose 3072,4096 for others

[
  {
    $match: {
      "parsed.subject_key_info.key_algorithm.name": "RSA",
      "parsed.subject_key_info.rsa_public_key.length": 2048
    }
  },
  {
    $project: {
      _id: 0,
      domain: 1
    }
  }
]

// fetch all the domains with ecdsa-p-384.chose 256 and any other

[
  {
    $match: {
      "parsed.subject_key_info.key_algorithm.name": "ECDSA",
      "parsed.subject_key_info.ecdsa_public_key.curve": "P-384"
    }
  },
  {
    $project: {
      _id: 0,
      domain: 1
    }
  }
]
// fetch the unique curves and length present in ecdsa

[
  {
    $match: {
      "parsed.subject_key_info.key_algorithm.name": "ECDSA"
    }
  },
  {
    $group: {
      _id: {
        curve: "$parsed.subject_key_info.ecdsa_public_key.curve",
      }
    }
  },
  {
    $project: {
      _id: 0,
      curve: "$_id.curve",
    }
  }
]


