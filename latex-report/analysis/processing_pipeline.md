# Processing Pipeline

## Evidence classification

Every shown process/data edge maps to a concrete function, subprocess call, query, or file operation and is **Verified from repository**. System-wide reliability, freshness, exactly-once behavior, and failure consequences are not established by these diagrams and remain inference where discussed.

## Initial acquisition pipeline

```mermaid
sequenceDiagram
    participant CSV as Domain CSV
    participant Q as Mongo domain_status
    participant W as Worker thread
    participant TLS as Domain:443
    participant Z as zcertificate
    participant M as Main certificates
    CSV->>Q: insert pending domains when queue empty
    W->>Q: atomic claim pending -> processing
    W->>TLS: TCP/TLS with domain SNI, no verification
    TLS-->>W: DER peer certificate
    W->>Z: PEM through subprocess
    Z-->>W: parsed X.509 + ZLint JSON
    W->>W: add domain, scope, scanned_at, is_leaf
    W->>M: insert document
    W->>Q: completed or failed
```

## CT freshness pipeline

```mermaid
flowchart TD
    LOGS[Public CT logs] --> CS[CertStream Go server]
    CS --> INGEST[go-server.py]
    INGEST --> CT[(go-server.certificates)]
    CT -->|known domain/SAN set| RENEW[data-renew.csv]
    CT -->|found=false first domain| NEW[new-data.csv]
    RENEW --> RC[renewal crawler]
    RC --> RDB[(data-renew)]
    RDB --> REPLACE[checkpointed ReplaceOne/upsert]
    REPLACE --> MAIN[(main certificates)]
    NEW --> NC[new-domain crawler]
    NC --> NDB[(new-data)]
    NDB --> INSERT[bulk insert]
    INSERT --> MAIN
    INSERT --> GLOBAL[global-dataset.csv append]
    MAIN --> PRE[generic precompute]
    PRE --> RESULTS[(results database)]
```

## Analytics/request pipeline

```mermaid
flowchart LR
    MAIN[(Main certificates)] --> IDX[Index creation]
    IDX --> JOBS[Six generic computations]
    JOBS --> RESULTS[(Scoped result documents)]
    USER[Dashboard interaction] --> CLIENT[apiClient + scope]
    CLIENT --> MW[ScopeMiddleware]
    MW --> CACHE{Redis hit?}
    CACHE -->|yes| JSON[JSON response]
    CACHE -->|no, aggregate view| RESULTS
    CACHE -->|no, live/list/detail/trend| MAIN
    RESULTS --> CTRL[Controller/serializer]
    MAIN --> CTRL
    CTRL --> CACHE
    CTRL --> JSON
    JSON --> USER
```

## Pipeline inputs and outputs

| Stage | Input | Transformation | Output |
|---|---|---|---|
| Dataset preparation | Tranco/Rapid7/supplied lists/APNIC data | filter, normalize, merge, deduplicate, CIDR summarize | domain/CIDR CSVs |
| Domain crawl | domain CSV | TLS retrieve, parse, ZLint, enrich | canonical certificate documents |
| CT ingestion | CT log stream | normalize SAN sets, batch/deduplicate | CT staging documents |
| Renewal selection | known domain CSV + CT staging | base/www variations, multikey match | renewal CSV |
| Renewal crawl | renewal CSV | same certificate acquisition | renewal staging documents |
| Renewal merge | staging documents | checkpointed replace/upsert by domain | refreshed main documents |
| New discovery | unprocessed CT documents | select/clean first domain, crawl | new staged/main documents and CSV append |
| Precompute | main certificates | scoped aggregations/scoring/bucketing | six results collections |
| API | request filters/scope | cache, live/materialized queries, serialization | JSON/CSV |
| UI | API responses | state, filtering, tables, visualizations | interactive dashboard |

## Failure handling

- Crawler failures are persisted in queue status/logs; stale processing work can be reset.
- CT server indices are persisted in `ct_index.json`.
- WebSocket batches and metadata flush on graceful shutdown.
- Renewal merge checkpoints only advance after a successful batch.
- Optional Redis failure falls back to MongoDB.
- Orchestrator steps log failures and generally abort the sequence.

There is no system-wide transaction, exactly-once guarantee, automated rollback, or committed disaster-recovery procedure.
