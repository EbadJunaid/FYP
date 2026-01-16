# Signature and Hashes Page Specification

## Overview

The **Signature and Hashes** page (`/dashboard/signature-hashes`) provides comprehensive analysis of cryptographic signatures and hash algorithms used across SSL certificates. This page helps administrators assess cryptographic strength, identify deprecated algorithms, and ensure compliance with modern security standards.

---

## Page Layout

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  [Header with Search, Filter, Notifications]                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │
│  │ Signature    │ │ Hash Func   │ │ Weak Hash   │ │ Signature    │       │
│  │ Algorithm    │ │ Compliance  │ │ Alert       │ │ Strength     │       │
│  │ Distribution │ │ Rate        │ │ Count       │ │ Score        │       │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │
│                                                                             │
│  ┌──────────────┐ ┌──────────────┐                                         │
│  │ Key Size    │ │ Self-Signed │                                          │
│  │ Distribution │ │ Certificates│                                          │
│  └──────────────┘ └──────────────┘                                         │
│                                                                             │
│  ┌────────────────────────────────┐ ┌────────────────────────────────┐     │
│  │ Signature Algorithm           │ │ Hash Algorithm Usage           │     │
│  │ Distribution (Pie Chart)      │ │ (Bar Chart)                    │     │
│  └────────────────────────────────┘ └────────────────────────────────┘     │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Hash Algorithm Adoption Over Time (Line Chart)                      │   │
│  │  [Show by Issuance Date] [Group by Quarter/Year]                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Signature Strength Heatmap by Issuer                                │   │
│  │  Shows key size + hash algorithm combinations per CA                 │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Certificates Table                                                   │   │
│  │  [Filter: Algorithm | Hash | Key Size | Strength Score]             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Cards (Metric Tiles) — 6 Total

### Card 1: Signature Algorithm Distribution
- **Value**: Dominant algorithm percentage (e.g., "RSA: 92.3%")
- **Secondary**: Second most used (e.g., "ECDSA: 7.7%")
- **Icon**: Key with signature icon
- **Color**: Blue (primary)
- **Info Tooltip**: "Distribution of signature algorithms across all certificates"
- **Click Action**: Opens breakdown modal showing full algorithm distribution, then click any algorithm filters table
- **API**: Aggregation on `parsed.signature_algorithm.name`

### Card 2: Hash Function Compliance Rate
- **Value**: Percentage using SHA-256 or stronger (e.g., "98.5%")
- **Icon**: Shield with checkmark
- **Color**: Green if ≥ 95%, Orange if 80-95%, Red if < 80%
- **Info Tooltip**: "Percentage of certificates using SHA-256 or stronger hash algorithms (SHA-384, SHA-512)"
- **Click Action**: Filter table to show only compliant/non-compliant certificates
- **Badge**: "SECURE" if ≥ 99%
- **API**: Count documents where hash algorithm is in ['SHA-256', 'SHA-384', 'SHA-512']

### Card 3: Weak Hash Alert
- **Value**: Count of certificates using deprecated hashes (MD5, SHA-1)
- **Icon**: Warning triangle
- **Color**: Red if count > 0, Green if 0
- **Info Tooltip**: "Certificates using deprecated hash algorithms (MD5, SHA-1) that are vulnerable to collision attacks"
- **Click Action**: Filter table to show only weak hash certificates
- **Badge**: "CRITICAL" if count > 10
- **API**: Count where `parsed.signature_algorithm.name` contains 'MD5' or 'SHA1'

### Card 4: Signature Strength Score
- **Value**: Overall score out of 100 (e.g., "94/100")
- **Icon**: Gauge meter
- **Color**: Green if ≥ 80, Orange if 60-80, Red if < 60
- **Info Tooltip**: "Composite score based on key sizes, hash algorithms, and signature types used across all certificates"
- **Click Action**: Opens modal explaining score breakdown (key size contribution, hash contribution, algorithm type)
- **Calculation**:
  ```
  Score = (KeySizeScore * 0.4) + (HashScore * 0.4) + (AlgorithmScore * 0.2)
  
  KeySizeScore: 4096+ bits = 100, 2048 = 80, 1024 = 40, < 1024 = 0
  HashScore: SHA-512 = 100, SHA-384 = 95, SHA-256 = 90, SHA-1 = 30, MD5 = 0
  AlgorithmScore: ECDSA = 100, RSA = 85, DSA = 60
  ```

### Card 5: Key Size Distribution
- **Value**: Dominant key size (e.g., "2048-bit: 78%")
- **Secondary**: "4096-bit: 15%"
- **Icon**: Key length icon
- **Color**: Blue
- **Info Tooltip**: "Distribution of public key sizes (RSA bit length or ECDSA curve size)"
- **Click Action**: Filter table by selected key size
- **API**: Aggregation on `parsed.subject_key_info.rsa_public_key.length`

### Card 6: Self-Signed Certificates
- **Value**: Count and percentage of self-signed certificates
- **Icon**: Circular arrow
- **Color**: Yellow (warning) if > 5%, Green otherwise
- **Info Tooltip**: "Certificates that are self-signed (issuer = subject), which may indicate test/dev environments or misconfigurations"
- **Click Action**: Filter table to show only self-signed certificates
- **API**: Count where `parsed.signature.self_signed == true`

---

## Graphs and Trends

### 1. Signature Algorithm Distribution (Pie/Donut Chart)

**Purpose**: Visual breakdown of signature algorithms used across all certificates.

**Segments**:
- **SHA256-RSA** (blue): Most common modern algorithm
- **SHA384-RSA** (light blue): Higher security RSA
- **SHA512-RSA** (dark blue): Maximum RSA security
- **SHA256-ECDSA** (green): Modern elliptic curve
- **SHA384-ECDSA** (light green): High-security EC
- **SHA1-RSA** (orange): Deprecated - highlight with warning
- **MD5-RSA** (red): Deprecated - critical warning
- **Other** (gray): DSA, etc.

**Center Value**: Total certificate count

**API**:
```python
def get_signature_algorithm_distribution():
    pipeline = [
        {'$group': {
            '_id': '$parsed.signature_algorithm.name',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
    return list(CertificateModel.collection.aggregate(pipeline))
```

**Clickable**: Each segment filters the table to show certificates with that algorithm

---

### 2. Hash Algorithm Usage (Horizontal Bar Chart)

**Purpose**: Compare usage of different hash functions with security ratings.

**Bars** (sorted by count):
```
SHA-256    ████████████████████████████████  45,678 (92.3%) ✓ SECURE
SHA-384    ████                                 2,345 (4.7%)  ✓ SECURE
SHA-512    ██                                     890 (1.8%)  ✓ SECURE
SHA-1      █                                      456 (0.9%)  ⚠ DEPRECATED
MD5                                                78 (0.2%)  ✗ CRITICAL
```

**Color Coding**:
- Green bars with checkmark: Secure algorithms
- Orange bars with warning: Deprecated but not critical
- Red bars with X: Critical vulnerabilities

**API**:
```python
def get_hash_algorithm_usage():
    # Extract hash from signature_algorithm.name (e.g., "SHA256-RSA" -> "SHA-256")
    pipeline = [
        {'$project': {
            'hash': {
                '$switch': {
                    'branches': [
                        {'case': {'$regexMatch': {'input': '$parsed.signature_algorithm.name', 'regex': 'SHA512'}}, 'then': 'SHA-512'},
                        {'case': {'$regexMatch': {'input': '$parsed.signature_algorithm.name', 'regex': 'SHA384'}}, 'then': 'SHA-384'},
                        {'case': {'$regexMatch': {'input': '$parsed.signature_algorithm.name', 'regex': 'SHA256'}}, 'then': 'SHA-256'},
                        {'case': {'$regexMatch': {'input': '$parsed.signature_algorithm.name', 'regex': 'SHA1'}}, 'then': 'SHA-1'},
                        {'case': {'$regexMatch': {'input': '$parsed.signature_algorithm.name', 'regex': 'MD5'}}, 'then': 'MD5'},
                    ],
                    'default': 'Other'
                }
            }
        }},
        {'$group': {'_id': '$hash', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]
```

---

### 3. Hash Algorithm Adoption Over Time (Line Chart)

**Purpose**: Show trends in hash algorithm usage based on certificate issuance dates.

**Lines** (multi-series):
- **SHA-256** (solid blue): Primary tracking
- **SHA-1** (dashed orange): Deprecation trend
- **SHA-384/512** (dotted green): Adoption of stronger hashes

**X-Axis**: Quarters or Years (based on `parsed.validity.start`)
**Y-Axis**: Percentage of certificates issued in that period

**Key Insights**:
- SHA-1 should show declining trend (deprecated since 2017)
- SHA-256 should dominate from 2017 onwards
- SHA-384/512 may show growth in recent periods

**API**:
```python
def get_hash_adoption_trends(granularity='quarterly', months=36):
    # Group by issuance date quarter and hash algorithm
    pipeline = [
        {'$match': {'parsed.validity.start': {'$gte': start_date_str}}},
        {'$project': {
            'hash': '...',  # Extract hash as above
            'issuedDate': {'$dateFromString': {'dateString': '$parsed.validity.start'}}
        }},
        {'$group': {
            '_id': {
                'year': {'$year': '$issuedDate'},
                'quarter': {'$ceil': {'$divide': [{'$month': '$issuedDate'}, 3]}},
                'hash': '$hash'
            },
            'count': {'$sum': 1}
        }},
        {'$sort': {'_id.year': 1, '_id.quarter': 1}}
    ]
```

**Clickable**: Click any data point to filter table by that period and hash algorithm

---

### 4. Signature Strength Heatmap by Issuer (Heatmap/Grid)

**Purpose**: Show which Certificate Authorities use which algorithm/key size combinations.

**Grid Structure**:
```
                    | RSA-2048 | RSA-4096 | ECDSA-256 | ECDSA-384 |
--------------------|----------|----------|-----------|-----------|
Let's Encrypt       |    ████  |          |     ██    |           |
DigiCert            |    ██    |    ███   |     █     |     █     |
Sectigo             |    ███   |    █     |           |           |
GlobalSign          |    ██    |    ██    |     ██    |     █     |
```

**Color Intensity**: Based on certificate count for that combination
**Hover**: Shows exact count and percentage

**API**:
```python
def get_issuer_algorithm_heatmap():
    pipeline = [
        {'$group': {
            '_id': {
                'issuer': {'$arrayElemAt': ['$parsed.issuer.organization', 0]},
                'algorithm': '$parsed.subject_key_info.key_algorithm.name',
                'keySize': '$parsed.subject_key_info.rsa_public_key.length'
            },
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}}
    ]
```

**Clickable**: Click any cell to filter table by issuer + algorithm combination

---

### 5. Key Size Trend Over Time (Optional Area Chart)

**Purpose**: Track adoption of larger key sizes over time.

**Areas** (stacked):
- 4096+ bits (dark blue): Growing trend
- 2048 bits (blue): Current standard
- 1024 bits (orange): Legacy/deprecated
- < 1024 bits (red): Critical - should be zero

---

## Interactive Click Behaviors

### Card Click Actions

| Card | Click Action | Table Filter Applied |
|------|--------------|---------------------|
| Signature Algorithm | Opens modal with distribution breakdown | `signature_algorithm=<selected>` |
| Hash Compliance | Toggles compliant/non-compliant view | `hash_compliant=true/false` |
| Weak Hash Alert | Filters to weak hashes only | `weak_hash=true` |
| Signature Strength | Opens score breakdown modal | Sort by computed score |
| Key Size | Opens key size breakdown | `key_size=<selected>` |
| Self-Signed | Filters self-signed certificates | `self_signed=true` |

### Chart Click Actions

| Chart | Click Target | Action |
|-------|--------------|--------|
| Pie Chart | Segment | Filter table: `signature_algorithm=<segment>` |
| Bar Chart | Bar | Filter table: `hash_algorithm=<bar>` |
| Line Chart | Data Point | Filter table: `issued_quarter=<point>&hash=<series>` |
| Heatmap | Cell | Filter table: `issuer=<row>&algorithm=<col>` |

### Table Behavior on Click

1. **Auto-scroll**: Table smoothly scrolls into view
2. **Pagination Reset**: Page resets to 1
3. **Filter Badge**: Active filter shown as dismissible badge above table
4. **Clear Filters**: "Clear All" button to reset view

---

## Analysis from Attached Certificate

Based on the provided certificate sample (`1.json`), here's what we can extract for signature/hash analysis:

### Signature Algorithm Information

```json
"parsed.signature_algorithm": {
    "name": "SHA256-RSA",
    "oid": "1.2.840.113549.1.1.11"
}
```

**Analysis Points**:
- **Hash Function**: SHA-256 (extracted from name prefix)
- **Signature Type**: RSA (extracted from name suffix)
- **OID**: Standard PKCS#1 SHA256WithRSA identifier
- **Security Status**: ✓ COMPLIANT (SHA-256 is current industry standard)

### Public Key Information

```json
"parsed.subject_key_info": {
    "key_algorithm": {"name": "RSA"},
    "rsa_public_key": {
        "exponent": 65537,
        "length": 4096
    }
}
```

**Analysis Points**:
- **Key Size**: 4096 bits (exceeds 2048-bit minimum requirement)
- **Exponent**: 65537 (standard secure value)
- **Security Score**: Maximum for RSA key size

### Signature Value and Validity

```json
"parsed.signature": {
    "signature_algorithm": {"name": "SHA256-RSA", "oid": "1.2.840.113549.1.1.11"},
    "value": "reZmFtPrIODe1ieqP1rN...",
    "valid": false,
    "self_signed": false
}
```

**Analysis Points**:
- **Signature Value**: Base64-encoded signature bytes
- **Validity Flag**: `false` may indicate chain verification issue (not the signature itself)
- **Self-Signed**: `false` confirms CA-issued certificate

### Fingerprints (Hash Outputs)

```json
"fingerprint_md5": "d7bc5b13440a25ba6393d9660ebbfa8a",
"fingerprint_sha1": "4cf330dbdb9e97b9ecbd529562b2c29d4612b78e",
"fingerprint_sha256": "66aa9efe447265f1ac0ba41167656066005ef5f9d899c8e1ac1f0711ed95a1d7",
"tbs_fingerprint": "f75881e36bcdc00b1628e377e26d3f5dc5622a499ae9b3a274e121ba509afad0",
"tbs_noct_fingerprint": "e182bdc60c922a15b967283162ae030a08fdb589929fcfaf1665c040c10f4a2a",
"spki_subject_fingerprint": "772ac52a2c8ce4cce9dcd1cca9ea1c21b67d2a34f8c4e94e044b52d71360f8f9"
```

**Analysis Points**:
- **Multiple Hash Types**: Certificate stores MD5, SHA-1, SHA-256 fingerprints for different use cases
- **TBS Fingerprint**: Hash of To-Be-Signed portion (used for CT logs)
- **SPKI Fingerprint**: Subject Public Key Info hash (for certificate pinning)

### What Hashes Tell Us

| Fingerprint Type | Purpose | Security Use |
|------------------|---------|--------------|
| `fingerprint_md5` | Legacy compatibility | ⚠ Deprecated - collision vulnerable |
| `fingerprint_sha1` | Legacy browser support | ⚠ Deprecated since 2017 |
| `fingerprint_sha256` | Primary identifier | ✓ Current standard for pinning |
| `tbs_fingerprint` | Certificate Transparency | ✓ SCT verification |
| `spki_subject_fingerprint` | HPKP/Pinning | ✓ Key-based identification |

---

## Understanding Hashes in SSL Certificates

### How Hash Functions Work in Signatures

1. **Certificate Creation**:
   ```
   TBS Certificate → Hash(TBS) → Sign(Hash, CA Private Key) → Signature Value
   ```
   
2. **Certificate Verification**:
   ```
   Signature Value → Verify(Signature, CA Public Key) → Hash₁
   TBS Certificate → Hash(TBS) → Hash₂
   If Hash₁ == Hash₂ → Valid Signature
   ```

### Common Hash Algorithms

| Algorithm | Output Size | Security Status | Notes |
|-----------|------------|-----------------|-------|
| **MD5** | 128 bits | ❌ CRITICAL | Collision attacks proven (2004) |
| **SHA-1** | 160 bits | ⚠ DEPRECATED | Collision attacks feasible (2017) |
| **SHA-256** | 256 bits | ✓ SECURE | Current industry standard |
| **SHA-384** | 384 bits | ✓ SECURE | Required for some compliance |
| **SHA-512** | 512 bits | ✓ SECURE | Maximum security option |

### Security Implications

> [!CAUTION]
> **Collision Resistance**: MD5 and SHA-1 are vulnerable to collision attacks where two different inputs produce the same hash. Attackers can create rogue certificates that appear valid.

> [!IMPORTANT]
> **SHA-256 Standard**: Since 2017, all major browsers and CAs require SHA-256 minimum. Certificates signed with SHA-1 are rejected.

### Detecting Weak Hashes

The dashboard should flag certificates with:
- `signature_algorithm.name` containing "MD5" or "SHA1"
- Issuance date after 2017 with SHA-1 (compliance violation)
- Any MD5-signed certificate regardless of date

---

## Unique Ideas for Valuable Analysis

### 1. Signature Strength Score Card (Described Above)
**Composite rating combining key size + hash algorithm + signature type**

Implementation: Weighted scoring system computed on backend or client-side based on the formula in Card 4.

### 2. Hash Collision Risk Alert
**Proactive warning for vulnerable certificates**

Display:
```
┌─────────────────────────────────────────────────┐
│  ⚠ COLLISION RISK DETECTED                     │
│                                                 │
│  3 certificates use SHA-1 signatures            │
│  1 certificate uses MD5 signature               │
│                                                 │
│  [View Affected Certificates] [Export List]    │
└─────────────────────────────────────────────────┘
```

API: Simple count query for deprecated algorithms

### 3. Algorithm Migration Timeline
**Visual showing when certificates transitioned from SHA-1 to SHA-256**

Purpose:
- Identify if any SHA-1 certificates were issued after deprecation date (Jan 2017)
- Show compliance timeline
- Highlight issuers still using deprecated algorithms

### 4. Key Size Adequacy Indicator
**Quick visual showing if key sizes meet requirements**

Display:
```
RSA Keys:  ████████████████░░░░  80% meet 2048+ standard
           ████████████████████  100% would meet 1024 (legacy)

ECDSA Keys: ████████████████████  100% meet P-256+ standard
```

### 5. Signature Algorithm Comparison Matrix
**Side-by-side comparison of RSA vs ECDSA certificates**

| Metric | RSA Certificates | ECDSA Certificates |
|--------|------------------|-------------------|
| Count | 45,678 (92.3%) | 3,800 (7.7%) |
| Avg Key Size | 2,560 bits | 256 bits (P-256) |
| Avg Validity | 365 days | 90 days |
| Top Issuer | Let's Encrypt | DigiCert |
| Performance | Slower verification | Faster verification |

### 6. Certificate Fingerprint Search
**Allow searching by any fingerprint type**

Feature: Input box accepting SHA-256, SHA-1, or MD5 fingerprint to quickly locate specific certificate.

```typescript
// Frontend component
<SearchBox 
    placeholder="Paste fingerprint (SHA-256, SHA-1, or MD5)..."
    onSearch={(fp) => {
        const type = detectFingerprintType(fp); // Based on length
        filterTable({ [`fingerprint_${type}`]: fp });
    }}
/>
```

### 7. Signature Validity Dashboard
**Quick overview of signature verification status**

Cards:
- **Valid Signatures**: Count where `parsed.signature.valid == true`
- **Invalid/Unverified**: Count where `parsed.signature.valid == false`
- **Chain Status**: Breakdown of why signatures might be invalid

---

## API Integration

### Existing Fields to Use

| Field Path | Description | Use |
|------------|-------------|-----|
| `parsed.signature_algorithm.name` | Combined hash+algorithm (e.g., "SHA256-RSA") | Primary grouping |
| `parsed.signature_algorithm.oid` | OID for the algorithm | Technical details |
| `parsed.signature.value` | Base64 signature bytes | Display/export |
| `parsed.signature.valid` | Signature verification status | Validity tracking |
| `parsed.signature.self_signed` | Is certificate self-signed | Self-signed filter |
| `parsed.subject_key_info.key_algorithm.name` | Key type (RSA/ECDSA) | Algorithm filtering |
| `parsed.subject_key_info.rsa_public_key.length` | RSA key size in bits | Key size analysis |
| `parsed.fingerprint_sha256` | Certificate fingerprint | Identification |

### New APIs Needed

#### 1. Signature/Hash Statistics
```
GET /api/certificates/signature-stats/
Response:
{
    "algorithmDistribution": [
        {"name": "SHA256-RSA", "count": 45678, "percentage": 92.3},
        {"name": "SHA256-ECDSA", "count": 3500, "percentage": 7.1},
        ...
    ],
    "hashDistribution": [
        {"name": "SHA-256", "count": 48000, "percentage": 97.0},
        {"name": "SHA-384", "count": 1200, "percentage": 2.4},
        ...
    ],
    "keySizeDistribution": [
        {"size": 2048, "count": 38500, "percentage": 77.8},
        {"size": 4096, "count": 7500, "percentage": 15.2},
        ...
    ],
    "weakHashCount": 45,
    "complianceRate": 98.5,
    "strengthScore": 94,
    "selfSignedCount": 234
}
```

#### 2. Hash Adoption Trends
```
GET /api/certificates/hash-trends/?months=36&granularity=quarterly
Response:
{
    "trends": [
        {"period": "Q1 2024", "SHA-256": 95.2, "SHA-384": 3.1, "SHA-1": 1.7},
        {"period": "Q2 2024", "SHA-256": 96.5, "SHA-384": 2.8, "SHA-1": 0.7},
        ...
    ]
}
```

#### 3. Issuer Algorithm Heatmap
```
GET /api/certificates/issuer-algorithm-matrix/
Response:
{
    "matrix": [
        {"issuer": "Let's Encrypt", "algorithm": "RSA-2048", "count": 12345},
        {"issuer": "Let's Encrypt", "algorithm": "ECDSA-256", "count": 2341},
        {"issuer": "DigiCert", "algorithm": "RSA-4096", "count": 5678},
        ...
    ]
}
```

---

## Caching Strategy

### Server-Side (Redis)
- Signature stats: 5-minute TTL
- Algorithm distribution: 5-minute TTL
- Hash trends: 15-minute TTL (historical data changes slowly)
- Heatmap: 10-minute TTL

### Client-Side (SWR)
```typescript
const swrConfig = {
    dedupingInterval: 300000,  // 5 minutes
    revalidateOnFocus: false,
    keepPreviousData: true
};
```

---

## Database Fields Summary

| Field | Path | Usage |
|-------|------|-------|
| Signature Algorithm | `parsed.signature_algorithm.name` | Algorithm distribution, compliance |
| Algorithm OID | `parsed.signature_algorithm.oid` | Technical details |
| Key Algorithm | `parsed.subject_key_info.key_algorithm.name` | RSA vs ECDSA |
| RSA Key Size | `parsed.subject_key_info.rsa_public_key.length` | Key size analysis |
| Self-Signed | `parsed.signature.self_signed` | Self-signed filtering |
| Signature Valid | `parsed.signature.valid` | Validity status |
| SHA-256 Fingerprint | `parsed.fingerprint_sha256` | Certificate identification |
| Issuance Date | `parsed.validity.start` | Trend analysis by date |
| Issuer Org | `parsed.issuer.organization[0]` | Issuer grouping |

---

## Implementation Priority

### Phase 1 (MVP)
- 4 core metric cards (Algorithm, Compliance, Weak Hash, Key Size)
- Signature algorithm pie chart
- Hash algorithm bar chart
- Basic table with filtering

### Phase 2 (Enhanced)
- Signature strength score card
- Hash adoption trends line chart
- Self-signed certificates card
- Click-to-filter on all charts

### Phase 3 (Advanced)
- Issuer algorithm heatmap
- Fingerprint search feature
- Algorithm comparison matrix
- Collision risk alerts

---

## Conclusion

The Signature and Hashes page provides critical cryptographic analysis for SSL certificate management. By analyzing signature algorithms, hash functions, and key sizes, administrators can ensure their certificate infrastructure meets current security standards and proactively identify deprecated or vulnerable configurations.

---

## API Reference

This section documents all API endpoints used by the Signature and Hashes page, including their integration with existing code, efficient query patterns, and example responses.

### Endpoint Overview

| Endpoint | Method | Description | Cache TTL |
|----------|--------|-------------|-----------|
| `/api/signature-stats/` | GET | Comprehensive stats for all cards and charts | 5 min |
| `/api/hash-trends/` | GET | Hash algorithm adoption over time | 10 min |
| `/api/issuer-algorithm-matrix/` | GET | Issuer × algorithm combinations | 10 min |
| `/api/certificates/` | GET | Filtered certificate list with pagination | 2 min |

---

### 1. GET `/api/signature-stats/`

**Purpose**: Returns all statistics needed for the 6 metric cards and chart data.

**Parameters**: None

**Response**:
```json
{
    "algorithmDistribution": [
        {"name": "SHA256-RSA", "count": 28423, "percentage": 56.23, "color": "#3b82f6"},
        {"name": "ECDSA-SHA256", "count": 18832, "percentage": 37.25, "color": "#10b981"},
        {"name": "SHA384-RSA", "count": 4156, "percentage": 8.22, "color": "#60a5fa"},
        {"name": "ECDSA-SHA384", "count": 2850, "percentage": 5.64, "color": "#34d399"}
    ],
    "hashDistribution": [
        {"name": "SHA-256", "count": 47255, "percentage": 93.48, "color": "#10b981", "security": "secure"},
        {"name": "Other", "count": 2500, "percentage": 4.95, "color": "#6b7280", "security": "unknown"},
        {"name": "SHA-384", "count": 700, "percentage": 1.38, "color": "#3b82f6", "security": "secure"},
        {"name": "SHA-512", "count": 89, "percentage": 0.18, "color": "#1d4ed8", "security": "secure"},
        {"name": "SHA-1", "count": 5, "percentage": 0.01, "color": "#f59e0b", "security": "deprecated"}
    ],
    "keySizeDistribution": [
        {"name": "RSA 2048", "algorithm": "RSA", "size": 2048, "count": 35000, "percentage": 69.24, "color": "#3b82f6"},
        {"name": "RSA 4096", "algorithm": "RSA", "size": 4096, "count": 12000, "percentage": 23.74, "color": "#3b82f6"},
        {"name": "ECDSA 256", "algorithm": "ECDSA", "size": 256, "count": 3500, "percentage": 6.92, "color": "#10b981"}
    ],
    "weakHashCount": 5,
    "hashComplianceRate": 95.04,
    "strengthScore": 87,
    "selfSignedCount": 1234,
    "totalCertificates": 50549,
    "maxEncryptionType": {
        "name": "RSA",
        "count": 47000,
        "percentage": 92.98
    }
}
```

**Backend Implementation** (`models.py`):
```python
@classmethod
def get_signature_stats(cls) -> Dict:
    # Efficient aggregation pipelines using $group
    # Uses allowDiskUse=True for large datasets
    # See lines 1557-1785 in models.py
```

**Integration**: Called by `SignatureStatsView` in `views.py` with Redis caching.

---

### 2. GET `/api/hash-trends/`

**Purpose**: Hash algorithm adoption trends for the line chart.

**Parameters**:
| Param | Type | Default | Description |
|-------|------|---------|-------------|
| `months` | int | 36 | Number of months to look back |
| `granularity` | string | "quarterly" | "quarterly" or "yearly" |

**Example Request**:
```
GET /api/hash-trends/?months=36&granularity=quarterly
```

**Response**:
```json
[
    {"period": "Q1 2024", "year": 2024, "quarter": 1, "total": 5000, "SHA-256": 94.2, "SHA-384": 3.1, "SHA-512": 1.2, "SHA-1": 1.4, "MD5": 0.1, "Other": 0.0},
    {"period": "Q2 2024", "year": 2024, "quarter": 2, "total": 5500, "SHA-256": 95.8, "SHA-384": 2.8, "SHA-512": 1.0, "SHA-1": 0.3, "MD5": 0.0, "Other": 0.1}
]
```

---

### 3. GET `/api/certificates/` (with signature filters)

**Purpose**: Fetch paginated certificates with signature/hash/key filters.

**New Filter Parameters for Signature Page**:

| Param | Type | Description | Example |
|-------|------|-------------|---------|
| `signature_algorithm` | string | Filter by exact signature algorithm | `SHA256-RSA` |
| `encryption_type` | string | Filter by algorithm type (matches all variants) | `RSA` (matches RSA 2048, RSA 4096) |
| `hash_type` | string | Filter by hash algorithm | `SHA-256`, `SHA-1`, `MD5` |
| `weak_hash` | boolean | Filter weak hash certs (SHA-1, MD5) | `true` |
| `self_signed` | boolean | Filter self-signed certificates | `true` |
| `key_size` | int | Filter by key size | `2048`, `4096` |

**Example Requests**:
```
# Get all RSA certificates (any key size)
GET /api/certificates/?encryption_type=RSA&page=1&page_size=10

# Get weak hash certificates
GET /api/certificates/?weak_hash=true&page=1&page_size=10

# Get self-signed certificates
GET /api/certificates/?self_signed=true&page=1&page_size=10

# Get certificates with specific key size
GET /api/certificates/?key_size=2048&page=1&page_size=10
```

---

## Card Computations

### First Card: Max Encryption Type

**Display**: Shows the encryption type (RSA or ECDSA) with the maximum certificate count.

**Computation**:
```python
# Group by key_algorithm.name, get top 1 by count
pipeline = [
    {'$group': {
        '_id': '$parsed.subject_key_info.key_algorithm.name',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 1}
]
```

**Click Action**: Filters table to show ALL certificates of that encryption type (e.g., clicking "RSA" shows RSA 2048, RSA 4096, etc.).

---

### Second Card: Hash Compliance Rate

**Display**: Percentage of certificates using secure hash algorithms (SHA-256, SHA-384, SHA-512).

**Computation**:
```python
compliant_count = count where signature_algorithm.name matches ^SHA256|^SHA384|^SHA512
total_count = total certificates
compliance_rate = (compliant_count / total_count) * 100
```

**Not Clickable**: This is an informational metric only.

---

### Third Card: Weak Hash Alert

**Display**: Count of certificates using deprecated hash algorithms (MD5, SHA-1).

**Definition of Weak Hash**:
- **MD5**: CRITICAL - Collision attacks proven since 2004
- **SHA-1**: DEPRECATED - Collision attacks feasible since 2017

**Computation**:
```python
weak_count = count where signature_algorithm.name matches ^SHA1|^SHA-1|^MD5
```

**Click Action**: Filters table to show all weak hash certificates with pagination.

---

### Fourth Card: Signature Strength Score

**Display**: Composite security score from 0-100.

**Computation Formula**:
```
Score = (KeySizeScore × 0.4) + (HashScore × 0.4) + (AlgorithmScore × 0.2)
```

**Key Size Score** (weighted by distribution):
| Key Size | Score |
|----------|-------|
| 4096+ bits (RSA) | 100 |
| 2048 bits (RSA) | 80 |
| 1024 bits (RSA) | 40 |
| < 1024 bits | 0 |
| 256+ bits (ECDSA) | 90 |

**Hash Score**: Direct mapping from compliance rate (0-100).

**Algorithm Score**:
| Algorithm | Base Score |
|-----------|------------|
| RSA | 85 |
| ECDSA | 100 (adds 0.15 bonus per percentage point) |

**Example Calculation**:
```
Given:
- 70% RSA 2048 (score 80), 30% RSA 4096 (score 100)
- Hash compliance: 95%
- 20% ECDSA usage

KeySizeScore = (0.7 × 80) + (0.3 × 100) = 86
HashScore = 95
AlgorithmScore = 85 + (20 × 0.15) = 88

FinalScore = (86 × 0.4) + (95 × 0.4) + (88 × 0.2) = 34.4 + 38 + 17.6 = 90
```

**Not Clickable**: Displays score breakdown in tooltip only.

---

### Fifth Card: Top Key Size

**Display**: Most common key size configuration (e.g., "RSA 2048").

**Computation**:
```python
# Group by algorithm + key size, get top 1
pipeline = [
    {'$group': {
        '_id': {
            'algo': '$parsed.subject_key_info.key_algorithm.name',
            'size': '$parsed.subject_key_info.rsa_public_key.length'
        },
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': 1}
]
```

**Click Action**: Filters table to show certificates with that key size.

---

### Sixth Card: Self-Signed Certificates

**Display**: Count of self-signed certificates.

**Computation**:
```python
self_signed_count = count where parsed.signature.self_signed == true
```

**Click Action**: Filters table to show all self-signed certificates.

---

## Efficient Query Patterns

### For Millions of Certificates:

1. **Use Indexes**: Ensure indexes on frequently queried fields:
   ```javascript
   db.certificates.createIndex({"parsed.signature_algorithm.name": 1})
   db.certificates.createIndex({"parsed.subject_key_info.key_algorithm.name": 1})
   db.certificates.createIndex({"parsed.signature.self_signed": 1})
   ```

2. **Use $match Early**: Always put $match stages first in pipelines to reduce documents processed.

3. **Use allowDiskUse**: Enable for large aggregations:
   ```python
   collection.aggregate(pipeline, allowDiskUse=True)
   ```

4. **Limit Projections**: Only project needed fields to reduce memory usage.

5. **Use count_documents()**: For simple counts, use indexed queries instead of aggregation.

---

## Frontend Integration

### SWR Configuration
```typescript
const swrConfig = {
    revalidateOnFocus: false,
    dedupingInterval: 300000,  // 5 minutes
    keepPreviousData: true
};
```

### Table Pagination Without Scroll Reset
- Use `keepPreviousData: true` in SWR to prevent flash
- Update page state without calling `handleFilterChange`
- Maintain scroll position on page change
