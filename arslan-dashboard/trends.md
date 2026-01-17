# Trends Analytics Page Design

## Overview
The Trends Analytics page focuses on **time-based analysis** of certificate data, showing how various metrics evolve over time. Unlike static analytics pages, this page emphasizes temporal patterns, rate of change, and predictive insights.

---

## Available Data Fields for Time-Based Analysis

Based on the certificate structure (`1.json`), the following fields are suitable for trend analysis:

| Field | Path | Trend Potential |
|-------|------|-----------------|
| Issuance Date | `parsed.validity.start` | Certificate issuance trends |
| Expiration Date | `parsed.validity.end` | Expiration forecasting |
| Validity Length | `parsed.validity.length` | Duration trends over time |
| Issuer/CA | `parsed.issuer.organization` | CA market share evolution |
| Signature Algorithm | `parsed.signature_algorithm.name` | Algorithm adoption trends |
| Key Size | `parsed.subject_key_info.rsa_public_key.length` | Key strength evolution |
| Validation Level | `parsed.validation_level` | DV/OV/EV trend shifts |
| SAN Count | `parsed.extensions.subject_alt_name.dns_names.length` | Multi-domain certificate trends |
| zlint Errors | `zlint.lints` | Compliance improvement over time |
| TLD Distribution | `domain` (extracted TLD) | Regional adoption trends |

---

## Proposed Metric Cards (4 Cards)

### 1. **Certificate Velocity**
- **Value**: Certificates issued in last 30 days
- **Trend Indicator**: % change vs previous 30 days (↑↓)
- **Tooltip**: "Rate of new certificate issuance. Higher velocity indicates active PKI environment."
- **Click Action**: Filter table by last 30 days issued

### 2. **Predicted Expirations (Next 30 Days)**
- **Value**: Count of certificates expiring soon
- **Trend Indicator**: Compared to previous month
- **Tooltip**: "Upcoming certificate expirations requiring renewal."
- **Click Action**: Filter by expiring in 30 days

### 3. **Algorithm Modernization Rate**
- **Value**: % of SHA256+ algorithms (modern)
- **Trend Indicator**: % point change over 6 months
- **Tooltip**: "Rate of adoption of modern cryptographic algorithms."
- **Click Action**: Filter by SHA256-RSA or newer

### 4. **Compliance Health Score**
- **Value**: % of certificates with 0 zlint errors
- **Trend Indicator**: Trend over last 3 months
- **Tooltip**: "Percentage of fully compliant certificates."
- **Click Action**: Filter by zero vulnerabilities

---

## Proposed Charts & Visualizations

### Row 1: Primary Time-Series Charts (Full Width Split)

#### 1. **Certificate Issuance Timeline** (Line Chart)
- **X-Axis**: Time (monthly/weekly granularity)
- **Y-Axis**: Number of certificates issued
- **Features**:
  - Toggle: Last 6 months / 1 year / 2 years
  - Hover: Show exact count per period
  - **Forecast Line**: Dotted line predicting next 3 months using linear regression
- **Click**: Filter table by selected month/week

#### 2. **Expiration Forecast Heatmap** (Calendar Heatmap)
- **Display**: Next 12 months, color-coded by expiration density
- **Colors**: Green (few) → Yellow (moderate) → Red (many expirations)
- **Click Action**: Click any month to filter certificates expiring that month
- **Unique Feature**: "Critical Days" highlighting (e.g., end of month clusters)

---

### Row 2: Algorithm & Security Evolution

#### 3. **Algorithm Adoption Timeline** (Stacked Area Chart)
- **Display**: Distribution of signature algorithms over time
- **Stacks**: SHA256-RSA, SHA384-RSA, ECDSA, SHA1-RSA (legacy), Others
- **Time Range**: Last 12 months by issuance date
- **Insight**: Shows migration from legacy to modern algorithms
- **Click**: Filter by specific algorithm at that time point

#### 4. **Key Size Evolution** (Line Chart with Milestones)
- **Y-Axis**: Average key size (RSA bits)
- **X-Axis**: Time (by issuance month)
- **Markers**: Highlight when 4096-bit adoption exceeded certain thresholds
- **Click**: Filter by key size at selected time

---

### Row 3: CA & Validation Trends

#### 5. **CA Market Share Over Time** (Animated Stacked Bar / Racing Bar)
- **Display**: Top 5 CAs market share evolution
- **Time Range**: Monthly snapshots over 12 months
- **Animated**: Optional "play" button to animate changes
- **Click**: Filter by CA at selected time

#### 6. **Validation Level Trends** (100% Stacked Area)
- **Stacks**: DV, OV, EV
- **X-Axis**: Time (monthly)
- **Insight**: Track shift towards DV certificates (Let's Encrypt effect)
- **Click**: Filter by validation level at time

---

### Row 4: Unique Analytical Features

#### 7. **Certificate Lifespan Distribution Over Time** (Violin / Box Plot Series)
- **Display**: For each month, show distribution of validity lengths
- **Insight**: Shows trend towards shorter certificate lifespans (90-day certs)
- **Highlight**: Draw attention to outliers (very long validity periods)

#### 8. **SAN Count Growth Trend** (Line + Histogram Combo)
- **Line**: Average SANs per certificate over time
- **Background Histogram**: Distribution of SAN counts
- **Insight**: Trend towards multi-domain certificates
- **Click**: Filter by time period

---

## Unique Feature Ideas

### 🔮 **Predictive Analytics Panel**
A collapsible section showing:
1. **Expiration Wave Forecast**: Predict when "waves" of expirations will occur
2. **Algorithm Sunset Predictions**: When legacy algorithms will reach <1%
3. **Renewal Rate Estimation**: Based on historical patterns

### 📊 **Trend Comparison Mode**
- Allow users to select TWO metrics and overlay them on the same chart
- Example: Compare "issuance rate" vs "expiration rate" to identify renewal gaps

### 📅 **Smart Alerts / Insights**
Auto-generated insights like:
- "37% increase in certificate issuance last month"
- "SHA-1 usage dropped below 1% for the first time"
- "Let's Encrypt overtook DigiCert in market share in March 2025"

### 🎯 **Cohort Analysis**
Group certificates by:
- **Issuance Quarter**: Compare Q1 2025 vs Q4 2024 cohorts
- **CA**: Compare Let's Encrypt vs DigiCert certificate characteristics
- **Validation Level**: Compare DV vs OV certificate trends

### ⏰ **Time Machine View**
Slider control to see "state of certificates" at any historical point:
- How many were active?
- What was the algorithm distribution?
- Which CAs were dominant?

---

## Data Table (Below Charts)

- **Title**: "Certificates by Time Period"
- **Quick Filters**: 
  - Issuance Date Range
  - Expiring Within (30/60/90 days)
  - Algorithm Type
- **Download**: Export with applied filters
- **Pagination**: Standard pagination with state restoration

---

## Suggested Implementation Priority

| Priority | Component | Complexity | Value |
|----------|-----------|------------|-------|
| 1 | Certificate Issuance Timeline | Medium | High |
| 2 | Expiration Forecast Chart | Medium | High |
| 3 | 4 Metric Cards | Low | Medium |
| 4 | Algorithm Adoption Timeline | Medium | High |
| 5 | CA Market Share Over Time | High | Medium |
| 6 | Validation Level Trends | Low | Medium |
| 7 | Predictive Analytics Panel | High | High |
| 8 | Time Machine View | Very High | Medium |

---

## API Endpoints Needed

```
GET /api/trends/issuance-timeline?period=monthly&months=12
GET /api/trends/expiration-forecast?months=12
GET /api/trends/algorithm-adoption?months=12
GET /api/trends/ca-market-share?months=12
GET /api/trends/validation-levels?months=12
GET /api/trends/key-size-evolution?months=12
GET /api/trends/san-count-trend?months=12
GET /api/trends/compliance-score?months=6
```

---

## UI Layout Sketch

```
┌─────────────────────────────────────────────────────────────────────┐
│ Trends Analytics                                                     │
│ Track certificate ecosystem changes over time                        │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐                    │
│ │ Velocity │ │Expiring │ │ Modern  │ │Compliance│                   │
│ │  +15% ↑  │ │  1,234  │ │ Algo %  │ │ Score %  │                   │
│ │  30 days │ │ 30 days │ │  94.2%  │ │   87.3%  │                   │
│ └─────────┘ └─────────┘ └─────────┘ └─────────┘                    │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐ ┌─────────────────────────┐            │
│ │ Certificate Issuance    │ │ Expiration Forecast     │            │
│ │ Timeline (Line Chart)   │ │ (Calendar Heatmap)      │            │
│ │ [Monthly ▼] [12mo ▼]   │ │ ■■■ Jan Feb Mar Apr ... │            │
│ └─────────────────────────┘ └─────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────┐ ┌─────────────────────────┐            │
│ │ Algorithm Adoption      │ │ Validation Level Trends │            │
│ │ (Stacked Area)          │ │ (100% Stacked Area)     │            │
│ └─────────────────────────┘ └─────────────────────────┘            │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────┐│
│ │ Certificates Table                       [All▼][Wildcard][Std] ││
│ │ ... data table with filters ...          [Download]            ││
│ └─────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

---

## Summary

This Trends page provides **temporal intelligence** about the certificate ecosystem:
- **What's happening now?** → Velocity, Expiring Soon cards
- **How did we get here?** → Historical timeline charts
- **Where are we going?** → Forecast and prediction features
- **What changed?** → Algorithm and CA evolution charts

The unique features (Time Machine, Cohort Analysis, Smart Alerts) differentiate this from static analytics pages.
