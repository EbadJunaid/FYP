# SSL Guardian API Documentation

This document describes all API endpoints for the SSL Guardian certificate analysis dashboard.

---

## Base URL

```
http://localhost:8000/api
```

---

## Endpoints

### 1. GET /api/certificates/

**Description:** Returns a paginated list of certificates with optional filters.

**HTTP Method:** `GET`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | int | No | Page number (default: 1) |
| `page_size` | int | No | Items per page (default: 10) |
| `status` | string | No | Filter by status: `VALID`, `EXPIRING_SOON`, `EXPIRED` |
| `country` | string | No | Filter by country (e.g., `Pakistan`, `United States`) |
| `issuer` | string | No | Filter by CA organization (e.g., `Google Trust Services`) |
| `search` | string | No | Search by domain or common name |
| `encryption_type` | string | No | Filter by encryption (e.g., `RSA 2048`, `ECDSA 256`) |
| `has_vulnerabilities` | boolean | No | `true` to filter only certificates with zlint errors |

**Example Request:**

```bash
# Get all certificates (page 1)
curl "http://localhost:8000/api/certificates/"

# Get active certificates (status=VALID)
curl "http://localhost:8000/api/certificates/?status=VALID&page=1&page_size=10"

# Get certificates with vulnerabilities
curl "http://localhost:8000/api/certificates/?has_vulnerabilities=true&page=1"

# Filter by encryption type
curl "http://localhost:8000/api/certificates/?encryption_type=RSA%202048"

# Filter by issuer
curl "http://localhost:8000/api/certificates/?issuer=Google%20Trust%20Services"
```

**Example Response:**

```json
{
  "certificates": [
    {
      "id": "676c8f5a1db4dc3b93d71d91",
      "domain": "example.pk",
      "commonName": "example.pk",
      "issuer": { "organization": ["Google Trust Services"], "country": ["US"] },
      "validity": { "start": "2025-10-20T05:43:00Z", "end": "2026-01-18T05:42:59Z" },
      "status": "VALID",
      "sslGrade": "A+",
      "encryption": "ECDSA 256 SHA256",
      "vulnerabilities": "0 Found",
      "country": "Pakistan"
    }
  ],
  "pagination": {
    "page": 1,
    "pageSize": 10,
    "total": 5810,
    "totalPages": 581
  }
}
```

**How to Test:**
- Browser: Navigate to `http://localhost:8000/api/certificates/`
- Postman: Create GET request with query params
- No authentication required

---

### 2. GET /api/certificates/{id}/

**Description:** Returns full details of a single certificate.

**HTTP Method:** `GET`

**Path Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `id` | string | Yes | MongoDB ObjectId of the certificate |

**Example Request:**

```bash
curl "http://localhost:8000/api/certificates/676c8f5a1db4dc3b93d71d91/"
```

**Example Response:**

```json
{
  "id": "676c8f5a1db4dc3b93d71d91",
  "domain": "1win-mobile.pk",
  "parsed": {
    "subject": { "common_name": ["1win-mobile.pk"] },
    "issuer": { "organization": ["Google Trust Services"], "country": ["US"] },
    "validity": { "start": "2025-10-20T05:43:00Z", "end": "2026-01-18T05:42:59Z" },
    "subject_key_info": { "key_algorithm": { "name": "ECDSA" } }
  },
  "zlint": { "lints": { "e_dnsname_not_valid_tld": { "result": "error" } } }
}
```

---

### 3. GET /api/metrics/

**Description:** Returns dashboard metrics including global health, active certs, expiring soon count, and vulnerabilities.

**HTTP Method:** `GET`

**Query Parameters:** None

**Example Request:**

```bash
curl "http://localhost:8000/api/metrics/"
```

**Example Response:**

```json
{
  "globalHealth": { "score": 77, "maxScore": 100, "status": "Good", "lastUpdated": "2026-01-12" },
  "activeCertificates": { "count": 5670, "change": 0 },
  "expiringSoon": { "count": 2041, "days": 30 },
  "criticalVulnerabilities": { "count": 2877, "new": 0 }
}
```

---

### 4. GET /api/encryption-strength/

**Description:** Returns encryption algorithm distribution for pie chart.

**HTTP Method:** `GET`

**Example Request:**

```bash
curl "http://localhost:8000/api/encryption-strength/"
```

**Example Response:**

```json
[
  { "id": "enc-0", "name": "ECDSA 256", "type": "Modern", "count": 5638, "percentage": 96.4, "color": "#10b981" },
  { "id": "enc-1", "name": "RSA 4096", "type": "Strong", "count": 105, "percentage": 1.8, "color": "#3b82f6" },
  { "id": "enc-2", "name": "RSA 2048", "type": "Standard", "count": 67, "percentage": 1.1, "color": "#3b82f6" }
]
```

---

### 5. GET /api/ca-distribution/

**Description:** Returns Certificate Authority distribution with counts and percentages.

**HTTP Method:** `GET`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max number of CAs to return (default: 10) |

**Example Request:**

```bash
curl "http://localhost:8000/api/ca-distribution/?limit=10"
```

**Example Response:**

```json
[
  { "id": "ca-0", "name": "Google Trust Services", "count": 5638, "percentage": 96.9, "color": "#10b981" },
  { "id": "ca-1", "name": "Let's Encrypt", "count": 105, "percentage": 1.8, "color": "#3b82f6" }
]
```

---

### 6. GET /api/geographic-distribution/

**Description:** Returns certificate distribution by country (from domain TLD).

**HTTP Method:** `GET`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `limit` | int | No | Max number of countries (default: 10) |

**Example Request:**

```bash
curl "http://localhost:8000/api/geographic-distribution/?limit=10"
```

**Example Response:**

```json
[
  { "country": "Pakistan", "count": 5810, "percentage": 100, "code": "PK" },
  { "country": "United States", "count": 0, "percentage": 0, "code": "US" }
]
```

---

### 7. GET /api/validity-trends/

**Description:** Returns certificate expiration trends by calendar month.

**HTTP Method:** `GET`

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `months` | int | No | Number of future months (default: 12) |

**Example Request:**

```bash
curl "http://localhost:8000/api/validity-trends/?months=18"
```

**Example Response:**

```json
[
  { "month": "Jan 2026", "expirations": 2041, "year": 2026, "monthNum": 1 },
  { "month": "Feb 2026", "expirations": 589, "year": 2026, "monthNum": 2 },
  { "month": "Mar 2026", "expirations": 421, "year": 2026, "monthNum": 3 }
]
```

---

### 8. GET /api/future-risk/

**Description:** Returns future risk assessment data.

**HTTP Method:** `GET`

**Example Response:**

```json
{
  "validPercentage": 62,
  "expiringPercentage": 35,
  "expiredPercentage": 3,
  "riskLevel": "medium"
}
```

---

### 9. GET /api/unique-filters/

**Description:** Returns unique values for filter dropdowns (statuses, issuers, countries).

**HTTP Method:** `GET`

**Example Response:**

```json
{
  "statuses": ["VALID", "EXPIRING_SOON", "EXPIRED"],
  "issuers": ["Google Trust Services", "Let's Encrypt", "DigiCert"],
  "countries": ["Pakistan", "United States", "Germany"]
}
```

---

## Testing

### Browser Testing

Open any endpoint URL directly in browser:
- `http://localhost:8000/api/certificates/?page=1`
- `http://localhost:8000/api/metrics/`

### Postman Testing

1. Create new request
2. Set method to GET
3. Enter URL with query params
4. No authentication headers needed
5. Click Send

### cURL Testing

```bash
# Test all endpoints
curl -X GET "http://localhost:8000/api/certificates/"
curl -X GET "http://localhost:8000/api/metrics/"
curl -X GET "http://localhost:8000/api/encryption-strength/"
curl -X GET "http://localhost:8000/api/ca-distribution/"
curl -X GET "http://localhost:8000/api/geographic-distribution/"
curl -X GET "http://localhost:8000/api/validity-trends/"
```

---

## Error Handling

All endpoints return errors in this format:

```json
{
  "error": "Error message description"
}
```

HTTP Status Codes:
- `200` - Success
- `404` - Not found
- `500` - Server error
