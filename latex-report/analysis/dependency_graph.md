# Dependency Graph

## Evidence classification

Concrete imports, subprocess calls, URLs, database references, and file transfers are **Verified from repository**. The high-level grouping of these facts into one system/context diagram is **Inference — approval required** under I-025. No diagram may imply a production deployment or measured runtime behavior.

## End-to-end dependency graph

```mermaid
flowchart LR
    CSV[global-dataset.csv] --> DC[Domain crawler]
    Internet[Domain TLS endpoints :443] --> DC
    ZC[zcertificate binary] --> DC
    DC --> MAIN[(Main MongoDB certificates)]

    CT[Public CT logs] --> GO[CertStream Go server]
    GO --> WS[go-server.py WebSocket consumer]
    WS --> CTDB[(go-server MongoDB)]
    MAIN --> RENEW[data-renew.py]
    CSV --> RENEW
    CTDB --> RENEW
    RENEW --> RDC[Renewal crawler]
    RDC --> RDB[(data-renew staging)]
    RDB --> MERGE[data-renew-merge.py]
    MERGE --> MAIN
    CTDB --> NEW[new-data.py]
    NEW --> NDC[New-domain crawler]
    NDC --> NDB[(new-data staging)]
    NDB --> MAIN
    NEW --> CSV

    MAIN --> PRE[Generic precompute scripts]
    PRE --> RESULTS[(Results MongoDB)]
    MAIN --> API[Django JSON API]
    RESULTS --> API
    REDIS[(Optional Redis)] <--> API
    API --> CLIENT[Typed frontend API client]
    CLIENT --> UI[Next.js dashboard pages]
```

## Backend package dependencies

```mermaid
flowchart TD
    URL[urls.py] --> VIEW[Feature views]
    VIEW --> CTRL[Feature controllers]
    CTRL --> QUERY[Query/model classes]
    CTRL --> CACHE[CacheService]
    QUERY --> DB[MongoDBClient / ScopedCollection]
    DB --> MAIN[(Main certificates)]
    QUERY --> RESULTS[(Precomputed results)]
    SCOPE[ScopeMiddleware] --> DB
```

The layering is conventional in the feature packages, but query classes also contain serialization and business rules. `SharedModels` is a central dependency for certificate status, grading, filtering, serialization, and risk enrichment. Feature packages depend on `MongoDBClient` for live scoped reads and direct result-database access for materialized analytics.

## Frontend dependencies

```mermaid
flowchart TD
    PAGES[App Router pages] --> PC[pageController.ts]
    PAGES --> AC[apiClient.ts]
    PAGES --> SWR[SWR]
    PC --> AC
    AC --> API[Django /api]
    PAGES --> CTX[Dashboard/Search/Theme contexts]
    PAGES --> COMP[Cards, tables, filters, charts]
    COMP --> RECHARTS[Recharts]
    CTX --> STORAGE[localStorage/sessionStorage]
```

## External dependencies and boundaries

- Public Internet: domain TLS services and Google/Chrome-configured CT logs.
- Local services: MongoDB at `localhost:27017`, optional Redis at `localhost:6379`, Django at port 8000, Next.js at port 3000, and the CertStream-compatible server at port 8080.
- Native executables: `zcertificate` and `certstream-server-go`.
- Filesystem contracts: input/output CSVs, PID file, CT checkpoint JSON, configuration JSON/YAML, and ignored logs.

## Dependency risks

- Several scripts hard-code local URLs, database defaults, or binary names instead of using the root configuration.
- The current Windows binaries have `.exe` suffixes, while scripts frequently expect extensionless paths.
- `go-server.py` uses `os.setsid`, a POSIX process primitive, despite the Windows repository environment.
- The shared-key list/detail pages hard-code `http://localhost:8000` instead of the frontend environment variable.
- Optional Redis failure is handled, but the application then sends all queries to MongoDB.
- No container/lockfile-based Python runtime definition covers every repository script.
