# SSL Guardian - Caching Strategy Documentation

## Table of Contents

1. [Overview](#1-overview)
2. [Client-Side Caching with SWR](#2-client-side-caching-with-swr)
3. [Server-Side Caching with Redis](#3-server-side-caching-with-redis)
4. [Hybrid Approach](#4-hybrid-approach)
5. [TTL (Time-To-Live) Strategy](#5-ttl-time-to-live-strategy)
6. [Cache Clearing Logic](#6-cache-clearing-logic)
7. [CDN/Edge Caching Analysis](#7-cdnedge-caching-analysis)
8. [Testing Caching is Working](#8-testing-caching-is-working)
9. [Implementation Checklist](#9-implementation-checklist)
10. [Redis Installation & Troubleshooting Guide](#10-redis-installation--troubleshooting-guide)
11. [Caching Behavior FAQ - Detailed Explanations](#11-caching-behavior-faq---detailed-explanations)
12. [Staleness Checking - How It Really Works](#12-staleness-checking---how-it-really-works)

---

## 1. Overview

### Why Caching?

With millions of SSL certificates in MongoDB, uncached queries can be expensive:

| Query Type | Without Cache | With Cache |
|------------|---------------|------------|
| Dashboard metrics | ~500-1000ms | ~5-10ms |
| Paginated list (page 1) | ~200-500ms | ~5-10ms |
| Aggregations (CA leaderboard) | ~1-2s | ~5-10ms |

### Caching Layers Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     USER BROWSER                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  SWR Cache (React State / Memory)                    │    │
│  │  • Stale-while-revalidate pattern                   │    │
│  │  • Per-key caching (page, filters)                  │    │
│  │  • Automatic background refresh                      │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    OPTIONAL: CDN Layer                       │
│  (CloudFlare, AWS CloudFront - for static/public data)      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   DJANGO BACKEND                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │         Redis Cache (Server-Side)                    │    │
│  │  • Key-value store with TTL                         │    │
│  │  • Shared across all client connections             │    │
│  │  • Sub-millisecond reads                            │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                  │
│                           ▼                                  │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            MongoDB (Source of Truth)                 │    │
│  │  • Full certificate data                            │    │
│  │  • Aggregations and complex queries                 │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Client-Side Caching with SWR

### What is SWR?

**SWR** (Stale-While-Revalidate) is a React data-fetching library created by Vercel. It implements the HTTP cache invalidation strategy from RFC 5861.

### How SWR Works

```
1. User requests data → SWR checks cache
2. If cached (stale) → IMMEDIATELY return cached data
3. While returning stale → Background fetch for fresh data
4. When fresh data arrives → Update cache + UI
```

**Flow Diagram:**

```
Request → Cache Hit? ─YES→ Return Stale Data → Background Revalidate → Update
              │
              NO
              ▼
         Fetch from API → Return Fresh Data → Cache Result
```

### Key SWR Features

| Feature | Benefit |
|---------|---------|
| **Stale-while-revalidate** | Instant UI with eventual consistency |
| **Automatic revalidation** | On focus, interval, or reconnect |
| **Request deduplication** | Multiple components share same fetch |
| **Optimistic updates** | Instant UI feedback on mutations |
| **Built-in error handling** | Retry logic and error states |
| **TypeScript support** | Full type inference |

### Installation

```bash
npm install swr
```

### Basic Usage Pattern

```tsx
import useSWR from 'swr';

const fetcher = (url: string) => fetch(url).then(res => res.json());

function Dashboard() {
    const { data, error, isLoading, mutate } = useSWR('/api/dashboard/metrics', fetcher);

    if (error) return <div>Failed to load</div>;
    if (isLoading) return <div>Loading...</div>;
    
    return <div>{data.activeCertificates}</div>;
}
```

### SWR Cache Keys

SWR uses the first argument as the cache key. Same key = same cached data:

```tsx
// These share the same cache (same key)
useSWR('/api/certificates?page=1', fetcher);  // Component A
useSWR('/api/certificates?page=1', fetcher);  // Component B

// These are cached separately (different keys)
useSWR('/api/certificates?page=1', fetcher);
useSWR('/api/certificates?page=2', fetcher);
useSWR('/api/certificates?status=active', fetcher);
```

### SWR Configuration Options

```tsx
useSWR(key, fetcher, {
    revalidateOnFocus: false,     // Don't refetch on window focus
    revalidateOnReconnect: true,  // Refetch when network reconnects
    refreshInterval: 5 * 60 * 1000, // Auto-refresh every 5 min
    dedupingInterval: 2000,       // Dedupe requests within 2s
    errorRetryCount: 3,           // Retry failed requests 3 times
    shouldRetryOnError: true,     // Enable retry on errors
});
```

### Global SWR Configuration

```tsx
// _app.tsx or providers.tsx
import { SWRConfig } from 'swr';

function App({ children }) {
    return (
        <SWRConfig value={{
            fetcher: (url) => fetch(url).then(r => r.json()),
            revalidateOnFocus: false,
            errorRetryCount: 2,
        }}>
            {children}
        </SWRConfig>
    );
}
```

### Mutation and Cache Invalidation

```tsx
const { mutate } = useSWRConfig();

// Revalidate specific key
mutate('/api/certificates');

// Revalidate all keys matching pattern
mutate(key => key?.startsWith('/api/certificates'), undefined, { revalidate: true });

// Optimistic update
mutate('/api/certificates', newData, false); // Update cache without revalidation
```

---

## 3. Server-Side Caching with Redis

### Why Redis?

| Feature | Redis | Memcached | In-Memory (Python dict) |
|---------|-------|-----------|-------------------------|
| **Speed** | Sub-ms | Sub-ms | Sub-ms |
| **Persistence** | Optional | No | No (lost on restart) |
| **Data structures** | Rich (hash, list, set) | Simple (key-value) | N/A |
| **TTL support** | Native | Native | Manual |
| **Cluster support** | Yes | Yes | No |
| **Multi-client** | Yes | Yes | No (per-process) |

**Recommendation: Redis** - Best balance of speed, features, and persistence.

### Redis Installation

**Windows (for development):**
```bash
# Using WSL or Docker
docker run -d --name redis -p 6379:6379 redis:alpine
```

**Production (Linux):**
```bash
sudo apt install redis-server
sudo systemctl start redis
```

### Python Redis Client Setup

```bash
pip install redis
```

### Django Redis Configuration

```python
# settings.py
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'ssl_guardian',
    }
}
```

### Custom Cache Service (Recommended for Control)

```python
# cache_service.py
import redis
import json
import hashlib
from typing import Optional, Any

class CacheService:
    def __init__(self):
        self.redis = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )
        self.prefix = 'ssl_guardian'
    
    def _make_key(self, namespace: str, params: dict) -> str:
        """Generate consistent cache key from params"""
        sorted_params = json.dumps(params, sort_keys=True)
        hash_val = hashlib.md5(sorted_params.encode()).hexdigest()[:12]
        return f"{self.prefix}:{namespace}:{hash_val}"
    
    def get(self, namespace: str, params: dict) -> Optional[Any]:
        """Get cached value"""
        key = self._make_key(namespace, params)
        data = self.redis.get(key)
        if data:
            return json.loads(data)
        return None
    
    def set(self, namespace: str, params: dict, value: Any, ttl: int = 300):
        """Set cached value with TTL in seconds"""
        key = self._make_key(namespace, params)
        self.redis.setex(key, ttl, json.dumps(value))
    
    def delete(self, namespace: str, params: dict):
        """Delete specific cache entry"""
        key = self._make_key(namespace, params)
        self.redis.delete(key)
    
    def invalidate_namespace(self, namespace: str):
        """Invalidate all keys in a namespace"""
        pattern = f"{self.prefix}:{namespace}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
    
    def clear_all(self):
        """Clear all SSL Guardian caches"""
        pattern = f"{self.prefix}:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)

# Singleton instance
cache = CacheService()
```

### Cache Key Naming Convention

```
ssl_guardian:{namespace}:{hash}

Examples:
ssl_guardian:certificates:abc123def     # Paginated list
ssl_guardian:metrics:xyz789             # Dashboard metrics
ssl_guardian:ca_analytics:456           # CA leaderboard
```

### Using Cache in Controllers

```python
# controllers.py
from .cache_service import cache

class CertificateController:
    @staticmethod
    def get_certificates(page=1, status=None, issuer=None, **kwargs):
        # Build cache params
        cache_params = {'page': page, 'status': status, 'issuer': issuer, **kwargs}
        
        # Try cache first
        cached = cache.get('certificates', cache_params)
        if cached:
            return cached
        
        # Query MongoDB
        result = CertificateModel.get_all(page=page, status=status, issuer=issuer, **kwargs)
        
        # Cache result (5 minute TTL for lists)
        cache.set('certificates', cache_params, result, ttl=300)
        
        return result
```

---

## 4. Hybrid Approach

### How Client + Server Caching Work Together

```
User Request Flow:
1. User opens dashboard
   └─▶ SWR checks browser cache → Empty (first load)
       └─▶ API request to Django
           └─▶ Redis checks server cache → Empty (first load)
               └─▶ MongoDB query → Return data
               └─▶ Store in Redis (TTL: 5 min)
           └─▶ Return to frontend
       └─▶ Store in SWR cache
   └─▶ Display data

2. User switches page, comes back
   └─▶ SWR checks browser cache → HIT (stale data)
       └─▶ Return stale IMMEDIATELY
       └─▶ Background: Check API → Redis HIT → Fresh data
       └─▶ Update SWR cache + UI (if different)

3. New user opens same page
   └─▶ SWR checks browser cache → Empty (different user)
       └─▶ API request → Redis HIT (cached from user 1)
       └─▶ Fast response without MongoDB
```

### Benefits of Hybrid Approach

| Layer | What It Reduces |
|-------|-----------------|
| SWR (Client) | API calls for same user |
| Redis (Server) | MongoDB queries for all users |

### Data Freshness Guarantee

- **SWR**: Returns stale data immediately, then revalidates
- **Redis TTL**: Data never older than TTL (e.g., 5 min)
- **Mutations**: Invalidate both caches on data changes

---

## 5. TTL (Time-To-Live) Strategy

### Recommended TTL Values

| Data Type | TTL | Reason |
|-----------|-----|--------|
| **Dashboard metrics** | 5 minutes | Changes with new scans |
| **Certificate list (page N)** | 3 minutes | May change with filters |
| **CA leaderboard** | 15 minutes | Very stable data |
| **Geographic distribution** | 30 minutes | Almost static |
| **Validity trends** | 15 minutes | Changes monthly |
| **Encryption strength** | 15 minutes | Stable distribution |
| **Notifications** | 2 minutes | Time-sensitive |

### SWR Revalidation Intervals

```tsx
// Dashboard metrics - refresh every 5 min
useSWR('/api/metrics', fetcher, { refreshInterval: 5 * 60 * 1000 });

// Notifications - refresh every 2 min
useSWR('/api/notifications', fetcher, { refreshInterval: 2 * 60 * 1000 });

// Static data - no auto-refresh
useSWR('/api/ca-analytics', fetcher, { refreshInterval: 0 });
```

---

## 6. Cache Clearing Logic

### When to Clear Caches

| Event | Action | Why |
|-------|--------|-----|
| **Full page refresh (F5)** | SWR revalidates | User expects fresh data |
| **Soft refresh (Ctrl+R)** | SWR revalidates | Same as F5 |
| **Browser tab focus** | Optional revalidate | Catch up on changes |
| **Data mutation** | Invalidate related caches | Ensure consistency |
| **Redis TTL expiry** | Auto-clear | Prevent stale data |
| **Manual cache clear** | Admin action | Force refresh |

### SWR Refresh Behavior

```tsx
// Control revalidation behavior
useSWR(key, fetcher, {
    revalidateOnMount: true,      // Revalidate on component mount
    revalidateOnFocus: false,     // Don't revalidate on window focus
    revalidateIfStale: true,      // Revalidate if data is stale
});
```

### F5 vs Ctrl+R Behavior

- **Both trigger page reload** → SWR cache is in memory → Clears on reload
- **No difference for SWR** → Both result in fresh fetch
- **Redis cache persists** → Fast server response even after refresh

### Session-Based Caching (Optional)

If you want data to persist across soft refreshes but clear on browser close:

```tsx
// Using sessionStorage as SWR cache provider
import { SWRConfig } from 'swr';

const sessionStorageProvider = () => {
    const map = new Map(JSON.parse(sessionStorage.getItem('swr-cache') || '[]'));
    window.addEventListener('beforeunload', () => {
        sessionStorage.setItem('swr-cache', JSON.stringify([...map.entries()]));
    });
    return map;
};

<SWRConfig value={{ provider: sessionStorageProvider }}>
    {children}
</SWRConfig>
```

> **Note**: Default SWR uses in-memory cache which clears on any page refresh. This is usually desired behavior.

---

## 7. CDN/Edge Caching Analysis

### Should We Use CDN for This Application?

**Analysis for SSL Guardian (millions of certificates, paginated):**

| Factor | CDN Suitable? | Reason |
|--------|---------------|--------|
| Static assets (JS/CSS) | ✅ Yes | Never changes |
| Public API responses | ⚠️ Maybe | Depends on cache headers |
| Filtered/paginated data | ❌ Challenging | Too many cache key variations |
| User-specific data | ❌ No | Can't cache per-user |
| Real-time notifications | ❌ No | Time-sensitive |

### Pros of CDN Caching

1. **Global edge locations** → Lower latency for worldwide users
2. **Reduced origin load** → Fewer requests hit your server
3. **DDoS protection** → CDN absorbs traffic spikes
4. **SSL offloading** → CDN handles HTTPS termination

### Cons for This Application

1. **Cache key explosion** → `certificates?page=1&status=active&issuer=LE...` = thousands of keys
2. **Stale data risk** → CDN may serve old data after DB changes
3. **Invalidation complexity** → Purging specific pages is difficult
4. **Cost** → Cache storage for many variations

### Recommendation

**For SSL Guardian, use CDN for:**
- ✅ Static assets (images, JS, CSS)
- ✅ Public API endpoints with simple responses (e.g., `/api/health`)

**Don't use CDN for:**
- ❌ Paginated certificate lists (too many variations)
- ❌ Filtered data (dynamic query params)
- ❌ Real-time data (notifications, metrics)

**Better alternative:** Redis caching at origin (already implemented) provides most benefits without CDN complexity.

### Basic CDN Setup (If Needed Later)

**CloudFlare (for static assets):**
```
Page Rule: /static/* 
Cache Level: Cache Everything
Edge TTL: 1 week
```

**Next.js Static Generation:**
```tsx
// For truly static pages (if any)
export const revalidate = 3600; // ISR every 1 hour
```

---

## 8. Testing Caching is Working

### A. Testing Client-Side (SWR) Caching

#### Step 1: Check Network Tab

1. Open DevTools → Network tab
2. Load dashboard page
3. **First load:** See API calls to `/api/metrics`, `/api/certificates`, etc.
4. Navigate away and back
5. **Second load:** Should see FEWER or NO API calls (SWR serving cached)

#### Step 2: Add Debug Logging

```tsx
// In your SWR hook
useSWR('/api/metrics', fetcher, {
    onSuccess: (data) => console.log('[SWR] Fresh data received:', data),
    onError: (err) => console.log('[SWR] Error:', err),
});

// In fetcher function
const fetcher = async (url: string) => {
    console.log('[FETCH] Calling API:', url);
    const res = await fetch(url);
    return res.json();
};
```

#### Step 3: Verify Deduplication

```tsx
// In two different components, use same key
// Should see only ONE fetch in network tab
useSWR('/api/metrics', fetcher);  // Component A
useSWR('/api/metrics', fetcher);  // Component B
```

### B. Testing Server-Side (Redis) Caching

#### Step 1: Redis CLI Commands

```bash
# Connect to Redis
redis-cli

# See all SSL Guardian keys
KEYS ssl_guardian:*

# Get specific key value
GET ssl_guardian:certificates:abc123

# Check TTL remaining
TTL ssl_guardian:certificates:abc123

# Clear all app caches
DEL ssl_guardian:*

# Monitor real-time commands
MONITOR
```

#### Step 2: Add Backend Logging

```python
# controllers.py
import logging
logger = logging.getLogger(__name__)

class CertificateController:
    @staticmethod
    def get_certificates(**kwargs):
        cache_params = {...}
        
        cached = cache.get('certificates', cache_params)
        if cached:
            logger.info(f"[CACHE HIT] certificates:{cache_params}")
            return cached
        
        logger.info(f"[CACHE MISS] certificates:{cache_params} - querying MongoDB")
        result = CertificateModel.get_all(**kwargs)
        cache.set('certificates', cache_params, result, ttl=300)
        return result
```

#### Step 3: Test Sequence

```bash
# Terminal 1: Watch Django logs
python manage.py runserver

# Terminal 2: Watch Redis
redis-cli MONITOR

# Browser: Load dashboard
# - First load: See "[CACHE MISS]" in Django, "SET" in Redis
# - Refresh: See "[CACHE HIT]" in Django, "GET" in Redis
```

### C. Verifying MongoDB is NOT Hit

#### Step 1: MongoDB Profiling

```javascript
// In MongoDB shell
db.setProfilingLevel(2);  // Log all queries

// After testing
db.system.profile.find().pretty()
```

#### Step 2: PyMongo Logging

```python
# In db.py or settings
import logging
logging.getLogger('pymongo').setLevel(logging.DEBUG)
```

#### Step 3: Expected Behavior

| Action | MongoDB Queries | Redis | SWR |
|--------|-----------------|-------|-----|
| First user, first load | YES | MISS → SET | MISS → FETCH |
| First user, refresh | NO | HIT | MISS → FETCH (from Redis) |
| Second user, first load | NO | HIT | MISS → FETCH (from Redis) |
| After Redis TTL expires | YES | MISS → SET | MISS → FETCH |

### D. Performance Metrics

Use browser DevTools Performance tab:
- **Before caching:** API response ~500ms
- **After caching (Redis):** API response ~10-50ms
- **After caching (SWR hit):** No API call, ~0ms

---

## 9. Implementation Checklist

### Phase 1: Client-Side (SWR)

- [ ] Install SWR: `npm install swr`
- [ ] Create SWRConfig provider in `_app.tsx` or `layout.tsx`
- [ ] Create custom hooks for each data type (e.g., `useMetrics`, `useCertificates`)
- [ ] Replace direct API calls in DashboardContext with SWR hooks
- [ ] Add loading/error states
- [ ] Test with Network tab

### Phase 2: Server-Side (Redis)

- [ ] Install Redis locally or via Docker
- [ ] Install Python client: `pip install redis`
- [ ] Create `cache_service.py` with CacheService class
- [ ] Add caching to `controllers.py` methods
- [ ] Configure TTLs per data type
- [ ] Add logging for cache hits/misses
- [ ] Test with `redis-cli MONITOR`

### Phase 3: Integration

- [ ] Ensure cache invalidation on data mutations
- [ ] Add cache clear endpoint for admin
- [ ] Monitor cache hit rates in production
- [ ] Adjust TTLs based on usage patterns

---

## Appendix: Quick Reference

### SWR Cheat Sheet

```tsx
// Basic usage
const { data, error, isLoading, mutate } = useSWR(key, fetcher);

// With options
useSWR(key, fetcher, { refreshInterval: 60000 });

// Conditional fetching
useSWR(shouldFetch ? key : null, fetcher);

// Revalidate manually
mutate(key);

// Update cache optimistically
mutate(key, newData, false);
```

### Redis Cheat Sheet

```python
# Basic operations
cache.set('namespace', params, data, ttl=300)
cache.get('namespace', params)
cache.delete('namespace', params)
cache.invalidate_namespace('namespace')
cache.clear_all()
```

### TTL Quick Reference

| Data | Redis TTL | SWR Refresh |
|------|-----------|-------------|
| Metrics | 5 min | 5 min |
| Certificates | 3 min | None |
| Analytics | 15 min | None |
| Notifications | 2 min | 2 min |

---

## 10. Redis Installation & Troubleshooting Guide

### Common Errors and Solutions

#### Error: `ModuleNotFoundError: No module named 'redis'`

**Cause:** Python redis library not installed in your environment.

**Solution:**
```bash
# Activate your virtual environment first!
# For conda:
conda activate FYP

# For venv:
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# Then install redis
pip install redis
```

**Verify installation:**
```bash
pip show redis
# Should show: Name: redis, Version: 7.x.x
```

---

#### Error: `redis.exceptions.ConnectionError: Connection refused`

**Cause:** Redis server is not running.

**Solution:** Install and start Redis server (see below).

---

### Redis Server Installation

#### Windows (3 Options)

**Option 1: Docker (Recommended)**
```bash
# Install Docker Desktop first: https://www.docker.com/products/docker-desktop
docker run -d --name redis -p 6379:6379 redis:alpine

# To stop:
docker stop redis

# To restart:
docker start redis
```

**Option 2: Windows Subsystem for Linux (WSL)**
```bash
# Install WSL first, then in WSL terminal:
sudo apt update
sudo apt install redis-server
sudo service redis-server start
```

**Option 3: Native Windows Build (Not officially supported)**
```bash
# Download from: https://github.com/tporadowski/redis/releases
# Extract and run redis-server.exe
```

#### macOS

```bash
# Using Homebrew
brew install redis

# Start Redis
brew services start redis

# Or run manually
redis-server
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install redis-server

# Start and enable on boot
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Check status
sudo systemctl status redis-server
```

---

### Verifying Redis is Running

```bash
# Test connection (should return PONG)
redis-cli ping

# Check server info
redis-cli info server

# See all keys (should be empty initially)
redis-cli KEYS "*"
```

---

### Python Library Installation

The `pip install redis` command should be run **in your active virtual environment**:

```bash
# Navigate to backend directory
cd backend

# If using conda
conda activate FYP
pip install redis

# If using venv
source venv/bin/activate
pip install redis

# Add to requirements.txt for future
echo "redis>=5.0.0" >> requirements.txt
```

---

### Graceful Fallback (Already Implemented)

The SSL Guardian `cache_service.py` includes graceful fallback:

1. **If redis library not installed** → Logs warning, continues without caching
2. **If Redis server not running** → Logs warning, continues without caching
3. **All API endpoints work normally** → Just query MongoDB directly

**Console output when Redis unavailable:**
```
[CACHE] Redis library not installed. Run 'pip install redis' to enable caching.
[CACHE] Application will continue without caching (all queries hit MongoDB).
```

---

### Testing Caching After Setup

**1. Start Redis:**
```bash
docker run -d -p 6379:6379 redis:alpine
```

**2. Restart Django:**
```bash
python manage.py runserver
```

**3. Look for success message:**
```
[CACHE] Connected to Redis successfully
```

**4. Verify caching works:**
```bash
# In another terminal
redis-cli MONITOR

# Load dashboard in browser
# Should see SET commands on first load
# Should see GET commands on refresh (cache hits)
```

---

### Environment-Specific Configuration

If you need different Redis hosts for dev/prod, set environment variable:

```python
# In cache_service.py (optional enhancement)
import os

REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
```

Then set in your environment:
```bash
# Linux/macOS
export REDIS_HOST=your-redis-host.com
export REDIS_PORT=6379

# Windows
set REDIS_HOST=your-redis-host.com
set REDIS_PORT=6379
```

---

### Quick Checklist

| Step | Command | Expected |
|------|---------|----------|
| 1. Install redis library | `pip install redis` | No errors |
| 2. Verify library | `pip show redis` | Shows version 5+ |
| 3. Start Redis server | `docker run -d -p 6379:6379 redis:alpine` | Container starts |
| 4. Test Redis | `redis-cli ping` | Returns `PONG` |
| 5. Start Django | `python manage.py runserver` | No errors |
| 6. Check logs | - | `[CACHE] Connected to Redis successfully` |

---

## 11. Caching Behavior FAQ - Detailed Explanations

### Question 1: Why does clicking a card call the API for its first page?

**Your Understanding is Correct!** Here's exactly what happens:

#### Current Client-Side Caching Flow (DashboardContext.tsx)

```
1. Click "Global Health" card
   └─▶ API call for page 1 (filter: all)
   └─▶ Store in pageCacheRef: "all:none:1" → data
   └─▶ Display data

2. Click "Next" (page 2)
   └─▶ Check cache for "all:none:2" → NOT FOUND
   └─▶ API call for page 2
   └─▶ Store in cache: "all:none:2" → data

3. Click "Previous" (back to page 1)
   └─▶ Check cache for "all:none:1" → FOUND!
   └─▶ Return cached data (NO API call)

4. Click different card (e.g., "Active Certificates")
   └─▶ CLEAR entire pageCacheRef (all previous pages gone)
   └─▶ API call for page 1 (filter: active)
   └─▶ Store in cache: "active:none:1" → data
```

#### Why Do We Clear Cache on Filter Change?

When you switch from one card to another, the **data type changes completely**:
- Global Health → ALL certificates
- Active Certificates → Only VALID status
- Vulnerabilities → Only certificates with zlint errors

Keeping old cache would cause confusion (mixing filtered and unfiltered data). So we **clear the cache and start fresh** for each card type.

#### What We DO Cache:
- All pages visited **within the same card/filter type**
- Example: If you're in "Global Health" and browse pages 1 → 2 → 3 → 1, all are cached

#### What We DON'T Cache:
- Pages from a **previously selected card** after switching cards
- This is intentional to ensure fresh data for each filter type

---

### Question 2: Does Server-Side (Redis) Caching Work the Same Way?

**No, Redis caching is DIFFERENT and MORE PERSISTENT!**

#### Key Difference: Client vs Server Caching

| Aspect | Client (pageCacheRef) | Server (Redis) |
|--------|----------------------|----------------|
| Scope | Single browser session | All users, all sessions |
| Clear on card change | YES | NO |
| Clear on page refresh | YES | NO |
| TTL | None (memory only) | 3-15 minutes |
| Shared between users | NO | YES |

#### Server-Side Redis Flow

```
User A: Click "Global Health" → Page 1
  └─▶ Backend: Check Redis for "ssl_guardian:certificates:{hash}"
      └─▶ MISS → Query MongoDB
      └─▶ Store in Redis (TTL: 3 min)
      └─▶ Return to frontend

User B: Click "Global Health" → Page 1 (same filter)
  └─▶ Backend: Check Redis for "ssl_guardian:certificates:{hash}"
      └─▶ HIT! → Return from Redis (no MongoDB query)

User A: Click "Active Certificates" → Page 1
  └─▶ Backend: Check Redis for "ssl_guardian:certificates:{different_hash}"
      └─▶ MISS (different filter = different hash)
      └─▶ Query MongoDB
      └─▶ Store in Redis (different key)

Important: Redis does NOT clear previous filter data!
Both "all certificates" and "active certificates" remain cached
with their own keys until their TTL expires.
```

#### Why Redis Doesn't Clear on Card Change

Redis uses **unique keys per query combination**:

```
Key: ssl_guardian:certificates:{md5_hash_of_params}

Different filters = Different hash = Different key:
- "all:page1:size10" → hash: abc123
- "active:page1:size10" → hash: def456
- "vulnerabilities:page1:size10" → hash: ghi789

All coexist in Redis without overwriting each other!
```

---

### Question 3: Page 1 Re-fetches After Clicking Previous - Is This a Bug?

**Yes, this WAS a bug!** Here's what was happening:

#### The Problem

```
Scenario:
1. Click "Global Health" → Fetches page 1 ✓
2. Click "Next" → Fetches page 2, caches it ✓
3. Click "Previous" → Uses cache for page 1 ✓ (if page 1 was cached)

But wait - was page 1 actually cached?
```

#### Root Cause Analysis

When you click a card (like "Global Health"), the `handleCardClick` function:
1. Calls the API for page 1
2. Clears the cache
3. **Then** stores page 1 in cache

But there was a timing issue in the original implementation where we stored the cache key using `activeFilter` which hadn't been updated yet to the new filter type.

#### The Fix Applied

In `DashboardContext.tsx`, we now use `getCacheKey` with the **current card's filter type** when caching page 1:

```typescript
// After card click, cache page 1 with correct filter type
const cacheKey = getCacheKey(activeFilter.type, activeFilter.value, 1);
pageCacheRef.current.set(cacheKey, { ... });
```

#### How to Verify It's Working

1. Open browser DevTools → Console
2. Click "Global Health" card
   - See: `[PAGE CACHE SET] all:none:1 (card click page 1)`
3. Click "Next" (page 2)
   - See: `[PAGE CACHE MISS] all:none:2` then `[PAGE CACHE SET] all:none:2`
4. Click "Previous" (page 1)
   - See: `[PAGE CACHE HIT] all:none:1` ← **No API call!**

If you see `[PAGE CACHE MISS]` for page 1 after step 4, there's still an issue. Let me know!

---

### Summary: Two-Layer Caching Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT-SIDE CACHE                         │
│  (DashboardContext pageCacheRef)                            │
│                                                             │
│  • Clears on: Card/filter change, page refresh, tab close  │
│  • Scope: Single user session                               │
│  • Purpose: Instant pagination within same filter           │
└─────────────────────────────────────────────────────────────┘
                           │
                    API Call (if cache miss)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    SERVER-SIDE CACHE                         │
│  (Redis with TTL)                                           │
│                                                             │
│  • Clears on: TTL expiry only (3-15 min)                   │
│  • Scope: All users, all sessions                           │
│  • Purpose: Reduce MongoDB load across all users            │
│  • Keys: Unique per filter/page combination                 │
└─────────────────────────────────────────────────────────────┘
                           │
                    MongoDB Query (if Redis miss)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MongoDB Database                          │
│  (Source of Truth)                                          │
└─────────────────────────────────────────────────────────────┘
```

---

### TTL Configuration Update

Page 1 data is especially important (first impression, most commonly viewed), so we now use a **longer TTL of 15 minutes** for page 1 queries:

| Page | Redis TTL |
|------|-----------|
| Page 1 | 15 minutes (900 seconds) |
| Page 2+ | 3 minutes (180 seconds) |

This means page 1 data stays cached longer, reducing load times for the most common access pattern.

---

## 12. Staleness Checking - How It Really Works

### Question 1: How Does Client-Side (SWR) Check Staleness?

**Important Clarification:** SWR does NOT call an API to "check" if data is stale!

#### How SWR Determines Staleness

SWR uses **time-based staleness**, not database comparison:

```
Staleness = (current time) - (time when data was cached) > dedupingInterval
```

**Here's what happens with events like tab switching:**

| Event | SWR Configuration | Behavior |
|-------|-------------------|----------|
| Tab focus | `revalidateOnFocus: false` | **NO API call** (we disabled this) |
| Network reconnect | `revalidateOnReconnect: true` | API call to refresh |
| Component mount | `revalidateOnMount: true` | API call on first render |
| refreshInterval | `refreshInterval: 5 * 60 * 1000` | API call every 5 min |

#### Why You Don't See API Calls on Tab Switch

In our `SWRProvider.tsx`, we set:
```typescript
revalidateOnFocus: false  // ← This is why!
```

This means:
- ✅ Switching tabs does NOT trigger API calls
- ✅ Coming back to dashboard does NOT re-fetch
- ✅ Data stays cached until explicit refresh or interval

#### SWR Staleness Flow (Current Implementation)

```
1. Local time check: Is cache older than refreshInterval?
   └─▶ NO → Return cached data (no API call)
   └─▶ YES → Return cached data IMMEDIATELY
              AND trigger background API call

2. No database comparison happens
   └─▶ SWR trusts the TTL/interval timing
   └─▶ It doesn't "ask" the server if data changed
```

#### If You WANT API Calls on Tab Focus

Change in `SWRProvider.tsx`:
```typescript
revalidateOnFocus: true  // Will call API on every tab switch
```

But this can cause excessive API calls if user switches tabs frequently.

---

### Question 2: Redis Staleness - Does It Auto-Sync with MongoDB?

**No, Redis does NOT automatically detect MongoDB changes!**

#### Current Redis Behavior

```
1. User makes API request
2. Check Redis:
   - If data exists and TTL not expired → Return Redis data
   - If TTL expired or no data → Query MongoDB, store in Redis

3. Manual MongoDB edit (via mongo shell or Compass):
   - Redis still has old data
   - Will serve stale data until TTL expires
   - No automatic sync
```

#### Why No Automatic Sync?

1. **Redis doesn't know about MongoDB** - They're separate systems
2. **No change detection** - MongoDB doesn't "push" changes to Redis
3. **TTL is the only expiry mechanism** - Data cleared only when timeout

#### Your Refined Approach Analysis

Your idea:
> "When API is called, first check Redis, return data, then simultaneously check DB. If changed, update Redis."

**This is a valid pattern called "Read-Through with Background Refresh"!**

Here's the refined version:

```python
# Pseudocode for your approach
def get_certificates(params):
    # 1. Check Redis first
    cached = cache.get('certificates', params)
    
    if cached:
        # 2. Return cached data immediately to user
        response = cached
        
        # 3. Start background task to validate data
        # (This runs AFTER returning the response)
        background_validate(params, cached)
        
        return response
    
    # Cache miss: query MongoDB
    result = mongodb.query(params)
    cache.set('certificates', params, result)
    return result

def background_validate(params, cached_data):
    # Compare cached vs actual MongoDB data
    fresh_data = mongodb.query(params)
    
    if fresh_data != cached_data:
        # Update cache with fresh data
        cache.set('certificates', params, fresh_data)
        logger.info("Cache updated with fresh data")
```

#### Potential Issues with Your Approach

| Issue | Problem | Solution |
|-------|---------|----------|
| **Concurrent requests** | Multiple API calls → Multiple background checks | Use locking or debouncing |
| **Performance** | Every request triggers DB check | Only check on X% of requests or time-based |
| **Race conditions** | Two writes to Redis at same time | Redis atomic operations |

#### Recommended Simple Solution Instead

Rather than complex background validation, use **shorter TTLs**:

```python
# Instead of 15-minute TTL, use 2-3 minutes
TTL_CONFIG = {
    'metrics': 120,      # 2 minutes
    'certificates_page1': 180,  # 3 minutes
    'certificates': 120,  # 2 minutes
    ...
}
```

This ensures:
- Data is never more than 2-3 minutes stale
- No complex background validation needed
- Simple and reliable

#### Cache Invalidation on Write Operations

If you want Redis to update when code makes changes:

```python
# In your create/update/delete methods
class CertificateModel:
    @classmethod
    def update_certificate(cls, cert_id, data):
        # 1. Update MongoDB
        cls.collection.update_one({'_id': cert_id}, {'$set': data})
        
        # 2. Invalidate related caches
        cache.invalidate_namespace('certificates')
        cache.invalidate_namespace('certificates_page1')
        cache.invalidate_namespace('metrics')
```

This ensures:
- ✅ After code updates DB, related caches are cleared
- ✅ Next request gets fresh data
- ❌ Manual mongo shell edits still won't trigger this

---

### Question: Will Concurrent API Calls Wait for Each Other?

**No, they won't wait!** Here's what happens:

```
Time 0ms:  Request A arrives → Check Redis → HIT → Return cached
Time 1ms:  Request B arrives → Check Redis → HIT → Return cached
Time 2ms:  Request A starts background validation
Time 3ms:  Request B starts background validation (duplicate work!)
Time 100ms: Request A's validation completes → Updates Redis
Time 101ms: Request B's validation completes → Updates Redis (again!)
```

**This is wasteful!** Solutions:

1. **Debouncing**: Only validate once per 10 seconds
2. **Locking**: Use Redis lock to prevent concurrent validations
3. **Simple TTL** (Recommended): Just keep TTLs short, no background validation

---

### Summary: What Checks Staleness Where?

| Layer | Staleness Check Method | Triggers API/DB Call? |
|-------|------------------------|----------------------|
| **SWR (Client)** | Time-based (refreshInterval) | Only on interval or explicit mutate() |
| **pageCacheRef (Client)** | None - clears on filter change | No |
| **Redis (Server)** | TTL expiry only | On expire → Queries MongoDB |
| **MongoDB** | N/A - Source of truth | Always fresh |

---

### Updated TTL Values (Shorter for Freshness)

Based on your feedback, we're reducing TTLs:

| Data Type | Old TTL | New TTL |
|-----------|---------|---------|
| Metrics | 5 min | 2 min |
| Certificates Page 1 | 15 min | 3 min |
| Certificates Page 2+ | 3 min | 2 min |
| CA Analytics | 15 min | 5 min |
| Encryption | 15 min | 5 min |
| Validity Trends | 15 min | 5 min |
| Geographic | 30 min | 5 min |
| Future Risk | 15 min | 5 min |
| Notifications | 2 min | 1 min |
| Unique Filters | 30 min | 5 min |
