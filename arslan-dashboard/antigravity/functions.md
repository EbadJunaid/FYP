# SSL Guardian Dashboard - Functions & Click Behavior Documentation

This document explains what happens when you click on different cards and elements on the SSL Guardian dashboard overview page. It covers which certificates are displayed in the table, the filtering logic, pagination behavior, and best practices for API/query design.

---

## Table of Contents
1. [Global Health Card Click](#1-global-health-card-click)
2. [Active Certificates Card Click](#2-active-certificates-card-click)
3. [Expiring Soon Card Click](#3-expiring-soon-card-click)
4. [Critical Vulnerabilities Card Click](#4-critical-vulnerabilities-card-click)
5. [Encryption Strength Distribution Card Click](#5-encryption-strength-distribution-card-click)
6. [CA Leaderboard Card Click](#6-ca-leaderboard-card-click)
7. [Geographic Distribution Card Click](#7-geographic-distribution-card-click)
8. [Validity Trend Chart Click](#8-validity-trend-chart-click)
9. [Best Practices for APIs & Queries](#9-best-practices-for-apis--queries)

---

## 1. Global Health Card Click

### What Happens?
When you click on the **Global Health** card, the table displays **ALL certificates** in the database with proper pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'globalHealth':
    await fetchCertificates({});  // No filter = all certificates
    break;
```

### Certificates Displayed
| Metric | Count (Example) |
|--------|-----------------|
| Total Displayed | 5810 |
| Filter Applied | None |
| Pagination | Yes (25 per page) |

### API Query
```python
# Backend: models.py - get_all()
query = {}  # Empty query = all documents
cursor = cls.collection.find(query).skip(skip).limit(page_size)
```

### Why All Certificates?
The Global Health score represents the overall health of **all** certificates in your system. Therefore, clicking it should show the complete dataset to allow full analysis. The table uses pagination (e.g., 25 per page) to avoid loading all 5810 certificates at once.

---

## 2. Active Certificates Card Click

### What Happens?
When you click on the **Active Certificates** card, the table displays **ONLY valid/active certificates** (not expired) with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'activeCertificates':
    await fetchCertificates({ status: 'VALID' });
    break;
```

### Certificates Displayed
| Metric | Count (Example) |
|--------|-----------------|
| Total Active | 5665 |
| Filter Applied | `status = 'VALID'` |
| Includes Expired | ❌ No |
| Includes Expiring Soon | ✅ Yes (they are still active) |
| Pagination | Yes (25 per page) |

### API Query
```python
# Backend filter logic
now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
if status == 'VALID':
    query['parsed.validity.end'] = {'$gt': now}  # Not expired
```

### Important Clarification
- **Active** = Certificate is currently valid (end date > now)
- **Expiring Soon** certificates ARE included because they are still active (not yet expired)
- **Expired** certificates are excluded

---

## 3. Expiring Soon Card Click

### What Happens?
When you click on the **Expiring Soon** card, the table displays **ONLY certificates expiring within the next 30 days** with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'expiringSoon':
    await fetchCertificates({ status: 'EXPIRING_SOON' });
    break;
```

### Certificates Displayed
| Metric | Count (Example) |
|--------|-----------------|
| Total Expiring Soon | 2001 |
| Filter Applied | `status = 'EXPIRING_SOON'` |
| Time Window | Now to Now + 30 days |
| Pagination | Yes (25 per page) |

### API Query
```python
# Backend filter logic
now = cls.get_current_time_iso()
now_plus_30 = (datetime.now(timezone.utc) + timedelta(days=30)).strftime('%Y-%m-%dT%H:%M:%SZ')

if status == 'EXPIRING_SOON':
    query['parsed.validity.end'] = {'$gte': now, '$lte': now_plus_30}
```

### What This Means
- Shows **ALL 2001** certificates expiring soon (with pagination)
- Does NOT mix with expired or valid certificates outside the 30-day window
- Each page shows 25 certificates until all 2001 are accessible through pagination

---

## 4. Critical Vulnerabilities Card Click

### What Happens?
When you click on the **Critical Vulnerabilities** card, the table displays **ONLY certificates that have at least one zlint error** with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'criticalVulnerabilities':
    await fetchCertificates({ hasVulnerabilities: true });
    break;
```

### Certificates Displayed
| Metric | Count (Example) |
|--------|-----------------|
| Total with Errors | ~2424 |
| Filter Applied | `hasVulnerabilities = true` |
| Includes Warnings-Only | ❌ No (errors only) |
| Pagination | Yes (25 per page) |

### API Query Logic
```python
# Backend should filter for certificates with zlint errors
pipeline = [
    {'$match': {'zlint.lints': {'$exists': True, '$ne': {}}}},
    {'$project': {'lints_array': {'$objectToArray': '$zlint.lints'}}},
    {'$unwind': '$lints_array'},
    {'$match': {'lints_array.v.result': 'error'}},
    {'$group': {'_id': '$_id'}}
]
```

### Important Notes
- Shows **ONLY** certificates with critical vulnerabilities (errors)
- Does NOT mix with clean certificates or warnings-only certificates
- The filter specifically checks for `result: 'error'` in zlint.lints

---

## 5. Encryption Strength Distribution Card Click

### What Happens?
When you click on a specific algorithm type (e.g., **RSA 2048**) in the Encryption Strength Distribution card, the table displays **ONLY certificates using that specific algorithm** with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'encryption':
    const encData = item as EncryptionStrength;
    await fetchCertificates({ encryptionType: encData.name });
    break;
```

### Certificates Displayed
| Algorithm Clicked | Filter Applied | Example Count |
|-------------------|----------------|---------------|
| RSA 2048 | `encryptionType = 'RSA 2048'` | ~4500 |
| RSA 4096 | `encryptionType = 'RSA 4096'` | ~800 |
| ECDSA 256 | `encryptionType = 'ECDSA 256'` | ~400 |
| ECDSA 384 | `encryptionType = 'ECDSA 384'` | ~110 |

### API Query
```python
# Backend filter for encryption type
if encryption_type:
    query['$and'] = [
        {'parsed.subject_key_info.key_algorithm.name': algo_name},
        # Optionally filter by key length too
    ]
```

### Important Notes
- Shows **ONLY** certificates with the clicked algorithm
- Does NOT mix with other algorithm types
- Full pagination through all matching certificates

---

## 6. CA Leaderboard Card Click

### What Happens?
When you click on a specific CA (e.g., **Let's Encrypt**) in the CA Leaderboard card, the table displays **ONLY certificates issued by that CA** with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'ca':
    const caData = item as CALeaderboardEntry;
    await fetchCertificates({ issuer: caData.name });
    break;
```

### Certificates Displayed
| CA Clicked | Filter Applied | Example Count |
|------------|----------------|---------------|
| Let's Encrypt | `issuer = "Let's Encrypt"` | ~2675 |
| Google Trust Services | `issuer = 'Google Trust...'` | ~1300 |
| DigiCert Inc. | `issuer = 'DigiCert Inc.'` | ~500 |

### API Query
```python
# Backend filter for issuer
if issuer:
    query['parsed.issuer.organization'] = {'$regex': issuer, '$options': 'i'}
```

### Important Notes
- Shows **ALL** certificates from the clicked CA (with pagination)
- Does NOT mix with certificates from other CAs
- Uses case-insensitive matching for flexibility

---

## 7. Geographic Distribution Card Click

### What Happens?
When you click on a specific country (e.g., **Pakistan**) in the Geographic Distribution card, the table displays **ONLY certificates registered in that country** with pagination.

### Current Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'geographic':
    const geoData = item as GeographicEntry;
    await fetchCertificates({ country: geoData.country });
    break;
```

### Certificates Displayed
| Country Clicked | Filter Applied | Derivation |
|-----------------|----------------|------------|
| Pakistan | `country = 'Pakistan'` | TLD `.pk` |
| United States | `country = 'United States'` | TLD `.com` |
| Germany | `country = 'Germany'` | TLD `.de` |

### API Query Logic
```python
# Backend must derive country from TLD, then filter
# The country is determined from domain TLD (e.g., .pk → Pakistan)
# Filter matches certificates with matching TLD-derived country
```

### Important Notes
- Shows **ALL** certificates from the clicked country (with pagination)
- Country is derived from domain TLD (e.g., example.pk → Pakistan)
- Does NOT mix with certificates from other countries

---

## 8. Validity Trend Chart Click

### What Happens?
When you click on a specific month in the Validity Trend chart (e.g., **March**), the table displays **ONLY certificates expiring in that specific month** with pagination.

### Recommended Implementation

**Frontend Flow:**
```typescript
// In DashboardContext.tsx
case 'validityTrend':
    const trendData = item as ValidityTrend;
    await fetchCertificates({ 
        expiringMonth: trendData.month,
        expiringYear: trendData.year 
    });
    break;
```

### Certificates Displayed
| Month Clicked | Filter Applied | Example Count |
|---------------|----------------|---------------|
| Jan 2026 | `validity.end` between Jan 1 - Jan 31 | ~350 |
| Feb 2026 | `validity.end` between Feb 1 - Feb 28 | ~420 |
| Mar 2026 | `validity.end` between Mar 1 - Mar 31 | ~380 |

### API Query
```python
# Backend filter for specific month
from calendar import monthrange
_, days_in_month = monthrange(year, month)
start = datetime(year, month, 1)
end = datetime(year, month, days_in_month, 23, 59, 59)

query['parsed.validity.end'] = {'$gte': start_str, '$lte': end_str}
```

### Important Notes
- Shows **ONLY** certificates expiring in the clicked month
- Uses calendar month boundaries (1st to last day)
- Full pagination through all matching certificates

---

## 9. Best Practices for APIs & Queries

### Pagination

**Always paginate** large result sets to avoid:
- Memory overload on server
- Slow network responses
- Browser performance issues

```python
# Good Practice
cursor = collection.find(query).skip(skip).limit(page_size)

# Bad Practice (never do this)
all_docs = list(collection.find(query))  # Loads everything into memory!
```

### Database Indexes

Create indexes on frequently filtered fields for faster queries:

```python
# Recommended indexes
collection.create_index([('parsed.validity.end', 1)])
collection.create_index([('parsed.issuer.organization', 1)])
collection.create_index([('parsed.subject_key_info.key_algorithm.name', 1)])
collection.create_index([('zlint.lints', 1)])
```

### Error Handling

Always wrap API calls in try-catch blocks:

```typescript
// Frontend
try {
    const result = await apiClient.getCertificates(filters);
    setData(result.certificates);
} catch (error) {
    console.error('Failed to fetch certificates:', error);
    setError('Unable to load certificates');
}
```

```python
# Backend
try:
    result = CertificateModel.get_all(**filters)
    return json_response(result)
except Exception as e:
    return json_response({'error': str(e)}, status=500)
```

### Efficient Aggregation

For counting or grouping, use MongoDB aggregation pipelines instead of fetching all documents:

```python
# Good Practice
pipeline = [
    {'$match': {'zlint.lints': {'$exists': True}}},
    {'$group': {'_id': '$_id'}},
    {'$count': 'total'}
]
result = collection.aggregate(pipeline)

# Bad Practice
all_docs = collection.find({})
count = sum(1 for doc in all_docs if 'zlint' in doc)  # Inefficient!
```

### Filter Specificity

Always apply specific filters based on user clicks:

| Click Action | Filter | Result |
|--------------|--------|--------|
| Global Health | None | All 5810 certificates |
| Active Certs | status=VALID | Only 5665 active |
| Expiring Soon | status=EXPIRING_SOON | Only 2001 expiring |
| Vulnerabilities | hasVulnerabilities=true | Only ~2424 with errors |
| RSA 2048 | encryptionType=RSA 2048 | Only that algorithm |
| Let's Encrypt | issuer=Let's Encrypt | Only that CA |
| Pakistan | country=Pakistan | Only that country |
| March 2026 | month=3, year=2026 | Only that month |

---

## Summary Table

| Card/Element | Filter Type | Shows All Matching? | Pagination |
|--------------|-------------|---------------------|------------|
| Global Health | None | ✅ Yes (all 5810) | ✅ Yes |
| Active Certificates | status=VALID | ✅ Yes (all 5665) | ✅ Yes |
| Expiring Soon | status=EXPIRING_SOON | ✅ Yes (all 2001) | ✅ Yes |
| Critical Vulnerabilities | hasVulnerabilities=true | ✅ Yes | ✅ Yes |
| Encryption Type (e.g., RSA 2048) | encryptionType | ✅ Yes | ✅ Yes |
| CA (e.g., Let's Encrypt) | issuer | ✅ Yes | ✅ Yes |
| Country (e.g., Pakistan) | country | ✅ Yes | ✅ Yes |
| Validity Trend Month | expiringMonth/Year | ✅ Yes | ✅ Yes |

**Key Principle:** Every click filters to show **ONLY** the relevant certificates, with proper pagination to handle large datasets efficiently. No mixing of unrelated data.
