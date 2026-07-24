# Module Analysis

## Evidence classification

Module inputs, outputs, functions/classes, and use relationships are **Verified from repository**. Recommendations about how to frame them in the report are editorial **Inference** and are controlled by `report_outline.md`.

## Core module traceability

| Module/file | Inputs | Outputs | Key functions/classes | Used by/why it exists |
|---|---|---|---|---|
| `project-config.json` | operator configuration | database pair, CSV path, country metadata | JSON fields | shared configuration for backend, precompute, CT jobs |
| `certificates/db.py` | root config, `Scopes.json`, request scope | scoped collections/database handles | `ScopedCollection`, `MongoDBClient` | central Mongo/scope boundary |
| `scope_middleware.py` | query/header | active scope mutation | `ScopeMiddleware` | applies frontend scope to every request |
| `cache_service.py` | namespace, params, values | Redis JSON keys/values | `CacheService` | reduces repeat Mongo work |
| `shared_apis/db_queries.py` | filters, ObjectIds, main/results data | serialized dashboard/certificate records | `SharedModels` | common business rules and list/detail queries |
| feature `views.py` files | HTTP request | JSON response | class-based GET views | validation and HTTP boundary |
| feature `controllers.py` files | typed query values | cached dictionaries/lists | controller static methods | coordinates cache and query model |
| feature `db_queries.py` files | scope/filter params | live/materialized analytics | feature model classes | Mongo aggregation and business logic |
| `generic-create-indexes.py` | configured DBs | source/result indexes | `build_source_indexes`, `build_results_indexes` | query/precompute performance |
| `run-generic.py` | CLI/config | executed jobs and verification | discovery/run/verify functions | repeatable analytics orchestration |
| `generic-compute-*.py` | main certificates | scoped result documents | family computation functions | materializes dashboard analytics |
| `backfill-is_leaf.py` | existing main documents | `is_leaf` updates/index | `backfill_database` | aligns legacy data with CA ranking |
| `crawler.py` | fixed CSV/config | main certificates + queue/log state | worker/doctor/dashboard functions | standalone bulk acquisition |
| `crawler-args.py` | CLI + CSV | configurable staging/main output | argument parsing plus crawler functions | invoked by CT pipeline |
| dataset Python scripts | upstream CSV/PEM/APNIC data | filtered/merged domain/CIDR files | extract/clean/merge functions | construct acquisition inputs |
| `go-server.py` | local WebSocket stream | CT Mongo batches/metadata | WebSocket callbacks, batch flush | continuous CT ingestion adapter |
| `data-renew.py` | known CSV + CT documents | renewal CSV + found flags | variation/batch processing | recognizes likely renewals |
| `data-renew-merge.py` | renewal staging | main replacements + checkpoint | sync/batch/checkpoint functions | idempotent domain refresh |
| `new-data.py` | unprocessed CT documents | new crawl/main inserts/CSV append | extract, crawler launch, bulk append | grows the corpus |
| `main.py` | filesystem/process/database state | eight-step pipeline | step functions | batch coordinator |
| `apiClient.ts` | typed params + stored scope | typed HTTP responses | `ApiClient` methods | one frontend API boundary |
| `pageController.ts` | page filters/API records | dashboard types/default fallbacks | fetch/adapter functions | separates API shapes from components |
| contexts | user actions/storage/API | shared UI state | providers/hooks | search/theme/dashboard coordination |
| page components | contexts/API responses | interactive views | App Router page functions | feature presentation |
| shared components | props/events | cards/charts/tables/modals | React components | consistent reusable UI |

## Important helper logic

- `scope_utils.py` normalizes database entries, builds TLD scope filters, creates scoped IDs, merges queries, and creates indexes only when missing.
- `SharedModels.build_filter_query` is the principal live-certificate filter builder used across dashboard tables and exports.
- `SharedModels.serialize_certificate` is the central schema adapter from zcertificate/Mongo documents to the frontend contract.
- `SANModel` stores/hydrates bounded certificate IDs rather than embedding all matching certificates in one result document.
- `OverviewModels` reuses shared-key results to add a key-reuse risk signal.
- `ValidityModels` combines materialized aggregate values with live expiring-window counts.

## Utility modules

- `useful-scripts/csv-cleaner-and-tld.py`: interactive CSV cleanup/TLD extraction with hard-coded path assumptions.
- `useful-scripts/ct-endpoints-tester.py`: checks checkpoint/STH endpoints and can poll them using HTTP/2.
- `useful-scripts/data-removal-from-db.py`: removes raw data, adds scope, and deduplicates fingerprints.
- `useful-scripts/prepare-test-dbs.py`: copies bounded samples into test databases.

## Documentation implications

The report should explain components and data contracts rather than claim a pure MVC architecture: query classes combine data access, serialization, and business rules, while controllers primarily coordinate caching. Experimental/legacy modules should be clearly separated from the active end-to-end path.
