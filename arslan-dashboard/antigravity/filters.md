# SSL Guardian - Global Filters System

## Overview

The global filters system allows users to filter dashboard data across **all cards** (except Global Health) and the **table**. When filters are applied, all metrics, aggregations, and table data are recomputed based on the filtered subset of certificates.

---

## Architecture

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| State Management | Extend `DashboardContext` | Industry practice: Keep related dashboard state together, avoid prop drilling |
| Backend Pattern | Base filtered getter | DRY principle: Single source of filtered data, reusable across all endpoints |
| Filter Combination | Intersection (AND) | Multiple filters narrow results (country=US AND status=VALID) |
| Card Click Behavior | Intersection with filters | Clicking "Active" after filter=US shows US + Active certificates |

---

## Filter Types

### 1. Date Range Filter

**Logic:** Overlap check - certificates valid at ANY point during the selected range.

```
Query: validFrom <= endDate AND validTo >= startDate
```

**Inclusive boundaries:** If startDate=2026-01-14, certificates with validFrom=2026-01-14 are included.

**Example:**
```
Date Range: Jan 14, 2026 - Jan 20, 2026
Certificate A: validFrom=Jan 10, validTo=Jan 18 → INCLUDED (overlaps)
Certificate B: validFrom=Jan 21, validTo=Jan 30 → EXCLUDED (no overlap)
Certificate C: validFrom=Jan 14, validTo=Jan 14 → INCLUDED (exact match)
```

**Backend Query:**
```python
match_filter = {
    'parsed.validity.start': {'$lte': end_date},
    'parsed.validity.end': {'$gte': start_date}
}
```

---

### 2. Country Filter

**Logic:** Filter by certificate's subject country (derived from TLD or explicit field).

**Backend Query:**
```python
match_filter = {'derived.country': {'$in': selected_countries}}
```

---

### 3. Certificate Issuer Filter

**Logic:** Filter by issuing CA organization.

**Backend Query:**
```python
match_filter = {'parsed.issuer.organization': {'$in': selected_issuers}}
```

---

### 4. SSL Grade Filter

**Logic:** Filter by calculated SSL grade.

**Backend Query:**
```python
match_filter = {'grade': {'$in': selected_grades}}
```

---

### 5. Certificate Status Filter

**Options:** Valid, Expired, Expiring Soon, Weak

**Backend Query:**
```python
now = datetime.now(timezone.utc)
if 'VALID' in statuses:
    match_filter['parsed.validity.end'] = {'$gt': now}
if 'EXPIRED' in statuses:
    match_filter['parsed.validity.end'] = {'$lte': now}
# etc.
```

---

### 6. Validation Level Filter

**Options:** DV (Domain Validation), OV (Organization Validation), EV (Extended Validation)

**Backend Query:**
```python
match_filter = {'validation_level': {'$in': selected_levels}}
```

---

## Combined Filters

When multiple filters are applied, they are combined with **AND** logic:

```python
combined_filter = {
    '$and': [
        date_filter,
        country_filter,
        issuer_filter,
        # ... etc
    ]
}
```

**Example:**
- Date Range: Jan 14-20
- Country: US
- Status: Valid

Result: Certificates that are (valid during Jan 14-20) AND (from US) AND (currently valid)

---

## Data Flow

### Without Filters (Default)
```
Dashboard Load
    └─▶ Fetch all metrics, cards, table data
        └─▶ Display full dataset
```

### With Filters Applied
```
User applies filter (e.g., Country=US)
    └─▶ DashboardContext updates globalFilters state
        └─▶ All card components re-fetch with filter params
            └─▶ Backend applies filter to aggregations
                └─▶ Cards display filtered metrics
        └─▶ Table re-fetches with filter params
            └─▶ Shows filtered certificates with pagination
```

### Card Click After Filter
```
Filter active: Country=US
User clicks "Active Certificates" card
    └─▶ Table shows: Country=US AND Status=VALID
        └─▶ (Filter + Card criteria = Intersection)
```

---

## Backend Implementation

### Base Filtered Getter

A single method that builds the MongoDB `$match` filter from query params:

```python
# models.py
@classmethod
def build_filter_query(cls, 
    start_date=None, end_date=None,
    countries=None, issuers=None,
    grades=None, statuses=None,
    validation_levels=None
) -> Dict:
    """Build MongoDB $match filter from query params"""
    filters = []
    
    # Date range (overlap check)
    if start_date and end_date:
        filters.append({
            'parsed.validity.start': {'$lte': end_date},
            'parsed.validity.end': {'$gte': start_date}
        })
    
    # Country
    if countries:
        filters.append({'derived.country': {'$in': countries}})
    
    # Issuer
    if issuers:
        filters.append({'parsed.issuer.organization': {'$elemMatch': {'$in': issuers}}})
    
    # ... etc for other filters
    
    return {'$and': filters} if filters else {}
```

### Usage in Endpoints

All endpoints use the same base filter:

```python
# controllers.py
def get_metrics(start_date=None, end_date=None, countries=None, ...):
    base_filter = CertificateModel.build_filter_query(
        start_date=start_date,
        end_date=end_date,
        countries=countries,
        ...
    )
    # Apply to aggregation
    pipeline = [{'$match': base_filter}, ...]
```

---

## Frontend Implementation

### DashboardContext Extension

```typescript
// DashboardContext.tsx
interface GlobalFilters {
    dateRange: { start: Date | null; end: Date | null };
    countries: string[];
    issuers: string[];
    grades: string[];
    statuses: string[];
    validationLevels: string[];
}

interface DashboardContextType {
    // ... existing
    globalFilters: GlobalFilters;
    setGlobalFilters: (filters: GlobalFilters) => void;
    hasActiveFilters: boolean;
}
```

### Filter Params Builder

```typescript
// utils/filterParams.ts
export function buildFilterQueryParams(filters: GlobalFilters): URLSearchParams {
    const params = new URLSearchParams();
    
    if (filters.dateRange.start) {
        params.set('start_date', filters.dateRange.start.toISOString());
    }
    if (filters.dateRange.end) {
        params.set('end_date', filters.dateRange.end.toISOString());
    }
    if (filters.countries.length) {
        params.set('countries', filters.countries.join(','));
    }
    // ... etc
    
    return params;
}
```

---

## Caching Strategy

### Client-Side (SWR)

Cache keys include filter params for uniqueness:

```typescript
// Without filters
key: '/api/metrics'

// With filters
key: '/api/metrics?start_date=2026-01-14&countries=US'
```

### Server-Side (Redis)

Cache keys include filter hash:

```python
# Without filters
key: 'ssl_guardian:metrics:{empty_hash}'

# With filters
key: 'ssl_guardian:metrics:{hash_of_filter_params}'
```

**TTL:** Same as existing (2-5 minutes depending on data type)

---

## UI Indicators

### Filter Icon Badge

When filters are active, show indicator on filter button:

```tsx
<button className="relative">
    <FilterIcon />
    {hasActiveFilters && (
        <span className="absolute -top-1 -right-1 w-2 h-2 bg-primary-blue rounded-full" />
    )}
</button>
```

### Active Filters Summary

Show small pills below cards or in header:

```tsx
{hasActiveFilters && (
    <div className="flex gap-2">
        {filters.countries.length > 0 && (
            <span className="text-xs bg-primary-blue/20 px-2 py-0.5 rounded">
                Country: {filters.countries.join(', ')}
            </span>
        )}
        {/* ... other active filters */}
    </div>
)}
```

---

## Reset Filters

Clears all filters and reverts to full unfiltered data:

```typescript
const resetFilters = () => {
    setGlobalFilters({
        dateRange: { start: null, end: null },
        countries: [],
        issuers: [],
        grades: [],
        statuses: [],
        validationLevels: [],
    });
    // Re-fetch all data without filters
    refreshData();
};
```

---

## Implementation Order

1. ✅ Create filters.md documentation
2. ⬜ Backend: Add `build_filter_query` to models.py
3. ⬜ Backend: Update all controllers to accept and use filters
4. ⬜ Frontend: Extend DashboardContext with globalFilters
5. ⬜ Frontend: Update FilterModal to use context
6. ⬜ Frontend: Pass filters to all API calls
7. ⬜ Frontend: Add filter indicator on button
8. ⬜ Test each filter type
