# Architecture

## Evidence classification

Components, configured stores, routes, and call/data flows are **Verified from repository** (V-001, V-004, V-009–V-022). The phrase “local, data-intensive analytics system” is an architectural interpretation (I-007), the deployment-style topology is a synthesis (I-025), and security/correctness consequences are inferences I-010–I-016 and I-022. Those interpretive elements require approval before report use.

## Architectural style

The project is a local, data-intensive analytics system composed of acquisition pipelines, MongoDB persistence, materialized analytics, a Django JSON API, and a Next.js single-page dashboard. It is not a single monolith: collection occurs in standalone Python processes, CT monitoring has a separate Go/WebSocket boundary, precomputation runs as batch jobs, and the UI/backend run as independent services.

## Logical components

1. **Domain acquisition:** worker threads claim MongoDB queue entries atomically, retrieve a peer certificate over TLS, parse it through `zcertificate`, enrich it with domain/scope/scan time/leaf status, and persist it.
2. **IP acquisition experiment:** APNIC data is filtered into Pakistan CIDRs; static or interactive scanners test IPs with configurable SNI behavior. Output remains in a separate database/schema.
3. **CT monitoring:** the Go server follows configured CT logs and exposes domain-only WebSocket events. `go-server.py` batches normalized SAN sets into a CT staging database with a `found` flag.
4. **Renewal/discovery orchestration:** `main.py` stops/starts CT collection, derives renewal candidates, crawls renewal and new-domain candidates into staging databases, merges them, refreshes the domain CSV, and invokes precomputation.
5. **Analytics materialization:** six generic computations generate per-scope CA, SAN, signature/hash, validity, geography, and shared-key result documents. Index generation precedes computation.
6. **Backend API:** Django views/controllers return cached or computed JSON. Certificate list/detail and trends can query the main collection; dashboard analytics generally prefer results collections.
7. **Frontend dashboard:** Next.js pages use a typed API client, SWR, contexts, local/session storage, reusable tables/cards, and Recharts.

## Request flow

1. The user chooses a logical country/global scope in the dashboard.
2. The frontend appends `scope` to the API request.
3. `ScopeMiddleware` changes the process-global active scope.
4. Cache keys include the normalized precomputed scope.
5. Live queries use `ScopedCollection`, which injects `{scope: <code>}` unless global is selected.
6. Precomputed queries select the document with the same scope, with a legacy global-document fallback.
7. Custom serializers convert MongoDB types and parsed X.509 fields into frontend response contracts.

## Data architecture

- **Main database:** `hugging-face-792k.certificates` in active configuration. Documents contain `_id`, `domain`, `scope`, `scanned_at`, `is_leaf`, `parsed`, and `zlint`.
- **Results database:** `hugging-face-792k-results` with `ca-analysis`, `geographic-distribution`, `san-analysis`, `shared-keys-detailed`, `signature-and-hash`, and `validity-analysis`.
- **Queue/staging databases:** crawler `domain_status`; CT `go-server.certificates`/`metadata`; temporary `data-renew` and `new-data` databases; merge checkpoint in the main database.
- **Experimental IP database:** separate `ip-based-crawler-*` database and a schema that is not consumed by dashboard code.
- **Django internal database:** SQLite `internal_db`, only for Django facilities.
- **Cache:** optional Redis database 0, keys prefixed `ssl_guardian`.

## Scope model

There is one configured physical main/results pair. `Scopes.json` defines 196 country choices and one global choice. Acquisition code stores an extracted final-label TLD as `scope`, while result jobs materialize only configured scopes. The frontend's “database” terminology is therefore historical: switching selects a logical TLD scope, not a different physical database. Local runtime scope counts are excluded because they are not committed repository evidence.

## Performance mechanisms

- atomic queue claims and concurrent crawler workers;
- bulk writes and batch sizes in CT ingestion/merge;
- persisted CT checkpoints and a renewal merge checkpoint;
- a broad set of main/results indexes, including scoped compound indexes;
- one-pass, all-scope precomputation for several analytics;
- certificate-ID reference buckets to avoid repeated live SAN/validity scans;
- optional Redis response caching;
- pagination and field projections.

No reproducible latency, throughput, memory, or scalability benchmark is committed. These mechanisms may be described as implementation strategies, not measured performance claims.

## Security and correctness boundaries

- Crawlers intentionally disable certificate/hostname verification so invalid, expired, and self-signed certificates can be collected; this is a research behavior, not a secure client configuration.
- The Django settings are development settings: committed secret key, `DEBUG=True`, localhost CORS, empty `ALLOWED_HOSTS`, and no project-specific authentication/authorization.
- Scope is mutable process-global state. Concurrent users requesting different scopes can interfere, so the current design is safest as a single-user/local research dashboard.
- Inputs reach regex/filter logic and export endpoints without an access-control layer.
- The CA scoring formula must be reported exactly as implemented. In particular, its `WKLP` helper returns 1 for keys below 2048 bits and is averaged positively; ECDSA key length is also compared with the RSA-oriented 2048 threshold in `KHS`. These are methodological limitations, not corrected facts.
- Renewal merge checkpoint reuse across dropped/recreated staging databases may skip new ObjectIds; no automated test proves recovery semantics.
- `new-data.py` assumes duplicate protection associated with certificate fingerprints, while the invoked crawler creates a non-unique fingerprint index and inserts without explicit fingerprint deduplication.
