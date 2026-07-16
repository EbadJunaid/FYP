# CA Ranking — The Formula Explained

This document explains how Certificate Authorities (CAs) are scored and ranked in the dashboard. It is written for **everyone** — whether you are new to SSL/TLS certificates or an expert.

---

## What this formula does

We score every **leaf certificate** (the certificate a website actually uses) based on five aspects of quality and security. Then we **average** the scores of all certificates issued by the same CA. That average becomes the CA's trust score.

> **Leaf certificate** = the end-entity certificate installed on a web server (e.g., `www.example.com`), as opposed to intermediate or root CA certificates that are only used to sign other certificates.

Higher score = better certificate hygiene according to this formula.

---

## The five categories at a glance

| # | Category | What it measures | In simple words |
|---|----------|-----------------|----------------|
| 1 | **Core Hygiene** | ZLint test results | Does the certificate follow the rules? (lint = a tool that catches certificate mistakes) |
| 2 | **Crypto Health** | Key strength, uniqueness, algorithm choice | Is the encryption solid and the key not reused elsewhere? |
| 3 | **Operational Stability** | CA diversity, temporal patterns, issuer consistency | Does the certificate behave consistently over time? |
| 4 | **Policy Compliance** | Extended Key Usage, certificate policies, validation level, name constraints | Does the certificate follow industry-standard policies? |
| 5 | **Risk Factors** | Issuer country risk, revocation support | Are there contextual warning signs? |

Each category produces a score between **0 and 1**, and the final certificate score is the **average of all five categories × 100** (so the final score is between **0 and 100**).

---

## The formula

```
core_hygiene          = mean(ZCS, ZHFS)
crypto_health         = mean(KHS, KUS, WKLP)
operational_stability = mean(CADS, TSI, IOPS)
policy_compliance     = mean(EKUVS, PICS, DVAS, NCVS)
risk_factors          = mean(GNS, ACCS, REVPS)

final_score           = mean(
                          core_hygiene,
                          crypto_health,
                          operational_stability,
                          policy_compliance,
                          risk_factors
                        ) × 100
```

Then for a CA:

```
CA_score = average(final_score of every leaf certificate issued by that CA)
```

---

## Component-by-component breakdown

### Constants used everywhere

| Constant | Value | What it means |
|----------|-------|---------------|
| `W_ERR` | 2.0 | Weight applied to a ZLint **error** result |
| `W_WARN` | 1.0 | Weight applied to a ZLint **warning** result |
| `MAX_VALIDITY_DAYS` | 825 | Maximum "good" validity period in days (beyond this is penalized) |
| `T_MAX` | 730 | Used to normalize timestamp variation in TSI |
| `INCLUDE_ACCS` | False | AIA CA issuer scoring is disabled (neutral) |

---

### Category 1: Core Hygiene

Measures whether the certificate passes ZLint — an automated linter that checks certificates against RFC standards.

Two sub-scores:

**ZCS (ZLint Compliance Score)** — non-critical issues only
1. Go through every ZLint result that is **not** in the critical list.
2. Add penalties: 2 points for each `error`, 1 point for each `warn`.
3. Compare the total penalty against the **95th percentile** of all penalties in the current dataset.
4. `ZCS = 1 - (your_penalty / P95)`, clipped to minimum 0.

This tells us: "how many non-critical lint mistakes does this certificate have, compared to the worst 5% of certificates out there?"

**ZHFS (ZLint Hygiene for Critical)** — critical issues only
1. Look at the 22 pre-defined **critical** lint IDs (these are serious security-impactful rules).
2. Count how many of them have an `error` result.
3. `ZHFS = 1 - (critical_error_count / 22)`

This tells us: "what fraction of serious lint rules did this certificate pass?"

---

### Category 2: Crypto Health

Measures the quality of the cryptographic key material.

**KHS (Key Health Score)**
- Is the key at least 2048 bits (for RSA) or equivalent (for ECDSA)? → 1 point
- Is the algorithm RSA or ECDSA (not something obsolete)? → 1 point
- Is the validity period short (under 825 days)? → score = `1 - (validity_days / 825)`, capped at 1
- `KHS = (bits_ok + algo_ok + age_score) / 3`

> **ECDSA** = Elliptic Curve Digital Signature Algorithm, a modern alternative to RSA.

**KUS (Key Uniqueness Score)**
- Is this public key **new** (never seen before in this dataset)? → 1 point
- Is this key **reused** from another certificate? → 0 points
- Is the key fingerprint missing? → 0.5 (neutral)

**WKLP (Weak Key Penalty)**
- Is the key smaller than 2048 bits? → 1 (marked as weak)
- Otherwise → 0

---

### Category 3: Operational Stability

Measures how consistent the certificate's operational patterns are.

**CADS (CA Diversity Score)**
- Look at the issuer names in the dataset.
- Compute the **entropy** (a measure of diversity) of issuer distribution.
- `CADS = min(1, entropy / log2(number_of_unique_issuers))`
- If only one issuer: CADS = 0.

> **Entropy** = a measure of variety. High entropy means many different CAs are used. Low entropy means the ecosystem is dominated by one CA.

**TSI (Temporal Stability Score)**
- Look at the `valid_from` timestamps of certificates.
- Compute the **standard deviation** of those timestamps.
- `TSI = max(0, 1 - std_dev / (730 × 24 × 3600 seconds))`
- If fewer than 2 timestamps are available: TSI = 0.5 (neutral).

> **Standard deviation** = a measure of how spread out the dates are. Small spread → stable issuance pattern. Large spread → erratic.

**IOPS (Issuer Operational Pattern Score)**
- Look at the sequence of issuer names, sorted by time.
- Count how often the same issuer appears consecutively.
- `IOPS = 1 - (same_adjacent_count / (total - 1))`
- If only 1 entry: IOPS = 1 (no penalty).

---

### Category 4: Policy Compliance

Measures whether the certificate follows standard policies and validation practices.

**EKUVS (Extended Key Usage Validation Score)**
- Look at the Extended Key Usage (EKU) extension — it says what the certificate is allowed to be used for.
- If no EKU: 0 points.
- If it has `server_auth` or `client_auth`:
  - ≤ 2 usages total → 1 point (focused, good)
  - > 2 usages → 0.5 points (too broad)
- Otherwise: 0 points.

**PICS (Policy Identifier Compliance Score)**
- Look at the Certificate Policies extension — it contains OIDs (object identifiers).
- Does it contain a known validation-level OID?
  - `2.23.140.1.2.1` → Domain Validation (DV)
  - `2.23.140.1.2.2` → Organization Validation (OV)
  - `2.23.140.1.1` → Extended Validation (EV)
- If yes → 1, otherwise → 0.

> **OID** = Object Identifier, a numeric string that uniquely identifies a policy or standard.

**DVAS (Domain Validation Assurance Score)**
- What is the certificate's **validation level**?
  - EV (Extended Validation, highest) → 1
  - OV (Organization Validation) → 0.75
  - DV (Domain Validation, basic) → 0.5
  - Unknown → 0

**NCVS (Name Constraints Presence Score)**
- Does the certificate have a **Name Constraints** extension (which restricts which domains the cert can be used for)?
- If yes → 1, otherwise → 0.

---

### Category 5: Risk Factors

Measures contextual risk signals that are not captured by the other categories.

**GNS (Geography Risk Score)**
- What is the issuer's country?
- Risky countries: `IR` (Iran), `KP` (North Korea), `SY` (Syria), `CU` (Cuba), `RU` (Russia)
- If the country is in this list → 0, otherwise → 1.

**ACCS (AIA CA Issuers Score)**
- This component is **disabled** (INCLUDE_ACCS = False).
- Always returns 0.5 (neutral).

**REVPS (Revocation Presence Score)**
- Does the certificate provide:
  - Both OCSP (online checking) and CRL (certificate revocation list) endpoints → 1
  - Only one of the two → 0.5
  - Neither → 0

> **OCSP** = Online Certificate Status Protocol, a way to check if a certificate is revoked in real-time.
> **CRL** = Certificate Revocation List, a periodically published list of revoked certificates.

---

## Example walkthrough

Let's score a single certificate step by step.

```
Certificate from "Example Trust CA"
ZLint: 1 non-critical error, 0 warnings, 0 critical errors
Key: 2048-bit RSA, unique fingerprint
Validity: 365 days
EKU: server_auth only
Policies: contains DV OID (2.23.140.1.2.1)
Validation: DV
Name constraints: absent
Issuer country: US
OCSP: present, CRL: present

Dataset P95 for ZLint penalty: 3.0
```

**Step 1 — Core Hygiene**
- ZCS: penalty = 2 (one error), P95 = 3 → ZCS = 1 - min(2,3)/3 = 0.333
- ZHFS: 0 critical errors / 22 → ZHFS = 1 - 0/22 = 1.0
- core_hygiene = mean(0.333, 1.0) = **0.667**

**Step 2 — Crypto Health**
- KHS: bits_ok=1, algo_ok=1, age_score=1-365/825=0.558 → KHS = (1+1+0.558)/3 = **0.853**
- KUS: first time seeing this key → **1.0**
- WKLP: 2048 is not < 2048 → **0**
- crypto_health = mean(0.853, 1.0, 0) = **0.618**

**Step 3 — Operational Stability**
- CADS: only one issuer → **0.0**
- TSI: only one timestamp → **0.5**
- IOPS: only one entry → **1.0**
- operational_stability = mean(0.0, 0.5, 1.0) = **0.5**

**Step 4 — Policy Compliance**
- EKUVS: server_auth only, len(eku) ≤ 2 → **1.0**
- PICS: has DV OID → **1.0**
- DVAS: DV → **0.5**
- NCVS: no name constraints → **0.0**
- policy_compliance = mean(1.0, 1.0, 0.5, 0.0) = **0.625**

**Step 5 — Risk Factors**
- GNS: US is not risky → **1.0**
- ACCS: disabled → **0.5**
- REVPS: has both OCSP and CRL → **1.0**
- risk_factors = mean(1.0, 0.5, 1.0) = **0.833**

**Step 6 — Final Score**
```
final_score = mean(0.667, 0.618, 0.5, 0.625, 0.833) × 100
            = 0.649 × 100
            = 64.9
```

**Step 7 — CA Score**
If Example Trust CA has 10,000 certificates with an average score of 64.9, its CA score = **64.9**.

---

## What is NOT measured

This formula does **not** measure:
- Whether a CA has been hacked or compromised
- The probability of a future attack
- The CA's market share or popularity (that is shown separately as `rank`)
- Browser trust store inclusion status

It is a **comparative quality score** based on observable properties in the certificate itself.

---

## Glossary

| Term | Explanation |
|------|-------------|
| **Leaf certificate** | The final certificate in a chain, issued to a real domain (e.g., `www.example.com`) |
| **ZLint** | A tool that checks certificates against RFC standards, reporting `error`, `warn`, or `pass` for each rule |
| **CRITICAL_LINTS** | A curated set of 22 ZLint rules that are considered security-critical |
| **Entropy** | A measure of diversity or randomness; higher = more variety |
| **Standard deviation** | How spread out a set of numbers is; lower = more consistent |
| **OID** | Object Identifier, a globally unique numeric code for policies, algorithms, etc. |
| **EKU** | Extended Key Usage — what a certificate is allowed to be used for |
| **OCSP** | Real-time certificate revocation checking protocol |
| **CRL** | Certificate Revocation List — a periodically published list of revoked certificates |
| **P95 / 95th percentile** | A value below which 95% of observations fall; used here to normalize penalties |
| **RSA / ECDSA** | Two common public-key cryptographic algorithms |
| **DV / OV / EV** | Validation levels: Domain (basic), Organization (moderate), Extended (highest) |
