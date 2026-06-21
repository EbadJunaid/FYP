# Vulnerabilities Page

This page ranks risky certificates using fast certificate fields and the precomputed shared-key results. SAN count is intentionally not used in this page because it made the vulnerabilities flow slow and belongs to SAN analytics.       

## Risk Formula

Each certificate starts with a score of 0. The final score is clamped between 0 and 100.

Risk additions:

- Expired certificate: 30
- Shared public key: 30
- Weak encryption: 20 when RSA key length is below 2048 bits
- Long validity period: 10 when validity is more than 398 days
- ZLint issues: up to 10 total

ZLint scoring:

- Each ZLint error adds 1 point.
- Every two ZLint warnings add 1 point.
- The ZLint score is capped at 10, so 10 errors gives the full 10 points.

Positive signals subtract small amounts:

- Currently valid certificate: -5
- Strong key: -10
- Modern validity period of 398 days or less: -5
- No ZLint errors or warnings: -5

Risk levels:

- Critical: score >= 85
- High: score >= 70
- Medium: score >= 40
- Low: score > 0

## What Clicking Does

Top summary cards:

- Critical Risk, High Risk, and Medium Risk call `/api/overview/vulnerablities/` with the selected `risk_level` and request enough rows to show that full risk level in the table.
- Total Risky calls `/api/overview/vulnerablities/` without a risk level, so it shows the complete ranked risky list with pagination.

Filter chips:

- Ranked Risk shows the computed ranked list from `/api/overview/vulnerablities/`.
- Expired uses `risk_filter=expired` and shows expired certificates. If an expired certificate also has shared keys, weak encryption, long validity, or ZLint issues, those factors still appear in the row score.
- Shared Keys uses `risk_filter=shared-key` and shows certificates that reuse a public key. Any additional risk factors still appear in the row score.
- Weak Encryption uses `risk_filter=weak-encryption` and shows RSA certificates below 2048 bits. Any additional risk factors still appear in the row score.
- Long Validity uses `risk_filter=long-validity` and shows certificates valid for more than 398 days. Any additional risk factors still appear in the row score.
- ZLint Issues uses `risk_filter=zlint` and shows certificates with ZLint errors or warnings. Any additional risk factors still appear in the row score.

Rows:

- Clicking the arrow expands the row.
- The expanded area shows shared key information, expiration, issuer, validation level, and sample domains from the shared-key group when available.
- Clicking the domain or View Full Certificate Details opens the full certificate details page, which loads the certificate through the shared certificate detail API.

The current scope is appended by the frontend API client, so the same page works for global, Pakistan, India, or any other configured scope.
