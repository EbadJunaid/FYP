# CA Analytics Page Design

## Overview
The CA (Certificate Authority) Analytics page provides insights into certificate issuers, their distribution, trustworthiness, and signing patterns across the certificate database.

---

## Key CA-Related Fields (from 1.json)

| Field Path | Description |
|------------|-------------|
| `parsed.issuer.organization[]` | CA organization name (e.g., "Let's Encrypt") |
| `parsed.issuer.common_name[]` | CA common name (e.g., "R12") |
| `parsed.issuer.country[]` | CA country code (e.g., "US") |
| `parsed.issuer_dn` | Full issuer distinguished name |
| `parsed.validation_level` | Certificate type: DV, OV, EV |
| `parsed.signature.self_signed` | Whether certificate is self-signed |
| `parsed.signature_algorithm.name` | Algorithm used by CA (e.g., "SHA256-RSA") |
| `parsed.extensions.basic_constraints.is_ca` | Whether certificate is a CA certificate |

---

## Page Components

### 1. Metric Cards Row (4 Cards)

| Card | Metric | Info Tooltip | Click Action |
|------|--------|--------------|--------------|
| **Total CAs** | Count of unique issuer organizations | "Number of unique Certificate Authorities issuing certificates in your ecosystem" | Filter table to show all |
| **Top CA** | Name and % of most common CA | "The most prevalent CA by certificate count" | Filter table to top CA |
| **Self-Signed Certs** | Count of self-signed certificates | "Certificates signed by themselves rather than a trusted CA - may indicate development or internal certs" | Filter table to self-signed |
| **CA Countries** | Count of unique CA countries | "Geographic distribution of Certificate Authorities" | No filter |

---

### 2. Charts Section (2 Charts)

#### Chart 1: CA Market Share (Horizontal Bar Chart)
- **Type**: Horizontal bar chart
- **Data**: Top 10 CAs by certificate count
- **Features**:
  - Clickable bars to filter table
  - Percentage labels
  - "Others" category for remaining CAs
- **Colors**: Gradient from primary-blue to accent-purple

#### Chart 2: CA Trust Distribution (Pie/Donut Chart)
- **Type**: Donut chart
- **Segments**:
  - **Trusted CAs**: Known major CAs (Let's Encrypt, DigiCert, Comodo, etc.)
  - **Enterprise CAs**: Internal/private CAs
  - **Self-Signed**: No CA involvement
  - **Unknown**: Unrecognized issuers
- **Clickable**: Each segment filters the table

---

### 3. Analysis Cards Section (2 Cards)

#### Card 1: Validation Level Distribution
- **Type**: Stacked bar or segmented bar
- **Segments**: DV, OV, EV counts with percentages
- **Purpose**: Shows certificate validation levels issued by CAs
- **Clickable**: Filter by validation level

#### Card 2: CA Signing Algorithm Distribution
- **Type**: Pie chart or bar chart
- **Data**: Count by signature algorithm (SHA256-RSA, SHA384-RSA, etc.)
- **Purpose**: Security posture based on signing algorithms
- **Highlight**: Weak algorithms (SHA-1, MD5) in red

---

### 4. CA Issuance Trends (Line Chart)
- **Type**: Line chart with multiple lines
- **X-Axis**: Time (months)
- **Y-Axis**: Certificate count
- **Lines**: Top 5 CAs over time
- **Purpose**: Track CA popularity changes over time
- **Features**: 
  - Clickable legend to toggle CAs
  - Interactive tooltips

---

### 5. CA Details Table
- **Columns**:
  | Column | Description |
  |--------|-------------|
  | CA Name | Issuer organization |
  | Country | CA country |
  | Certificates | Count issued |
  | Market Share | Percentage |
  | Validation Types | DV/OV/EV breakdown |
  | Algorithms | Signature algorithms used |
  | Avg Validity | Average certificate validity period |

- **Features**:
  - Sortable columns
  - Pagination (10 per page)
  - Export/Download option
  - Click row to filter certificate table

---

### 6. Certificates Table (Filtered)
- **Standard DataTable** showing certificates filtered by selected CA
- **Filter indicators**: Show active filter (CA name, self-signed, etc.)
- **Clear filter button** to reset

---

## Filter Flow
1. User clicks metric card → filters to that category
2. User clicks chart segment/bar → filters to that CA/type
3. Reset to "All" clears filter
4. Table scrolls into view on filter change

---

## API Endpoints Required

| Endpoint | Purpose |
|----------|---------|
| `GET /api/ca-stats/` | Metric card data (counts, top CA) |
| `GET /api/ca-distribution/` | Bar chart data (top 10 CAs) |
| `GET /api/ca-trends/` | Line chart data (CA issuance over time) |
| `GET /api/certificates/?issuer=X` | Filtered certificates by CA |

---

## Backend Aggregation Queries

```python
# Top CAs aggregation
pipeline = [
    {"$unwind": "$parsed.issuer.organization"},
    {"$group": {"_id": "$parsed.issuer.organization", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}},
    {"$limit": 10}
]

# Self-signed count
{"parsed.signature.self_signed": True}

# Validation level distribution
pipeline = [
    {"$group": {"_id": "$parsed.validation_level", "count": {"$sum": 1}}}
]

# CA country distribution
pipeline = [
    {"$unwind": "$parsed.issuer.country"},
    {"$group": {"_id": "$parsed.issuer.country", "count": {"$sum": 1}}},
    {"$sort": {"count": -1}}
]
```

---

## Caching Strategy
- CA stats: 5 min TTL (relatively stable)
- CA distribution: 10 min TTL
- CA trends: 15 min TTL (historical)
