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
20. [Validity Trends Card - How Data Is Fetched](#20-validity-trends-card---how-data-is-fetched)
21. [Validity Trends: Count vs Full Certificate Data](#21-validity-trends-count-vs-full-certificate-data)
22. [Card Clickability: Card vs Content](#22-card-clickability-card-vs-content)
23. [Info Icons: Why Only on Some Cards?](#23-info-icons-why-only-on-some-cards)
24. [Current Pagination Approach - Offset-Based](#24-current-pagination-approach---offset-based-pagination)
25. [Better Pagination Alternatives](#25-better-pagination-alternatives-for-large-datasets)
26. [Migration Strategy: Changing Pagination](#26-migration-strategy-changing-pagination-without-breaking-existing-logic)
27. [Caching Strategy for Millions of Certificates](#27-caching-strategy-for-millions-of-certificates)
28. [Download Implementation - Complete Data vs This Page](#28-download-implementation---complete-data-vs-this-page-only)
29. [Notification System - Suggestions and Implementation](#29-notification-system---suggestions-and-implementation)

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

---

## 20. Validity Trends Card - How Data Is Fetched

### Data Source and Query

The Validity Trends card shows how many certificates expire/expired in each calendar month. The data is fetched using `CertificateModel.get_validity_trends()`:

```python
@classmethod
def get_validity_trends(cls, months_before: int = 4, months_after: int = 4) -> List[Dict]:
    """Get certificate expiration trends by calendar month"""
    from calendar import monthrange
    from dateutil.relativedelta import relativedelta
    
    trends = []
    now = datetime.now(timezone.utc)
    
    for i in range(-months_before, months_after + 1):
        target_date = now + relativedelta(months=i)
        year = target_date.year
        month = target_date.month
        
        # Get first and last day of the month
        _, days_in_month = monthrange(year, month)
        month_start = datetime(year, month, 1, 0, 0, 0, tzinfo=timezone.utc)
        month_end = datetime(year, month, days_in_month, 23, 59, 59, tzinfo=timezone.utc)
        
        # Count certificates expiring in this month
        count = cls.collection.count_documents({
            'parsed.validity.end': {
                '$gte': month_start.strftime('%Y-%m-%dT%H:%M:%SZ'),
                '$lte': month_end.strftime('%Y-%m-%dT%H:%M:%SZ')
            }
        })
        
        trends.append({
            'month': month_start.strftime('%b %Y'),  # e.g., "Jan 2026"
            'expirations': count,
            'year': year,
            'monthNum': month,
            'isCurrent': (year == now.year and month == now.month)
        })
    
    return trends
```

### Step-by-Step Breakdown

1. **Calculate Month Range**: Starting from 4 months before current to 4 months after (total 9 months)
2. **For Each Month**: Calculate calendar boundaries (1st to last day)
3. **Count Query**: Use `count_documents()` to count certificates where `parsed.validity.end` falls within that month
4. **Return Format**: Returns month label ("Jan 2026"), count, and metadata

---

## 21. Validity Trends: Count vs Full Certificate Data

### Question: "Since you're fetching count by dates, don't you already have the full data?"

**No**, the `get_validity_trends()` method **only returns counts**, not the full certificate documents:

```python
# This returns COUNT only (integer)
count = cls.collection.count_documents({
    'parsed.validity.end': {'$gte': month_start, '$lte': month_end}
})
```

### Why Count-Only?

1. **Performance**: Counting is O(1) with indexes, fetching full documents is O(n)
2. **Memory**: A count uses ~bytes, full documents use ~KB each × thousands
3. **Display Purpose**: The chart only needs the number for the Y-axis

### When You Click a Month

When a user clicks on a month in the Validity Trend chart, a **separate query** is made with pagination:

```python
# This returns FULL DOCUMENTS with pagination
result = CertificateModel.get_all(
    page=1,
    page_size=10,
    expiring_month=1,    # January
    expiring_year=2026   # 2026
)
# Returns: { certificates: [...], pagination: {...} }
```

This is the same pattern used for other cards:
- **Display**: Count-only query for fast chart rendering
- **Click/Filter**: Full paginated query for table display

---

## 22. Card Clickability: Card vs Content

### Question: "The validity card itself is clickable, not the curve. But CA Leaderboard content is clickable?"

You are correct! There are **two clickability patterns** in the dashboard:

### Pattern 1: Card-Level Clickability (Validity Trends, Global Health)
```tsx
<Card
    onClick={() => handleCardClick('validityTrend')}
    isClickable={true}  // Entire card is clickable
>
    <AreaChart data={validityTrend} />
</Card>
```
- **Clicking anywhere on the card** (including chart area) triggers the same action
- Common for overview/summary cards

### Pattern 2: Content-Level Clickability (CA Leaderboard, Encryption Strength)
```tsx
<Card isClickable={false}>  {/* Card NOT clickable */}
    {data.map(item => (
        <div
            onClick={() => handleCardClick('ca', item)}  {/* Each item clickable */}
            className="cursor-pointer hover:bg-..."
        >
            {item.name}
        </div>
    ))}
</Card>
```
- **Clicking specific items** (e.g., "Let's Encrypt", "RSA 2048") triggers filtered action
- Each click passes different data to the handler

### Why Different Patterns?

| Card Type | Click Behavior | Reason |
|-----------|---------------|--------|
| **Validity Trends** | Card-level | Chart shows aggregate trends; clicking shows all certs (or TODO: point-specific) |
| **CA Leaderboard** | Content-level | Each CA is a distinct filter; clicking "Let's Encrypt" shows only those certs |
| **Encryption Strength** | Content-level | Each algorithm is a distinct filter |
| **Global Health** | Card-level | Single aggregate metric; shows all certs |
| **Geographic** | Content-level | Each country is a distinct filter |

### Current Implementation Issue

Currently, the Validity Trends card is **card-level clickable**, meaning clicking anywhere shows all certs in some month range. To make **individual month points clickable** (like CA Leaderboard), the chart needs `onClick` handlers on data points:

```tsx
<Area
    dataKey="expirations"
    onClick={(data) => handleMonthClick(data.month)}  // Per-point click
/>
```

---

## 23. Info Icons: Why Only on Some Cards?

### Question: "Why are info icons only on Active, Expiring Soon, and Vulnerabilities cards?"

The info icons with tooltips were initially added to the **MetricCard** component only:

```tsx
// MetricCard.tsx - Has infoTooltip prop
export default function MetricCard({
    infoTooltip,  // ✅ Added
    ...
}: MetricCardProps) {
```

### Current State

| Card | Uses Component | Has Info Icon |
|------|----------------|---------------|
| Global Health | `GlobalHealthCard` | ❌ Not yet |
| Active Certificates | `MetricCard` | ✅ Yes |
| Expiring Soon | `MetricCard` | ✅ Yes |
| Critical Vulnerabilities | `MetricCard` | ✅ Yes |
| Encryption Strength | `Card` + custom | ❌ Not yet |
| Future Prediction | `Card` + custom | ❌ Not yet |
| CA Leaderboard | `Card` + custom | ❌ Not yet |
| Geographic Distribution | `Card` + custom | ❌ Not yet |
| Validity Trends | `Card` + custom | ❌ Not yet |
| Recent Scans Table | `Card` + custom | ❌ Not yet |

### Solution: Add to All Cards

The `Card` component already supports `infoTooltip`:
```tsx
// Card.tsx - Already has infoTooltip prop
<Card
    title="CA Leaderboard"
    infoTooltip="Top certificate authorities by issuance count"
>
```

To add info icons to all cards, simply pass the `infoTooltip` prop when using each card component.

---

## 24. Current Pagination Approach - Offset-Based Pagination

### What Type of Pagination Are We Using?

We are currently using **Offset-Based Pagination** (also called "skip/limit" pagination):

```python
# models.py - get_all method
skip = (page - 1) * page_size  # e.g., page 2 → skip 10
cursor = cls.collection.find(query).skip(skip).limit(page_size)
```

### How It Works

1. **User requests page N** → Frontend calls `/api/certificates?page=N&page_size=10`
2. **Backend calculates offset** → `skip = (N - 1) * 10`
3. **MongoDB query** → `db.certificates.find({...}).skip(skip).limit(10)`
4. **Return results** → 10 certificates + total count for pagination UI

### Why Offset Pagination is Problematic for Millions of Certificates

| Problem | Explanation | Impact at Scale |
|---------|-------------|-----------------|
| **O(n) complexity** | MongoDB must scan ALL documents before `skip` offset | Page 100,000 = scan 1M+ docs first |
| **Memory pressure** | Large skip values load docs into memory then discard | Server memory spikes |
| **Inconsistency** | If data changes between pages, you may see duplicates or miss items | Data integrity issues |
| **Slow deep pages** | Page 1 = fast, Page 10,000 = very slow | Poor UX for pagination |

### Real Performance Example

```
Page 1    (skip 0):     ~5ms     ✅ Fast
Page 100  (skip 1000):  ~50ms    ⚠️ Noticeable
Page 1000 (skip 10000): ~500ms   ❌ Slow
Page 10000 (skip 100000): ~5s+   ❌ Unusable
```

### When Is Offset Pagination Acceptable?

✅ **Good for:**
- Small datasets (< 100,000 records)
- Users typically view only first few pages
- Simple implementation needs
- Admin dashboards with limited data

❌ **Not ideal for:**
- Millions of certificates
- Deep pagination (page 1000+)
- Real-time data that changes frequently
- High-concurrency systems

---

## 25. Better Pagination Alternatives for Large Datasets

### Option 1: Cursor-Based (Keyset) Pagination ⭐ RECOMMENDED

Instead of "skip N records", use "get records after this ID":

```python
# Cursor-based approach
def get_all_cursor(cls, last_id: str = None, page_size: int = 10):
    query = {}
    if last_id:
        query['_id'] = {'$gt': ObjectId(last_id)}
    
    cursor = cls.collection.find(query).sort('_id', 1).limit(page_size)
    certificates = list(cursor)
    
    next_cursor = str(certificates[-1]['_id']) if certificates else None
    return {'certificates': certificates, 'next_cursor': next_cursor}
```

**Advantages:**
- O(1) performance regardless of page depth
- Uses index efficiently (`_id` is always indexed)
- Consistent results even if data changes
- Scales to billions of records

**Frontend Usage:**
```tsx
// First page
GET /api/certificates?page_size=10

// Next page (use cursor from previous response)
GET /api/certificates?after=507f1f77bcf86cd799439011&page_size=10
```

### Option 2: Time-Based Cursor (For Chronological Data)

If certificates are often queried by date:

```python
def get_all_by_date(cls, before_date: str = None, page_size: int = 10):
    query = {}
    if before_date:
        query['parsed.validity.end'] = {'$lt': before_date}
    
    cursor = cls.collection.find(query).sort('parsed.validity.end', -1).limit(page_size)
    return list(cursor)
```

### Option 3: Search After (Elasticsearch-style)

For complex sorting with multiple fields:

```python
# Sort by (expiry_date, _id) for deterministic results
query = {}
if search_after:
    query['$or'] = [
        {'parsed.validity.end': {'$lt': search_after[0]}},
        {
            'parsed.validity.end': search_after[0],
            '_id': {'$gt': ObjectId(search_after[1])}
        }
    ]
```

### Comparison Table

| Technique | Deep Page Speed | Implementation | Jump to Page | Consistency |
|-----------|-----------------|----------------|--------------|-------------|
| Offset (current) | O(n) slow | ⭐ Easy | ✅ Yes | ❌ Poor |
| Cursor-based | O(1) fast | ⭐⭐ Medium | ❌ No | ✅ Good |
| Time-based | O(1) fast | ⭐⭐ Medium | ❌ No | ✅ Good |
| Search After | O(1) fast | ⭐⭐⭐ Complex | ❌ No | ✅ Good |

---

## 26. Migration Strategy: Changing Pagination Without Breaking Existing Logic

### Step 1: Add New Cursor-Based Endpoint (Non-Breaking)

```python
# views.py - Add new endpoint, keep old one
class CertificateListCursorView(View):
    """New cursor-based pagination (v2)"""
    def get(self, request):
        after_id = request.GET.get('after')
        page_size = int(request.GET.get('page_size', 10))
        
        result = CertificateController.get_certificates_cursor(
            after_id=after_id,
            page_size=page_size,
            # ... other filters
        )
        return json_response(result)
```

### Step 2: Update Controller

```python
# controllers.py
@staticmethod
def get_certificates_cursor(after_id=None, page_size=10, **filters):
    return CertificateModel.get_all_cursor(
        after_id=after_id,
        page_size=page_size,
        **filters
    )
```

### Step 3: Update Model

```python
# models.py
@classmethod
def get_all_cursor(cls, after_id=None, page_size=10, **kwargs):
    query = cls._build_query(**kwargs)  # Reuse existing filter logic
    
    if after_id:
        query['_id'] = {'$gt': ObjectId(after_id)}
    
    cursor = cls.collection.find(query).sort('_id', 1).limit(page_size + 1)
    docs = list(cursor)
    
    has_more = len(docs) > page_size
    certificates = [cls.serialize_certificate(d) for d in docs[:page_size]]
    
    return {
        'certificates': certificates,
        'pagination': {
            'has_more': has_more,
            'next_cursor': str(docs[-2]['_id']) if has_more else None,
            'page_size': page_size
        }
    }
```

### Step 4: Update Frontend (Gradual Migration)

```tsx
// Option A: Keep numbered pagination UI, use cursor internally
// Store cursor for each "page" in state

// Option B: Switch to "Load More" button
interface CursorPagination {
    hasMore: boolean;
    nextCursor: string | null;
}

const loadMore = async () => {
    const result = await apiClient.getCertificatesCursor({
        after: pagination.nextCursor,
        pageSize: 10,
        ...activeFilters
    });
    setData(prev => [...prev, ...result.certificates]);
    setPagination(result.pagination);
};
```

### Step 5: Deprecation Timeline

1. **Week 1-2**: Add cursor endpoint alongside existing
2. **Week 3-4**: Update frontend to use cursor for deep pages
3. **Week 5-6**: Monitor performance and fix issues
4. **Week 7+**: Deprecate offset endpoint for large queries

---

## 27. Caching Strategy for Millions of Certificates

### Why Caching Is Essential

Without caching, every dashboard load = 10+ API calls × DB queries = slow and resource-intensive.

### Caching Layers Overview

```
┌─────────────────────────────────────────────────────────┐
│                    USER BROWSER                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Client-Side Cache (React Query / SWR / State)  │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    CDN / Edge Cache                      │
│  (CloudFlare, Vercel Edge, AWS CloudFront)              │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND SERVER                         │
│  ┌─────────────────────────────────────────────────┐    │
│  │   Server-Side Cache (Redis / Memcached)         │    │
│  └─────────────────────────────────────────────────┘    │
│                           │                              │
│  ┌─────────────────────────────────────────────────┐    │
│  │   MongoDB Query Cache (Application-level)       │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    MONGODB                               │
│  (WiredTiger cache, index cache)                        │
└─────────────────────────────────────────────────────────┘
```

### Recommendation: Client-Side + Server-Side (Hybrid)

#### Layer 1: Client-Side Caching (React Query or SWR) ⭐ EASIEST

**Why React Query/SWR:**
- Automatic caching with stale-while-revalidate
- Deduplication of concurrent requests
- Background refetching
- Built-in loading/error states

**Implementation:**

```tsx
// Install: npm install @tanstack/react-query

// _app.tsx or providers
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 5 * 60 * 1000,      // 5 minutes
            cacheTime: 30 * 60 * 1000,     // 30 minutes
            refetchOnWindowFocus: false,
        },
    },
});

// Usage in component
const { data, isLoading, error } = useQuery({
    queryKey: ['certificates', { page, status, issuer }],
    queryFn: () => apiClient.getCertificates({ page, status, issuer }),
});
```

**Cache Keys:**
```tsx
// Different keys = different cache entries
['certificates', { page: 1, status: 'active' }]
['certificates', { page: 1, status: 'expiring_soon' }]
['certificates', { page: 2, status: 'active' }]
```

#### Layer 2: Server-Side Caching (Redis) ⭐ RECOMMENDED FOR SCALE

**Why Redis:**
- Sub-millisecond reads
- Shared across all server instances
- TTL-based expiration
- Industry standard

**Implementation:**

```python
# cache.py
import redis
import json
import hashlib

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(host='localhost', port=6379, db=0)
    
    def _make_key(self, prefix: str, params: dict) -> str:
        """Generate cache key from params"""
        sorted_params = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        return f"{prefix}:{hash_val}"
    
    def get(self, prefix: str, params: dict):
        key = self._make_key(prefix, params)
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    def set(self, prefix: str, params: dict, value: dict, ttl: int = 300):
        key = self._make_key(prefix, params)
        self.redis.setex(key, ttl, json.dumps(value))
    
    def invalidate(self, prefix: str):
        """Invalidate all keys with prefix"""
        for key in self.redis.scan_iter(f"{prefix}:*"):
            self.redis.delete(key)

cache = CacheService()

# Usage in models.py
@classmethod
def get_all(cls, **kwargs):
    # Try cache first
    cached = cache.get('certificates_list', kwargs)
    if cached:
        return cached
    
    # Query database
    result = cls._query_database(**kwargs)
    
    # Store in cache (5 minute TTL)
    cache.set('certificates_list', kwargs, result, ttl=300)
    
    return result
```

#### TTL Recommendations

| Data Type | TTL | Reason |
|-----------|-----|--------|
| Dashboard metrics | 5 min | Changes infrequently |
| Certificate list | 2-5 min | May change with new scans |
| CA leaderboard | 15 min | Very stable data |
| Geographic distribution | 30 min | Almost static |
| Validity trends | 15 min | Changes monthly |
| Single certificate | 1 hour | Rarely changes |

### Easiest Implementation Path

1. **Start with React Query** (client-side) - 2 hours of work
2. **Add HTTP caching headers** - 30 minutes
3. **Add Redis later** if needed - 4-8 hours

**HTTP Cache Headers (Quick Win):**

```python
# views.py
from django.views.decorators.cache import cache_control

class DashboardMetricsView(View):
    @method_decorator(cache_control(max_age=300, public=True))
    def get(self, request):
        # Response cached by browser/CDN for 5 minutes
        return json_response(metrics)
```

### Summary: What to Use

| Scenario | Recommendation |
|----------|----------------|
| Quick implementation | Client-side (React Query/SWR) |
| Production scale | Redis + React Query |
| Static data (CA list) | CDN/Edge cache |
| Real-time needs | Skip caching, optimize queries |
| Budget constraints | HTTP cache headers + React Query |

---

## 28. Download Implementation - Complete Data vs This Page Only

### Overview

The download button should offer two options:
1. **This Page Only**: Generate CSV client-side from current table data
2. **Complete Data**: Stream full CSV from backend for all filtered certificates

### Backend Implementation

**Streaming CSV Generator** (handles millions without memory issues):

```python
# views.py
from django.http import StreamingHttpResponse
import csv
from io import StringIO

class CertificateDownloadView(View):
    def get(self, request):
        # Get filter params
        status = request.GET.get('status')
        issuer = request.GET.get('issuer')
        # ... other filters
        
        # Create streaming response
        response = StreamingHttpResponse(
            self._generate_csv(status=status, issuer=issuer),
            content_type='text/csv'
        )
        response['Content-Disposition'] = 'attachment; filename="certificates.csv"'
        return response
    
    def _generate_csv(self, **filters):
        """Generator for streaming CSV rows"""
        # Yield header row
        yield self._csv_row([
            'Domain', 'Start Date', 'End Date', 'SSL Grade', 
            'Encryption', 'Issuer', 'Country', 'Status', 'Vulnerabilities'
        ])
        
        # Stream data in batches
        batch_size = 1000
        query = CertificateModel.build_download_query(**filters)
        cursor = CertificateModel.collection.find(query).batch_size(batch_size)
        
        for doc in cursor:
            cert = CertificateModel.serialize_certificate(doc)
            yield self._csv_row([
                cert.get('domain', 'N/A'),
                cert.get('validFrom', 'N/A'),
                cert.get('validTo', 'N/A'),
                cert.get('sslGrade', 'N/A'),
                cert.get('encryptionType', 'N/A'),
                cert.get('issuer', 'N/A'),
                cert.get('country', 'N/A'),
                cert.get('status', 'N/A'),
                cert.get('vulnerabilityCount', 0)
            ])
    
    def _csv_row(self, row):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(row)
        return output.getvalue()
```

### Frontend Modal and Download Logic

```tsx
// DownloadModal.tsx
interface DownloadModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentPageData: ScanEntry[];
    activeFilter: { type: string; value?: string };
}

const handleDownloadThisPage = () => {
    // Generate CSV client-side
    const csv = generateCSV(currentPageData);
    downloadBlob(csv, 'certificates-page.csv', 'text/csv');
};

const handleDownloadAll = async () => {
    // Trigger backend download with current filters
    const params = new URLSearchParams();
    if (activeFilter.type === 'active') params.append('status', 'VALID');
    if (activeFilter.type === 'ca') params.append('issuer', activeFilter.value);
    // ... map other filters
    
    window.location.href = `/api/certificates/download/?${params}`;
};
```

This approach ensures:
- No memory issues with millions of records
- Streaming response starts immediately
- Client downloads progressively
- Filters are respected

---

## 29. Notification System - Suggestions and Implementation

### What to Fetch and Display in Notifications

The notification system should provide **real-time alerts** derived from database queries, helping users stay informed about critical certificate issues without manually checking.

### Suggested Notification Types

| Type | Priority | Description | DB Query |
|------|----------|-------------|----------|
| **Expiring in 1-2 Days** | 🔴 Critical | Certs expiring within 48 hours | `parsed.validity.end` between now and +2 days |
| **Expiring in 7 Days** | 🟠 High | Certs expiring within a week | `parsed.validity.end` between now and +7 days |
| **Critical Vulnerabilities** | 🔴 Critical | Certs with `zlint.errors_present: true` | `zlint.errors_present: true` |
| **Weak Encryption** | 🟠 High | RSA < 2048 or deprecated algorithms | `rsa_public_key.length < 2048` |
| **Newly Expired** | 🔴 Critical | Certs expired in last 24 hours | `parsed.validity.end` between -24h and now |
| **Recently Scanned Issues** | 🟡 Medium | New issues found in recent scans | New records with vulnerabilities |

### API Design: `/api/notifications`

#### Response Structure

```json
{
    "notifications": [
        {
            "id": "expiring-1-2-days",
            "type": "critical",
            "category": "expiring",
            "title": "5 certificates expiring in 1-2 days",
            "description": "Immediate attention required",
            "count": 5,
            "filterParams": {
                "status": "EXPIRING_SOON",
                "days": 2
            },
            "timestamp": "2026-01-13T16:42:50Z",
            "read": false
        },
        {
            "id": "vulnerabilities",
            "type": "error",
            "category": "security",
            "title": "12 certificates with vulnerabilities",
            "description": "ZLint detected issues",
            "count": 12,
            "filterParams": {
                "has_vulnerabilities": true
            },
            "timestamp": "2026-01-13T15:30:00Z",
            "read": false
        }
    ],
    "unreadCount": 4,
    "totalCount": 6
}
```

### Database Queries for Notifications

#### 1. Certificates Expiring in 1-2 Days

```python
from datetime import datetime, timezone, timedelta

now = datetime.now(timezone.utc)
two_days = now + timedelta(days=2)

expiring_critical = collection.count_documents({
    'parsed.validity.end': {
        '$gte': now.isoformat(),
        '$lte': two_days.isoformat()
    }
})
```

#### 2. Certificates Expiring in 7 Days

```python
seven_days = now + timedelta(days=7)
expiring_soon = collection.count_documents({
    'parsed.validity.end': {
        '$gte': now.isoformat(),
        '$lte': seven_days.isoformat()
    }
})
```

#### 3. Certificates with Vulnerabilities

```python
vulnerable = collection.count_documents({
    'zlint.errors_present': True,
    'parsed.validity.end': {'$gt': now.isoformat()}  # Still active
})
```

#### 4. Weak Encryption (RSA < 2048)

```python
weak_rsa = collection.count_documents({
    'parsed.subject_key_info.key_algorithm.name': 'RSA',
    'parsed.subject_key_info.rsa_public_key.length': {'$lt': 2048}
})
```

#### 5. Newly Expired (Last 24 Hours)

```python
yesterday = now - timedelta(days=1)
newly_expired = collection.count_documents({
    'parsed.validity.end': {
        '$gte': yesterday.isoformat(),
        '$lt': now.isoformat()
    }
})
```

### Notification Features to Implement

| Feature | Description |
|---------|-------------|
| **Badge Count** | Show unread notification count on bell icon |
| **Click Action** | Filter table to show related certificates |
| **Mark Read** | Track read status (localStorage or DB) |
| **Mark All Read** | Clear all notification badges |
| **Remove/Dismiss** | Delete individual notifications |
| **View All** | Expand to show full notification list |
| **Auto-Refresh** | Poll for new notifications every 5 minutes |

### Suggested Implementation Approach

1. **Backend Endpoint**: `/api/notifications` - Aggregate counts from DB
2. **No Persistence Needed**: Derive notifications from real-time certificate data
3. **Read Status**: Store in localStorage (simple) or user preferences table (multi-device)
4. **Efficient Queries**: Use indexed fields (`parsed.validity.end`, `zlint.errors_present`)
5. **Caching**: Cache notification counts for 1-2 minutes to reduce DB load

### Frontend Integration

```tsx
// On notification click
const handleNotificationClick = (notif: Notification) => {
    // Apply filter based on notification type
    if (notif.category === 'expiring') {
        handleCardClick('expiringSoon', { days: notif.filterParams.days });
    } else if (notif.category === 'security') {
        handleCardClick('vulnerabilities');
    }
    // Mark as read
    markNotificationRead(notif.id);
    // Close dropdown
    setShowNotifications(false);
};
```

### Performance Considerations

- **Index Required**: Ensure `parsed.validity.end` is indexed for fast expiring queries
- **Batch Queries**: Fetch all notification counts in single API call
- **Aggregation Pipeline**: Use MongoDB aggregation for efficient counting
- **Limit Queries**: Cap at 1000 documents for count accuracy

### Sample Aggregation Pipeline

```python
pipeline = [
    {'$facet': {
        'expiring_2_days': [
            {'$match': {'parsed.validity.end': {'$gte': now, '$lte': plus_2_days}}},
            {'$count': 'count'}
        ],
        'expiring_7_days': [
            {'$match': {'parsed.validity.end': {'$gte': now, '$lte': plus_7_days}}},
            {'$count': 'count'}
        ],
        'vulnerabilities': [
            {'$match': {'zlint.errors_present': True, 'parsed.validity.end': {'$gt': now}}},
            {'$count': 'count'}
        ]
    }}
]
```

This approach provides real-time, actionable notifications based on actual certificate data.
