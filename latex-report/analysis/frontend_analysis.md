# Frontend Analysis

## Evidence classification

Routes, components, contexts, API calls, dependencies, and static-check results are **Verified from repository** (V-022–V-024, V-036). Treating the unversioned 1080p recording as the current release is **Inference — approval required** (I-026).

## Structure

The frontend uses Next.js App Router with client-side dashboard pages. `apiClient.ts` defines TypeScript response contracts and attaches the selected scope. `pageController.ts` adapts API certificate records into table rows and supplies defensive empty results. SWR handles page-level data caching/revalidation. Reusable cards, charts, filters, tables, pagination, layout, and modal components provide the interface.

## Routes and data sources

| Route | Functionality | Principal API groups |
|---|---|---|
| `/` | primary dashboard: health, active/expiring/vulnerable metrics, encryption, CA, geography, validity, scans | shared, overview, CA |
| `/dashboard/overview` | overview metrics and paginated certificate table | shared global health/certificates |
| `/dashboard/active-vs-expired` | active/expired/expiring filters and list | shared health/certificates |
| `/dashboard/validity-analytics` | validity statistics, buckets, issuance/validity trends, filtered certificates | validity and shared |
| `/dashboard/signature-hash` | algorithms, hashes, key sizes, issuer matrix, filtered certificates | signature/hash and shared |
| `/dashboard/ca-analytics` | CA metrics, distribution, validation matrix, ranking, filtered certificates | CA and shared |
| `/dashboard/ca-ranking` | extended ranked CA table and selected CA certificates | CA ranking and shared |
| `/dashboard/san-analytics` | SAN metrics, distributions, TLDs, wildcards, filtered certificates | SAN |
| `/dashboard/trends` | expiration, algorithm, validation, and key-size time series | trends and shared |
| `/dashboard/shared-keys` | metadata, distribution, issuer/heatmap views, group list | shared keys |
| `/dashboard/shared-keys/[publicKeyHash]` | detailed key group and certificates | shared-key detail |
| `/dashboard/vulnerabilities` | ranked risk and individual risk-signal filters | overview vulnerabilities and shared certificates |
| `/dashboard/issuer-countries` | geographic selector and country certificate list | shared geography/health/certificates |
| `/dashboard/cas-vs-domains` | CA selector and matching domains/certificates | CA distribution/stats and shared certificates |
| `/certificate/[id]` | parsed certificate identity, validity, issuer/subject, key, SAN, fingerprints, ZLint | shared certificate detail |

## State and interaction

- `DashboardContext` owns filters, selected card state, paginated scan data, page transitions, and dashboard loading.
- `SearchContext` shares the global header search with feature pages.
- `ThemeContext` persists the theme under `ssl-guardian-theme`.
- Scope/database choice is stored locally and appended to requests.
- Several pages use session storage to restore selected rows, page number, filter, and scroll position after navigating to certificate details.
- Download/filter modals turn current UI state into API query parameters.

## Reusable UI

The component set includes a sidebar/header/mobile drawer, metric and analytics cards, progress/bar/line/pie visualizations, data tables, badges, pagination, search, filter and download modals, information tooltips, and a certificate detail layout. Recharts is used for plotted analytics; Tailwind classes implement the dark/light design system.

## Verification

- TypeScript compilation with `tsc --noEmit --incremental false` succeeds.
- ESLint reports 22 errors and 45 warnings. Main categories are synchronous state updates inside effects under current React rules, manual memoization dependency mismatches, explicit `any`, unused imports/state, and hook dependency warnings.
- Active pages use real API calls; the legacy `mockData.ts` file is not imported.

## Limitations and inconsistencies

- Shared-key list/detail calls hard-code `http://localhost:8000`, while the main client uses `NEXT_PUBLIC_API_URL` with a localhost fallback.
- The main client defaults to `http://localhost:8000/api`; another provider path uses `127.0.0.1`, a minor configuration inconsistency.
- The notification method and handler remain in types/client code, but the visible icon and backend route are disabled.
- “View full report” and other unfinished interactions open `NotDevelopedModal`.
- Several pages restore state by setting React state synchronously inside effects, triggering current ESLint errors.
- No frontend unit, component, or end-to-end tests are committed.
- The current recording captures overview, validity, certificate detail, and trends; other pages do not have committed current screenshots.
