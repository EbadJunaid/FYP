# SAN Analytics Page Design

## Overview
The **SAN Analytics** (Subject Alternative Name Analytics) page analyzes the domains and hostnames protected by each SSL certificate. SAN entries are crucial for understanding certificate coverage, identifying multi-domain certificates, wildcard usage patterns, and potential security misconfigurations.

---

## Data Source (from `1.json`)
```json
"extensions": {
  "subject_alt_name": {
    "dns_names": ["onlinebookshop.pk", "www.onlinebookshop.pk"]
  }
},
"names": ["onlinebookshop.pk", "www.onlinebookshop.pk"]
```

---

## Metric Cards (4 Cards)

| Card | Metric | Data Source | Click Action |
|------|--------|-------------|--------------|
| **Total SANs** | Count of all SAN entries across all certs | `SUM(parsed.names.length)` | Filter: Show all certs |
| **Avg SANs per Cert** | Average domains per certificate | `AVG(parsed.names.length)` | Filter: Show certs with avg SANs |
| **Wildcard Certs** | Certs with `*.domain` entries | `COUNT WHERE names CONTAINS '*'` | Filter: Wildcard certs only |
| **Multi-Domain Certs** | Certs with 5+ SANs (high coverage) | `COUNT WHERE names.length >= 5` | Filter: Multi-domain certs |

---

## Charts & Visualizations

### 1. **SAN Distribution Histogram** (Bar Chart)
- **Purpose**: Show how many SANs certificates typically have
- **X-Axis**: SAN count buckets (1, 2-3, 4-5, 6-10, 11-20, 21-50, 50+)
- **Y-Axis**: Number of certificates
- **Interaction**: Click bar → filter table by SAN count range
- **Insight**: Identifies if your ecosystem uses single-domain or multi-domain certs

### 2. **Wildcard vs Standard SANs** (Pie Chart)
- **Purpose**: Compare wildcard (`*.domain`) vs explicit subdomain usage
- **Segments**: 
  - Wildcard SANs (e.g., `*.example.com`)
  - Standard SANs (e.g., `www.example.com`)
- **Interaction**: Click segment → filter table
- **Insight**: Wildcard overuse can indicate lazy security practices

### 3. **Top TLDs by SAN Count** (Horizontal Bar Chart)
- **Purpose**: Analyze domain extensions (.com, .pk, .org, etc.)
- **Data**: Extract TLD from each SAN entry and count
- **Display**: Top 10 TLDs sorted by occurrence
- **Interaction**: Click bar → filter certs by TLD
- **Insight**: Geographic and organizational distribution of protected domains

### 4. **SAN Name Patterns Analysis** (Table/Heatmap)
- **Purpose**: Identify common subdomain patterns
- **Categories**:
  - `www.*` prefixes
  - `mail.*` / `smtp.*` (email servers)
  - `api.*` / `dev.*` / `staging.*` (development)
  - `cdn.*` / `static.*` (content delivery)
  - `admin.*` / `portal.*` (internal)
- **Insight**: Understand certificate usage across infrastructure types

### 5. **Issuer × SAN Count Matrix** (Heatmap)
- **Purpose**: Which CAs issue certs with many SANs
- **Rows**: Top 10 CAs
- **Columns**: SAN count buckets (1, 2-5, 6-10, 11+)
- **Cell Value**: Certificate count
- **Interaction**: Click cell → filter by CA + SAN range
- **Insight**: Some CAs may specialize in multi-domain certs

---

## Unique Analysis Ideas

### A. **Domain Overlap Detection** 🔍
- Flag certificates where the same domain appears in multiple certs (potential misconfiguration)
- Show count of "overlapping" domains
- Helps identify certificate sprawl

### B. **www vs non-www Coverage** ✓
- Count certs that have both `domain.com` AND `www.domain.com`
- Count certs missing the counterpart
- Insight: Best practice is to include both

### C. **Subdomain Depth Analysis** 📊
- Analyze subdomain levels: `a.example.com` (depth 1), `b.a.example.com` (depth 2)
- Most certs should have depth 0-1
- Deep nesting may indicate internal/test certs

### D. **SAN Entry Security Audit** ⚠️
- Flag potentially suspicious SAN patterns:
  - Internal hostnames (localhost, *.local, *.internal)
  - IP addresses in SANs (less common for public certs)
  - Very long domain names (typosquatting indicator)

---

## Backend API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/san-stats/` | GET | Returns metric card data |
| `/api/san-distribution/` | GET | Returns SAN count histogram data |
| `/api/san-patterns/` | GET | Returns subdomain pattern analysis |
| `/api/san-tld-breakdown/` | GET | Returns TLD distribution |

---

## Aggregation Queries (MongoDB)

### SAN Stats (for metric cards)
```javascript
db.certificates.aggregate([
  {
    $project: {
      sanCount: { $size: { $ifNull: ["$parsed.names", []] } },
      hasWildcard: { $gt: [{ $size: { $filter: { input: { $ifNull: ["$parsed.names", []] }, cond: { $regexMatch: { input: "$$this", regex: /^\*\./ } } } } }, 0] }
    }
  },
  {
    $group: {
      _id: null,
      totalSans: { $sum: "$sanCount" },
      avgSansPerCert: { $avg: "$sanCount" },
      wildcardCerts: { $sum: { $cond: ["$hasWildcard", 1, 0] } },
      multiDomainCerts: { $sum: { $cond: [{ $gte: ["$sanCount", 5] }, 1, 0] } },
      totalCerts: { $sum: 1 }
    }
  }
])
```

### SAN Distribution (histogram)
```javascript
db.certificates.aggregate([
  { $project: { sanCount: { $size: { $ifNull: ["$parsed.names", []] } } } },
  {
    $bucket: {
      groupBy: "$sanCount",
      boundaries: [1, 2, 4, 6, 11, 21, 51, 1000],
      default: "50+",
      output: { count: { $sum: 1 } }
    }
  }
])
```

---

## Table Columns
When filtering the table, display these columns:

| Column | Data Source |
|--------|-------------|
| Domain | `domain` (primary domain) |
| SAN Count | `parsed.names.length` |
| SANs Preview | First 3 SANs with `+N more` |
| Issuer | `parsed.issuer.organization` |
| Wildcard | Yes/No indicator |
| Expiry | `parsed.validity.end` |
| Status | `VALID` / `EXPIRED` / `EXPIRING_SOON` |

---

## Caching Strategy
| Data | TTL | Key Pattern |
|------|-----|-------------|
| SAN Stats | 10 min | `san_stats` |
| SAN Distribution | 10 min | `san_distribution` |
| SAN Patterns | 15 min | `san_patterns` |
| SAN TLD Breakdown | 15 min | `san_tld` |

---

## Frontend Components Structure
```
SAN Analytics Page
├── Header ("SAN Analytics", subtitle)
├── Metric Cards Row (4 cards)
│   ├── Total SANs
│   ├── Avg SANs per Cert
│   ├── Wildcard Certs
│   └── Multi-Domain Certs
├── Charts Row 1 (2 columns)
│   ├── SAN Distribution Histogram
│   └── Wildcard vs Standard Pie
├── Charts Row 2 (2 columns)
│   ├── Top TLDs Bar Chart
│   └── Issuer × SAN Count Heatmap
├── SAN Patterns Table (subdomain types breakdown)
└── Certificates Table (filtered by clicks)
    └── DownloadModal
```

---

## Click Interactions Flow
| Element Clicked | Filter Applied | Table Title |
|-----------------|----------------|-------------|
| Total SANs card | None | All Certificates |
| Wildcard card | `has_wildcard=true` | Wildcard Certificates |
| Multi-Domain card | `min_sans=5` | Multi-Domain Certificates |
| Histogram bar | `san_count_min` & `san_count_max` | Certs with X-Y SANs |
| Pie segment | `san_type=wildcard` or `standard` | Wildcard/Standard SANs |
| TLD bar | `tld=.com` | Certificates with .com TLD |
| Heatmap cell | `issuer=X` & `san_range=Y` | X Certs with Y SANs |

---

## State Restoration
- Save: `filter`, `filterValue`, `page`, `scrollY`
- Key: `san-analytics-state`
- Restore on mount, save on row click
