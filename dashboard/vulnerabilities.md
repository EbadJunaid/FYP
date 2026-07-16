# Vulnerabilities Page

This page ranks risky certificates using fast certificate fields and the precomputed shared-key results. SAN count is intentionally not used here because it made the vulnerabilities flow slow and belongs to SAN analytics.

## Risk Formula

Each certificate starts with a score of **0**. Risk-increasing factors add points; risk-reducing factors subtract them. The final score is clamped between **0 and 100**.

### Risk-increasing factors

| Factor | Points | Condition |
|---|---|---|
| Expired certificate | +30 | `validity.end` is in the past |
| Shared public key | +30 | Key SHA-256 fingerprint matches another certificate in the dataset |
| Weak encryption | +20 | RSA key length < 2048 bits |
| Long validity | +10 | Validity > 398 days (CA/Browser Forum limit) |
| ZLint issues | Up to +10 | Errors and warnings from ZLint linting |

### ZLint scoring

Each ZLint error = **1 point**. Warnings contribute **1 point per two warnings (rounded up)** — so 1 warning = 1 point, 2 warnings = 1 point, 3 warnings = 2 points, etc. The combined error + warning score is capped at **10**.

### Risk-reducing factors

| Factor | Points | Condition |
|---|---|---|
| Currently valid certificate | -5 | `validity.end` is in the future |
| Strong key | -5 | RSA ≥ 2048 bits or ECDSA/EC key |
| Modern validity | -5 | Validity ≤ 398 days |
| No ZLint errors or warnings | -5 | ZLint check passed cleanly |

### Risk levels

| Level | Score range |
|---|---|
| Critical | ≥ 85 |
| High | 70 – 84 |
| Medium | 40 – 69 |
| Low | 1 – 39 |

Scores of 0 are not returned — a certificate must have at least one risk factor to appear.

### Worked example

Take an expired certificate with a 1024-bit RSA key, shared key fingerprint, validity of 500 days, and 3 ZLint errors + 2 warnings:

| Factor | Points | Running score |
|---|---|---|
| Expired | +30 | 30 |
| Shared public key | +30 | 60 |
| Weak encryption (RSA 1024) | +20 | 80 |
| Long validity (500 days) | +10 | 90 |
| ZLint: 3 errors + 2 warnings = 3 + ceil(2/2) = 4 | +4 | 94 |
| Score clamped to 0–100 | — | **94 (Critical)** |

### What the score does NOT mean

- A high score does **not** mean the certificate is compromised or actively exploited. It means the certificate has many observable risk flags.
- A low score does **not** mean the certificate is fully trustworthy. It means fewer risk flags were detected in the automated checks.
- The score is a **ranking signal** for triage, not a security audit verdict.

## What Clicking Does

### Top summary cards

- **Critical Risk**, **High Risk**, and **Medium Risk** call `/api/overview/vulnerabilities/` with the selected `risk_level` and request enough rows to show that full risk level in the table.
- **Total Risky** calls `/api/overview/vulnerabilities/` without a risk level, showing the complete ranked list with pagination.

### Filter chips

Filter chips call `/shared/certificates/` with `risk_filter` and pass risk-specific filtering directly to the database:

| Chip | `risk_filter` value | What it shows |
|---|---|---|
| Ranked Risk | _(none — uses `risk_level`)_ | Computed ranked list from vulnerabilities endpoint |
| Expired | `expired` | Expired certificates (other risk factors still shown per row) |
| Shared Keys | `shared-key` | Certificates that reuse a public key |
| Weak Encryption | `weak-encryption` | RSA certificates below 2048 bits |
| Long Validity | `long-validity` | Certificates valid > 398 days |
| ZLint Issues | `zlint` | Certificates with ZLint errors or warnings |

### Rows

- Clicking the arrow expands the row.
- The expanded area shows shared-key information, expiration, issuer, validation level, and sample domains from the shared-key group (when available).
- Clicking the domain or **View Full Certificate Details** opens the full certificate details page.
- The current scope is appended by the frontend API client, so the same page works for global, Pakistan, India, or any other configured scope.

## Glossary

| Term | Meaning |
|---|---|
| **RSA key length** | Number of bits in the RSA modulus. 2048+ is the modern minimum; below 2048 is considered weak. |
| **ZLint** | An open-source certificate linter that checks X.509 certificates against CA/Browser Forum baseline requirements. |
| **Shared public key** | Two or more certificates using the exact same RSA/ECDSA public key, which may indicate key reuse or misissuance. |
| **398 days** | The CA/Browser Forum maximum allowed certificate validity (Ballot SC-31). |
| **OCSP/CRL** | Online Certificate Status Protocol / Certificate Revocation List — revocation-checking mechanisms. |
| **Clamping** | Limiting a value to a range. Here scores below 0 are rounded up to 0, and scores above 100 are rounded down to 100. |
