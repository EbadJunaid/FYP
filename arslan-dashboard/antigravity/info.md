# SSL Guardian Dashboard - Technical Documentation

This document provides comprehensive explanations of how each dashboard component works, the underlying database queries, what data is real vs hardcoded, and how to verify data accuracy.

---

## Table of Contents
1. [Global Health Card - Detailed Breakdown](#1-global-health-card---detailed-breakdown)
2. [Active Certificates Card](#2-active-certificates-card)
3. [Expiring Soon Card - Action Needed](#3-expiring-soon-card---action-needed)
4. [Critical Vulnerabilities Card](#4-critical-vulnerabilities-card)
5. [CA Leaderboard](#5-ca-leaderboard)
6. [Geographic Distribution](#6-geographic-distribution)
7. [Validity Trends](#7-validity-trends)
8. [Encryption Strength - Complete Explanation](#8-encryption-strength---complete-explanation)
9. [Domain Display in Table](#9-domain-display-in-table)
10. [Scan Date in Table](#10-scan-date-in-table)
11. [SSL Grades Calculation](#11-ssl-grades-calculation)
12. [Validation Level on Certificate Detail Page](#12-validation-level-on-certificate-detail-page)
13. [Table Data - Real vs Hardcoded](#13-table-data---real-vs-hardcoded)
14. [API Endpoints Reference](#14-api-endpoints-reference)
15. [How to Verify Data Correctness](#15-how-to-verify-data-correctness)
16. [Pagination Caching Strategy](#16-pagination-caching-strategy-future-implementation)
17. [Critical Vulnerabilities Card - Why Is It Slower?](#17-critical-vulnerabilities-card---why-is-it-slower)
18. [CA Leaderboard Card - Why Not All CAs Displayed?](#18-ca-leaderboard-card---why-not-all-cas-displayed)
19. [Geographic Distribution Card - How It Works](#19-geographic-distribution-card---how-it-works)

---

## 1. Global Health Card - Detailed Breakdown

### Step-by-Step Calculation

The Global Health score is computed in `models.py` → `get_dashboard_metrics()`:

#### Step 1: Get Total Certificate Count
```python
total = cls.collection.count_documents({})
# Example: total = 5810
```

#### Step 2: Count Expired Certificates
```python
now = cls.get_current_time_iso()  # e.g., "2026-01-08T16:00:00Z"
expired_count = cls.collection.count_documents({
    'parsed.validity.end': {'$lt': now}
})
# Example: expired_count = 103
```
This MongoDB query finds all certificates where `validity.end` (expiration date) is BEFORE the current time.

#### Step 3: Calculate Active Certificates
```python
active_count = total - expired_count
# Example: active_count = 5810 - 103 = 5707
```

#### Step 4: Estimate Critical Vulnerabilities
```python
sample_size = min(total, 500)
sample_docs = list(cls.collection.aggregate([
    {'$sample': {'size': sample_size}},
    {'$project': {'zlint.lints': 1}}
]))

critical_in_sample = 0
for doc in sample_docs:
    lints = doc.get('zlint', {}).get('lints', {})
    error_count = sum(1 for v in lints.values() 
                     if isinstance(v, dict) and v.get('result') == 'error')
    if error_count > 0:
        critical_in_sample += 1

# Extrapolate to total
critical_vulns = int((critical_in_sample / sample_size) * total)
# Example: 200 in sample with errors → (200/500) * 5810 = 2324
```

#### Step 5: Compute Health Score
```python
active_percentage = (active_count / total) * 100
# Example: (5707 / 5810) * 100 = 98.2%

vuln_penalty = min(20, (critical_vulns / total) * 100)
# Example: min(20, (2324/5810)*100) = min(20, 40) = 20

health_score = int(min(100, max(0, active_percentage - vuln_penalty)))
# Example: 98.2 - 20 = 78
```

#### Step 6: Determine Risk Status
```python
if health_score >= 80:
    health_status = 'SECURE'      # Green badge
elif health_score >= 50:
    health_status = 'AT_RISK'     # Yellow badge
else:
    health_status = 'CRITICAL'    # Red badge
```

### What's Real vs Hardcoded
| Item | Real/Hardcoded | Source |
|------|----------------|--------|
| Score (78) | ✅ Real | Calculated from DB |
| Status (AT_RISK) | ✅ Real | Based on score threshold |
| Last Updated | ⚠️ Now shows current time | `datetime.now()` |

---

## 2. Active Certificates Card

### Data Source: **100% REAL from Database**

```python
# MongoDB Query
now = "2026-01-08T16:00:00Z"
expired = cls.collection.count_documents({'parsed.validity.end': {'$lt': now}})
active = total - expired
```

### Logic
- **Active** = Certificate where `validity.end > current_date`
- **Expired** = Certificate where `validity.end < current_date`

---

## 3. Expiring Soon Card - Action Needed

### What Triggers "Action Needed" Badge
```python
expiring_count = cls.collection.count_documents({
    'parsed.validity.end': {'$gte': now, '$lte': now_plus_30}
})
actionNeeded = expiring_count > 100
```

### What Actions Can Be Taken?
When certificates are expiring soon, administrators should:

1. **Renew Certificates**: Contact the CA (Let's Encrypt, DigiCert, etc.) to renew
2. **Automate Renewal**: Set up certbot or ACME for auto-renewal
3. **Monitor Timeline**: Prioritize certificates expiring soonest
4. **Update DNS**: Ensure DNS records are ready for validation
5. **Test New Certs**: Deploy renewed certificates to staging first
6. **Notify Stakeholders**: Alert domain owners of impending expirations

---

## 4. Critical Vulnerabilities Card

### What Constitutes a "Critical" Vulnerability?

We query the `zlint.lints` object in each certificate document. Each lint has a `result` field:
- `"error"` → **Critical vulnerability** (counted)
- `"warn"` → **Warning** (NOT counted here, but shown elsewhere)
- Other values → Ignored

### The Query Logic
```python
lints = doc.get('zlint', {}).get('lints', {})
error_count = sum(1 for v in lints.values() 
                 if isinstance(v, dict) and v.get('result') == 'error')
if error_count > 0:
    # This certificate has critical vulnerabilities
```

### What Types of Errors?
Common zlint errors include:
- Invalid key usage
- Weak signature algorithms
- Missing required extensions
- Malformed certificate fields

### Summary
- **Critical Vulnerabilities Card** = Only certificates with **ERRORS** (not warnings)
- **SSL Grade** = Based on BOTH errors AND warnings

---

## 5. CA Leaderboard

### Calculation
```python
total = cls.collection.count_documents({})
pipeline = [
    {'$unwind': '$parsed.issuer.organization'},
    {'$group': {'_id': '$parsed.issuer.organization', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}},
    {'$limit': 10}
]
# Percentage = (count / total) * 100
```

### Fixed Issue
Previously showing `2675%` because it displayed `count` with a `%` sign. Now correctly shows:
- Let's Encrypt: 46.0%
- Google Trust: 22.3%
- etc.

---

## 6. Geographic Distribution

### How Countries are Derived
Countries are determined from domain TLDs (Top-Level Domains):

```python
TLD_TO_COUNTRY = {
    'pk': 'Pakistan',
    'com': 'United States',
    'uk': 'United Kingdom',
    'de': 'Germany',
    'org': 'International',
    ...
}

def get_tld_country(domain):
    # "example.pk" → "pk" → "Pakistan"
    parts = domain.split('.')
    tld = parts[-1]
    return TLD_TO_COUNTRY.get(tld, 'Unknown')
```

### Limitation
- `.com`, `.org`, `.net` domains map to generic categories
- Country-code TLDs are accurate (.pk, .uk, .de)

---

## 7. Validity Trends

### What It Shows
Certificates expiring in each future month.

```python
for i in range(months):
    month_start = now + timedelta(days=30 * i)
    month_end = now + timedelta(days=30 * (i + 1))
    count = cls.collection.count_documents({
        'parsed.validity.end': {'$gte': start_str, '$lt': end_str}
    })
    trends.append({'month': month_name, 'expirations': count})
```

---

## 8. Encryption Strength - Complete Explanation

### Types of Encryption Algorithms

#### RSA (Rivest-Shamir-Adleman)
- **RSA 2048**: 2048-bit key length, minimum security standard
- **RSA 4096**: 4096-bit key length, stronger security
- **Classification**: "Standard" encryption

#### ECDSA (Elliptic Curve Digital Signature Algorithm)
- Uses elliptic curve cryptography
- Smaller key sizes for equivalent security
- **ECDSA P-256**: 256-bit curve, equivalent to RSA 3072
- **ECDSA P-384**: 384-bit curve, equivalent to RSA 7680
- **Classification**: "Modern" encryption

### Security Comparison
| Algorithm | Key Size | Security Level | Speed |
|-----------|----------|----------------|-------|
| RSA 2048 | 2048-bit | Standard | Slow |
| RSA 4096 | 4096-bit | Strong | Very Slow |
| ECDSA P-256 | 256-bit | Strong (equiv. RSA 3072) | Fast |
| ECDSA P-384 | 384-bit | Very Strong | Fast |

### How We Classify (Standard/Modern)
```python
# HARDCODED mapping in models.py
type_labels = {
    'RSA': 'Standard',      # Older, widely supported
    'ECDSA': 'Modern',      # Newer, faster, recommended
    'EC': 'Modern',
    'DSA': 'Deprecated',    # Outdated, avoid
}
```

### How We Get the Data
```python
pipeline = [
    {'$project': {
        'algo': '$parsed.subject_key_info.key_algorithm.name',
        'rsa_length': '$parsed.subject_key_info.rsa_public_key.length',
        'ec_length': '$parsed.subject_key_info.ecdsa_public_key.length'
    }},
    {'$addFields': {
        'key_length': {'$ifNull': ['$rsa_length', '$ec_length']}
    }},
    {'$group': {
        '_id': {'algo': '$algo', 'length': '$key_length'},
        'count': {'$sum': 1}
    }}
]
# Results in: "RSA 2048", "RSA 4096", "ECDSA 256" etc.
```

---

## 9. Domain Display in Table

### Where Domains Come From
Currently, domains are fetched from:
```python
domain = subject.get('common_name', ['Unknown'])[0]
# From: doc['parsed']['subject']['common_name']
```

### Database Field `domain`
There is also a `domain` field directly in the document root:
```json
{
    "_id": "...",
    "domain": "example.pk",
    "parsed": {
        "subject": {
            "common_name": ["example.pk"]
        }
    }
}
```

### Should Use
The `domain` field at root level should be used for consistency:
```python
domain = doc.get('domain', 'Unknown')
```

---

## 10. Scan Date in Table

### Current Source
```python
'scanDate': validity.get('start', '')
# From: doc['parsed']['validity']['start']
```

This is the certificate's **"Not Before"** date - when it became valid, NOT when it was scanned.

### What It Actually Represents
- **validity.start**: Certificate issue date (Not Before)
- **validity.end**: Certificate expiration date (Not After)

### Suggestion
If a `scanDate` or `lastUpdated` field exists in the database, use that instead for accurate scan timestamps.

---

## 11. SSL Grades Calculation

### Grading Logic (Based on zlint)
```python
lints = zlint_data.get('lints', {})
error_count = count where result == 'error'
warn_count = count where result == 'warn'

if error_count >= 3: return 'F'     # 3+ errors
elif error_count >= 2: return 'C'   # 2 errors
elif error_count >= 1: return 'B'   # 1 error
elif warn_count >= 3: return 'B+'   # 0 errors, 3+ warnings
elif warn_count >= 1: return 'A-'   # 0 errors, 1-2 warnings
else: return 'A+'                   # Perfect
```

---

## 12. Validation Level on Certificate Detail Page

### What Are Validation Levels?

#### DV (Domain Validation)
- **Verification**: Only domain ownership checked
- **Speed**: Minutes to hours
- **Trust**: Basic
- **Example**: Blog sites, personal websites

#### OV (Organization Validation)
- **Verification**: Domain + organization identity
- **Speed**: Days
- **Trust**: Medium
- **Example**: Business websites

#### EV (Extended Validation)
- **Verification**: Thorough legal/physical verification
- **Speed**: Weeks
- **Trust**: Highest (shows company name in browser)
- **Example**: Banks, e-commerce

### How We Determine Validation Level
Currently derived from certificate policy OIDs in `parsed.extensions`:
```python
def get_validation_level(doc):
    extensions = doc.get('parsed', {}).get('extensions', {})
    policies = extensions.get('certificate_policies', [])
    
    for policy in policies:
        if 'organization-validation' in str(policy).lower():
            return 'OV'
        elif 'extended-validation' in str(policy).lower():
            return 'EV'
    
    return 'DV'  # Default
```

⚠️ **Note**: This is currently using basic logic. Full OID matching should be implemented for accuracy.

---

## 13. Table Data - Real vs Hardcoded

### Data Source: **100% REAL from Database**

All table data is fetched via API calls to the backend:
```typescript
// Frontend: pageController.ts
const result = await apiClient.getCertificates({
    page: 1,
    pageSize: 25,
    status: filterStatus,
    country: filterCountry
});
```

Backend query:
```python
# models.py - get_all()
cursor = cls.collection.find(query).skip(skip).limit(page_size)
```

### How to Verify Data is Correct

#### Method 1: MongoDB Shell
```bash
mongo
use latest-pk-domains
db.certificates.count()
db.certificates.findOne()
```

#### Method 2: API Testing (Postman/curl)
```bash
curl http://localhost:8000/api/certificates/?page=1&page_size=5
```

#### Method 3: Compare Counts
1. Get total from API: `/api/dashboard/global-health/` → `activeCertificates.total`
2. Compare with MongoDB: `db.certificates.count()`
3. They should match

---

## 14. API Endpoints Reference

### Dashboard Metrics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/dashboard/global-health/` | GET | Dashboard metrics, health score |

**Response:**
```json
{
    "globalHealth": {"score": 78, "maxScore": 100, "status": "AT_RISK"},
    "activeCertificates": {"count": 5707, "total": 5810},
    "expiringSoon": {"count": 1750, "daysThreshold": 30, "actionNeeded": true},
    "criticalVulnerabilities": {"count": 2324, "new": 232},
    "expiredCertificates": {"count": 103}
}
```

---

### Certificates

| Endpoint | Method | Params | Description |
|----------|--------|--------|-------------|
| `/api/certificates/` | GET | page, page_size, status, country, issuer, search | List certificates |
| `/api/certificates/{id}/` | GET | - | Single certificate detail |

**Example:**
```bash
GET /api/certificates/?page=1&page_size=10&status=VALID
```

---

### Analytics

| Endpoint | Method | Params | Description |
|----------|--------|--------|-------------|
| `/api/encryption-strength/` | GET | - | Encryption type distribution |
| `/api/validity-trends/` | GET | months | Expiration trends |
| `/api/ca-analytics/` | GET | limit | CA leaderboard |
| `/api/geographic-distribution/` | GET | limit | Country distribution |
| `/api/future-risk/` | GET | - | Risk predictions |
| `/api/unique-filters/` | GET | - | Filter dropdown options |
| `/api/vulnerabilities/` | GET | page, page_size | Vulnerable certificates |

---

## 15. How to Verify Data Correctness

### Quick Verification Steps

1. **Check Total Count**
   ```bash
   # MongoDB
   db.certificates.count()
   
   # API
   curl http://localhost:8000/api/dashboard/global-health/ | jq '.activeCertificates.total'
   ```

2. **Verify Specific Certificate**
   ```bash
   # MongoDB
   db.certificates.findOne({domain: "example.pk"})
   
   # API
   curl http://localhost:8000/api/certificates/?search=example.pk
   ```

3. **Check Expired Count**
   ```bash
   # MongoDB
   db.certificates.count({
       "parsed.validity.end": {$lt: "2026-01-08T00:00:00Z"}
   })
   ```

4. **Verify CA Distribution**
   ```bash
   db.certificates.aggregate([
       {$unwind: "$parsed.issuer.organization"},
       {$group: {_id: "$parsed.issuer.organization", count: {$sum: 1}}},
       {$sort: {count: -1}},
       {$limit: 5}
   ])
   ```

---

## Summary: What's Real vs Hardcoded

| Component | Real Data | Hardcoded/Note |
|-----------|-----------|----------------|
| Global Health Score | ✅ | Calculated from DB |
| Active Certificates | ✅ | MongoDB count |
| Expiring Soon | ✅ | 30-day window query |
| Vulnerabilities | ✅ | Sampled & extrapolated |
| CA Leaderboard | ✅ | Aggregation query |
| Geographic | ✅ | Derived from TLD |
| Validity Trends | ✅ | Monthly buckets |
| Encryption Types | ✅ | Standard/Modern labels hardcoded |
| SSL Grades | ✅ | Based on zlint |
| Scan Date | ⚠️ | Uses validity.start (issue date) |
| Future Risk | ⚠️ | Hardcoded predictions |

---

## 16. Why Sampling Was Used (500 Documents) - IMPORTANT

### The Problem with Sampling

In the original implementation, we used MongoDB's `$sample` operator to randomly select 500 documents:

```python
sample_size = min(total, 500)
sample_docs = list(cls.collection.aggregate([
    {'$sample': {'size': sample_size}},
    {'$project': {'zlint.lints': 1}}
]))
```

### Why This Causes Count Changes on Refresh

**The `$sample` operator picks RANDOM documents each time it runs!**

- First refresh: Might pick 200 certificates with errors out of 500
- Second refresh: Might pick 180 certificates with errors out of 500
- Third refresh: Might pick 220 certificates with errors out of 500

Then the code extrapolates to total:
```python
critical_vulns = int((critical_in_sample / 500) * 5810)
# 200/500 * 5810 = 2324
# 180/500 * 5810 = 2092
# 220/500 * 5810 = 2556
```

**This is why the count changes on every refresh!**

### The Fix

We now query ALL documents without sampling:
```python
# Count all certificates with zlint errors
pipeline = [
    {'$match': {'zlint.lints': {'$exists': True}}},
    {'$project': {'lints': {'$objectToArray': '$zlint.lints'}}},
    {'$unwind': '$lints'},
    {'$match': {'lints.v.result': 'error'}},
    {'$group': {'_id': '$_id'}},
    {'$count': 'total'}
]
```

---

## 17. Why Vulnerability Count Changed on Every Refresh

### Root Cause: Random Sampling

The `$sample` operator in MongoDB is **non-deterministic** - it selects different documents each time.

### Before (Random):
```
Refresh 1: Sample picks docs with 40% error rate → 2324 vulnerabilities
Refresh 2: Sample picks docs with 36% error rate → 2092 vulnerabilities
Refresh 3: Sample picks docs with 44% error rate → 2556 vulnerabilities
```

### After (Fixed):
```
Every refresh: Exact count from ALL documents → 2424 vulnerabilities (consistent)
```

---

## 18. Encryption Strength Distribution - Is It Correct?

### What We Fetch
```python
'algo': '$parsed.subject_key_info.key_algorithm.name'  # RSA, ECDSA, EC, etc.
'rsa_length': '$parsed.subject_key_info.rsa_public_key.length'  # 2048, 4096
'ec_length': '$parsed.subject_key_info.ecdsa_public_key.length'  # 256, 384
```

### Is This the Right Thing to Fetch?

**YES!** This is correct because:

1. **`key_algorithm.name`** tells us the encryption algorithm type (RSA, ECDSA)
2. **`rsa_public_key.length`** or **`ecdsa_public_key.length`** tells us the key strength

### What Each Means:

| Field | Value | Meaning |
|-------|-------|---------|
| `key_algorithm.name` | "RSA" | Uses RSA encryption |
| `rsa_public_key.length` | 2048 | 2048-bit key (minimum standard) |
| `rsa_public_key.length` | 4096 | 4096-bit key (stronger) |
| `key_algorithm.name` | "ECDSA" | Uses Elliptic Curve |
| `ecdsa_public_key.length` | 256 | P-256 curve (~RSA 3072 equivalent) |

### Data Uses Full Collection
The encryption strength query uses **full data** via aggregation with grouping - no sampling.

---

## 19. CA Leadership Card - Sample or Total?

### Current Implementation
```python
total = cls.collection.count_documents({})
pipeline = [
    {'$unwind': '$parsed.issuer.organization'},
    {'$group': {'_id': '$parsed.issuer.organization', 'count': {'$sum': 1}}},
    {'$sort': {'count': -1}},
    {'$limit': 10}
]
```

### Is This Full Data?

**YES!** The aggregation pipeline:
1. Processes ALL documents in the collection (no $sample)
2. Groups by issuer organization
3. Counts occurrences
4. Sorts by count descending
5. Limits to top 10

### Percentage Calculation
```python
percentage = round((count / total) * 100, 1)
```

This is accurate because both `count` (from aggregation) and `total` (from count_documents) use the complete dataset.

---

## 20. Geographic Distribution - Country Source

### Current Implementation

Countries are derived from **domain TLD** (Top-Level Domain):

```python
def get_tld_country(domain):
    parts = domain.lower().split('.')
    tld = parts[-1]  # e.g., "pk" from "example.pk"
    return TLD_TO_COUNTRY.get(tld, 'Unknown')
```

### Why NOT from parsed.subject.country?

The `parsed.subject.country` field exists but:
1. **Often missing** - Many certificates don't have this field populated
2. **Represents CA's country** - Not the domain owner's country
3. **Inconsistent** - Some have country codes, some have full names

### Should "Server Location" Label Be Used?

**NO!** The TLD-derived country is NOT the server location. It's the **domain registration country**.

- `example.pk` → Pakistan domain → Owner likely in Pakistan
- But the server could be hosted in US, Germany, etc.

### Better Label: "Domain Country" or "Registration Country"

### Priority Order (Updated):
1. First check `parsed.subject.country` if present and valid
2. If not, derive from domain TLD

---

## 16. Pagination Caching Strategy (Future Implementation)

### Overview

This section explains the caching logic for paginated data to avoid repeated API calls for the same pages/filters.

### Current Behavior (No Caching)

Currently, every page change triggers a new API call:
- Click "Page 2" → API call to `/api/certificates/?page=2&page_size=10`
- Click "Page 1" → API call to `/api/certificates/?page=1&page_size=10` (again!)

This is inefficient when users navigate back and forth between pages.

### Proposed Caching Solution

#### Cache Structure

```typescript
interface PageCache {
  [filterKey: string]: {
    [pageNumber: number]: {
      data: ScanEntry[];
      timestamp: number;
    };
  };
}

// Example cache state:
{
  "filter:all": {
    1: { data: [...10 certs...], timestamp: 1704891234567 },
    2: { data: [...10 certs...], timestamp: 1704891256789 }
  },
  "filter:status=VALID": {
    1: { data: [...10 certs...], timestamp: 1704891278901 }
  },
  "filter:issuer=Google Trust Services": {
    1: { data: [...10 certs...], timestamp: 1704891290123 }
  }
}
```

#### Caching Logic

```typescript
const setPage = async (page: number) => {
  const cacheKey = getFilterCacheKey(activeFilter);
  
  // Check cache first
  if (pageCache[cacheKey]?.[page]) {
    const cached = pageCache[cacheKey][page];
    const age = Date.now() - cached.timestamp;
    
    // Use cache if less than 5 minutes old
    if (age < 5 * 60 * 1000) {
      setState(prev => ({ ...prev, recentScans: cached.data }));
      setPagination(prev => ({ ...prev, currentPage: page }));
      return; // No API call needed!
    }
  }
  
  // Cache miss or expired - fetch from API
  const result = await fetchCertificates({ page, pageSize: 10, ...activeFilter });
  
  // Store in cache
  setPageCache(prev => ({
    ...prev,
    [cacheKey]: {
      ...prev[cacheKey],
      [page]: { data: result.certificates, timestamp: Date.now() }
    }
  }));
  
  setState(prev => ({ ...prev, recentScans: result.certificates }));
};
```

#### Cache Invalidation

Clear cache when:
1. **Filter changes**: New card clicked → clear all pages for old filter
2. **Data update**: Certificate added/deleted → clear entire cache
3. **Time expiry**: Cache entries older than 5 minutes → refetch
4. **Manual refresh**: User clicks refresh → clear cache

```typescript
// On filter change
const handleCardClick = (cardType, data) => {
  // Clear cache for new filter
  setPageCache({});
  
  // Fetch first page
  const result = await fetchCertificates(...);
  
  // Store in new cache
  setPageCache({ [cacheKey]: { 1: result.certificates } });
};
```

### Benefits

1. **Reduced API load**: Fewer duplicate requests
2. **Faster navigation**: Instant page switches for cached pages
3. **Better UX**: No loading spinner for cached data
4. **Lower server costs**: Less database queries

### Implementation Options

1. **React Query**: Built-in caching with stale-while-revalidate
2. **Redux Toolkit Query**: Integrated with Redux state
3. **SWR**: Lightweight data fetching with caching
4. **Custom useState/useRef**: Simple manual caching

### Note

This caching strategy is documented for **future implementation** and is not currently active in the codebase.

---

## 17. Critical Vulnerabilities Card - Why Is It Slower?

### The Problem

When you click the Critical Vulnerabilities card, you notice it takes longer to load and navigate between pages compared to Global Health or Active Certificates cards. Here's why:

### Root Cause: Complex Aggregation Pipeline

**Global Health / Active Certificates queries are simple:**
```python
# Simple indexed query - FAST
cls.collection.count_documents({'parsed.validity.end': {'$gt': now}})
cls.collection.find(query).skip(skip).limit(page_size)
```
These use MongoDB's standard `find()` with indexed fields, which is O(log n) lookup.

**Critical Vulnerabilities query is complex:**
```python
# Complex aggregation - SLOW
count_pipeline = [
    {'$match': {'zlint.lints': {'$exists': True, '$ne': {}}}},
    {'$project': {
        '_id': 1,
        'lints_array': {'$objectToArray': '$zlint.lints'}  # Converts object to array
    }},
    {'$match': {'lints_array.v.result': 'error'}},  # Checks if ANY lint has error
    {'$count': 'total'}
]
```

### Step-by-Step Explanation

1. **$match on zlint.lints existence**: First, filter to only documents that have zlint results.

2. **$objectToArray conversion**: This is the SLOW part. The `zlint.lints` field is an object like:
   ```json
   {
     "e_dnsname_not_valid_tld": {"result": "error", "details": "..."},
     "w_subject_common_name_deprecated": {"result": "warn", "details": "..."},
     "n_contains_redacted_dnsname": {"result": "notice", "details": "..."}
   }
   ```
   MongoDB must convert EVERY lint in EVERY document to an array format:
   ```json
   [
     {"k": "e_dnsname_not_valid_tld", "v": {"result": "error"}},
     {"k": "w_subject_common_name_deprecated", "v": {"result": "warn"}},
     ...
   ]
   ```

3. **$match on lints_array.v.result**: Then it checks if ANY element has `result: "error"`.

### Why We Can't Use Simple Query

Unlike status filters where we query indexed fields:
```python
query['parsed.validity.end'] = {'$gt': now}  # Indexed field
```

The zlint.lints structure is a **dynamic object with variable keys**. We CANNOT directly query:
```python
query['zlint.lints.*.result'] = 'error'  # MongoDB doesn't support wildcards like this
```

### Optimized Approach: Use Boolean Flags

The SSL certificates in the DB have boolean flags:
- `zlint.errors_present`: true if ANY lint has `result: "error"`
- `zlint.warnings_present`: true if ANY lint has `result: "warn"`

**Optimized query using these flags:**
```python
# FAST - uses indexed boolean field
query = {'zlint.errors_present': True}
total = cls.collection.count_documents(query)
cursor = cls.collection.find(query).skip(skip).limit(page_size)
```

### Important: Are We Checking Certificates One-by-One?

**NO**, we are NOT checking each certificate individually in Python. The aggregation pipeline runs entirely in MongoDB, but:

1. The `$objectToArray` operation is expensive (O(n * m) where n = documents, m = lints per doc)
2. The pipeline must process EVERY document that has zlint data
3. There's no index on the converted array elements

---

## 18. CA Leaderboard Card - Why Not All CAs Displayed?

### Current Implementation

The CA Leaderboard uses a **limit** parameter (default: 10):

```python
@classmethod
def get_ca_distribution(cls, limit: int = 10) -> List[Dict]:
    pipeline = [
        {'$project': {
            'issuer_org': {'$arrayElemAt': ['$parsed.issuer.organization', 0]}
        }},
        {'$match': {'issuer_org': {'$exists': True, '$ne': None}}},
        {'$group': {
            '_id': '$issuer_org',
            'count': {'$sum': 1}
        }},
        {'$sort': {'count': -1}},
        {'$limit': limit}  # <-- LIMIT HERE: Only top 10 CAs
    ]
```

### Why Limit?

1. **UI Space**: The card has limited vertical space to display CAs
2. **Readability**: Showing 50+ CAs would be overwhelming
3. **Performance**: Aggregation over all CAs is already computed, limit just for display

### How Many Unique CAs Exist?

Based on the `unique.json` file (result of DB query), there are **18 unique CAs**:
- Let's Encrypt
- Google Trust Services
- Sectigo Limited
- DigiCert Inc
- DigiCert, Inc.
- GoGetSSL
- GoDaddy.com, Inc.
- Amazon
- Starfield Technologies, Inc.
- cPanel, LLC
- ZeroSSL
- CLOUDFLARE, INC.
- SSL Corporation
- WoTrus CA Limited
- Buypass AS-983163327
- Certainly
- Certera
- Entrust Limited
- GlobalSign nv-sa

### Summing to 100%

The percentages shown (e.g., 46%, 38.5%, 5.5%, etc.) **DO sum to 100%** because:
- We calculate `percentage = (ca_count / total) * 100`
- Total = ALL certificates, not just top 10 CAs
- The remaining CAs (beyond top 10) would also contribute to 100%

### Solution: Add "Others" Entry

To show all CAs without UI clutter, we can add an "Others" entry:
```python
# After getting top 10
top_ca_counts = sum(r['count'] for r in results[:10])
others_count = total - top_ca_counts
if others_count > 0:
    results.append({
        'name': 'Others',
        'count': others_count,
        'percentage': round((others_count / total) * 100, 1)
    })
```

---

## 19. Geographic Distribution Card - How It Works

### Current Implementation

The geographic distribution derives country from the **domain TLD** (Top-Level Domain):

```python
@classmethod
def get_geographic_distribution(cls, limit: int = 10) -> List[Dict]:
    pipeline = [
        {'$unwind': '$parsed.subject.common_name'},  # Get domain
        {'$group': {
            '_id': '$parsed.subject.common_name',
            'count': {'$sum': 1}
        }},
        {'$limit': 5000}
    ]
    
    results = list(cls.collection.aggregate(pipeline))
    
    # Group by country using TLD
    country_counts = {}
    for r in results:
        country = cls.get_tld_country(r['_id'])  # Extract TLD -> Country
        country_counts[country] = country_counts.get(country, 0) + r['count']
```

### TLD to Country Mapping

The `get_tld_country()` method maps country-code TLDs:
```python
TLD_TO_COUNTRY = {
    'pk': 'Pakistan',
    'us': 'United States',
    'uk': 'United Kingdom',
    'de': 'Germany',
    'fr': 'France',
    'cn': 'China',
    'jp': 'Japan',
    'in': 'India',
    'au': 'Australia',
    'ca': 'Canada',
    'com': 'United States',  # Generic TLDs default to US
    'org': 'United States',
    'net': 'United States',
    # ... more mappings
}

def get_tld_country(domain):
    tld = domain.split('.')[-1].lower()
    return TLD_TO_COUNTRY.get(tld, 'Unknown')
```

### Why Not Use parsed.subject.country?

The `parsed.subject.country` field exists BUT:

1. **Often Missing**: Many certificates don't have this field populated
2. **Represents CA's Country**: Not the domain owner's country
3. **Inconsistent Format**: Some have country codes ("US"), some have full names ("United States")

### Recommendation: Hybrid Approach

For more accurate country detection:

1. **First Priority**: Check `parsed.subject.country` if present and valid
2. **Second Priority**: Use GeoIP lookup on the domain's resolved IP (requires external API)
3. **Fallback**: Derive from TLD as current implementation

```python
def get_certificate_country(doc):
    # Priority 1: Subject country field
    subject_country = doc.get('parsed', {}).get('subject', {}).get('country', [])
    if subject_country and subject_country[0]:
        return normalize_country_name(subject_country[0])
    
    # Priority 2: TLD derivation
    domain = doc.get('domain', '')
    return get_tld_country(domain)
```

### Why It Might Be Slow Now

The current implementation:
1. Uses `$unwind` on common_name (creates intermediate docs)
2. Groups 5000 domains first
3. Then iterates in Python to derive countries

**Optimized approach**: Compute TLD in MongoDB aggregation:
```python
pipeline = [
    {'$project': {
        'tld': {'$arrayElemAt': [{'$split': ['$domain', '.']}, -1]}
    }},
    {'$group': {
        '_id': '$tld',
        'count': {'$sum': 1}
    }},
    {'$sort': {'count': -1}},
    {'$limit': limit}
]
# Then map TLDs to countries in Python (much smaller dataset)
```
