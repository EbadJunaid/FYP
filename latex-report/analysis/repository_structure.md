# Repository Structure

## Evidence classification

Inventory counts, paths, configuration values, and committed-data line counts are **Verified from repository**. The analytical distinction between active, generated, legacy, and “important” files follows explicit call/import/configuration evidence but remains a documentation categorization, not an implemented project feature.

## Scan scope

The repository was recursively inventoried on 13 July 2026. The folder named `archive` was excluded exactly as requested. Hidden and configuration material relevant to the project was included, notably `.gitignore`, `.vscode/settings.json`, and the root `project-config.json`. Generated dependency trees (`node_modules`), Next.js build output (`.next`), Python bytecode, and Git object storage were inventoried but are not treated as project-authored source.

The initial physical inventory contained 32,625 files and 2,746 directories. Most of that volume is generated material: the dashboard subtree includes `node_modules` and `.next`, while `.git` contains repository history. After removing generated/build/history material and the excluded `archive` folder, the implementation and evidence set is approximately 200 first-party files. Git tracks 236 files outside `archive`.

## Top-level hierarchy

```text
FYP/
|-- binaries/                         Runtime executables used by crawlers/CT ingestion
|-- ct-logs-renewal-pipeline/         CT monitoring, renewal, discovery, merge, orchestration
|-- dashboard/
|   |-- backend/                      Django API, MongoDB access, analytics, precomputation
|   `-- frontend/                     Next.js/React dashboard
|-- figures-and-poster/               Diagrams, editable sources, icon, project poster
|-- recordings/                       Current and obsolete dashboard demonstrations
|-- reports/                          Standalone exploratory/report-generation scripts
|-- research-papers/                  Three locally stored related-work papers
|-- ssl-certificates-crawler/
|   |-- domain-based-crawler/         Concurrent domain TLS crawler and dataset preparation
|   `-- ip-based-crawler/             Experimental Pakistan IPv4 crawler
|-- useful-scripts/                   Maintenance and test-data utilities
|-- .gitignore                        Generated-data, logs, environments, outputs exclusions
|-- project-config.json               Active MongoDB pair, CSV path, logical countries
`-- README.md                         Project overview; useful but partly stale
```

## Main implementation hierarchy

```text
dashboard/backend/
|-- certificates/
|   |-- ca_analytics/                 CA statistics, validation matrix, ranking
|   |-- overview/                     filters, encryption, risk/vulnerability views
|   |-- san_analytics/                SAN summary, buckets, TLD/wildcard analytics
|   |-- shared_apis/                  dashboard metrics, certificate list/detail, geography
|   |-- shared_keys/                  shared-public-key analytics and details
|   |-- signature_hash/               signature/hash/key-size analytics
|   |-- trends/                       live trend aggregations
|   |-- validity_analysis/            validity summary/distribution/timeline
|   |-- cache_service.py              optional Redis JSON cache
|   |-- db.py                         Mongo connection, logical scope, collection wrapper
|   |-- scope_middleware.py           request scope selection
|   `-- Scopes.json                   196 configured country scopes plus global
|-- pre-compute-scripts/              six analytics computations, indexes, orchestration
|-- ssl_dashboard/                    Django project settings, root URLs, WSGI/ASGI
|-- country-domain-extractors/        legacy one-off domain extraction utilities
|-- manage.py
`-- requirements.txt

dashboard/frontend/src/
|-- app/                              App Router pages and certificate detail route
|-- components/                       layout, charts, cards, tables, filters, exports
|-- context/                          dashboard, search, and theme state
|-- controllers/pageController.ts     UI-oriented API adapters
|-- services/apiClient.ts             typed HTTP client and response contracts
|-- hooks/                            reusable data hooks
|-- types/                            dashboard types
`-- data/mockData.ts                  legacy mock data, not used by active pages
```

## Data and generated material

- `ct-logs-renewal-pipeline/global-dataset.csv` contains a header plus 707,084 data rows at scan time.
- `ssl-certificates-crawler/domain-based-crawler/datasets/pk-domains.csv` contains a header plus 8,185 rows.
- APNIC evidence includes 83,089 delegated-statistics lines globally and 720 Pakistan-filtered lines; `pk-ip-ranges.csv` contains 720 lines.
- Crawler logs, report outputs, database dumps, raw source datasets, virtual environments, `.next`, and `node_modules` are intentionally ignored and are not report evidence.

## Configuration authority

The active configuration authority is the root `project-config.json`. It selects the physical MongoDB pair `hugging-face-792k` and `hugging-face-792k-results`, the global dataset CSV, and configured country metadata. `dashboard/backend/pre-compute-scripts/databases.json` still names an older 700k database and is treated as stale legacy configuration. Several README passages and crawler defaults also retain older database names; code paths invoked by the generic precompute runner use the root configuration.
