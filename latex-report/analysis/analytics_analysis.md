# Analytics Analysis

## Evidence classification

Metric definitions, formulas, thresholds, buckets, stored fields, and query sources are **Verified from repository** (V-014, V-015, V-025, V-026). Scientific validity, semantic adequacy, misleading-label critique, or security interpretation are **Inference — approval required** (I-019–I-021).

## Precompute framework

`run-generic.py` loads root configuration, pings MongoDB, discovers `generic-*.py` jobs, runs `generic-create-indexes.py` first, executes selected/all computations, and verifies expected result collections and indexes. The six materialized families are CA, geography, SAN, shared keys, signature/hash, and validity. Trends remain live aggregations.

All configured result jobs produce global plus 196 country-scope results in the current configuration. Scope helpers add live matches and stable scoped document IDs.

## Analytics catalog

| Family | Principal computation | Output/consumer |
|---|---|---|
| Global health | live counts for active/total, expiring soon, application risk plus derived score | dashboard cards |
| Validity | lifetime length, <=398-day compliance, four buckets, monthly issuance, live 7/30/90-day expiry | validity pages/cards |
| CA | issuer distribution, self-signed count, country/validation matrix, multi-factor leaf ranking | CA analytics/ranking |
| Signature/hash | signature algorithm, hash family, key size/type, weak hashes, self-signed, compliance/strength, historical/issuer matrix | signature page |
| SAN | average/total SANs, single/multi/wildcard groups, count buckets, TLDs, referenced certificates | SAN page |
| Shared keys | group by public-key fingerprint across distinct certificate fingerprints, exposure/risk/context | shared-key pages and vulnerability context |
| Geography | derives country from domain final TLD and aggregates counts | map/country page |
| Trends | live monthly expiration, algorithm, validation, and key-size aggregation | trends page |
| Vulnerability | bounded candidate queries plus additive/clamped application score | vulnerability page |
| Encryption | live exact key algorithm/size counts | overview dashboard |

## Validity definitions

- Lifetime is derived from parsed validity length/dates.
- Compliance is the fraction with lifetime at most 398 days.
- Buckets are 0–90, 90–365, 365–730, and 730+ days.
- Precomputed documents store bounded certificate ID arrays for interactive filtering; near-expiry counts are queried live.

## Signature/hash strength

The precompute score is:

```text
strength = int(0.4 * key_score + 0.4 * hash_compliance_rate + 0.2 * algorithm_score)
```

Key-size contributions are 100 for >=4096, 80 for >=2048, 40 for >=1024, and 90 for >=256. Hash compliance counts SHA-256/384/512. Algorithm score starts at 85 and adds 0.15 times the ECDSA percentage, capped at 100. The result is clamped to 0–100. Because the size branches are algorithm-agnostic, a 256-bit EC key is rewarded through the >=256 branch, while unusual RSA sizes can also enter that branch; the score should be presented as project-defined.

## CA scoring details

The CA computation scans `is_leaf=true` documents, calculates ZLint penalties server-side, retains slim per-certificate columns, obtains per-scope 95th-percentile normalization, and performs an in-memory second scoring pass. It averages certificate scores per CA and stores sample count and five component averages.

Important methodology notes:

- 23 curated ZLint names count as critical; other errors cost 2 and warnings cost 1 before P95 normalization.
- max validity in key hygiene is 825 days.
- CA operational stability is fixed to mean(0, 0.5, 1) in the optimized per-certificate implementation.
- authority-access compliance is disabled and returns 0.5.
- a hard-coded risky-country set is `{IR, KP, SY, CU, RU}`.
- key reuse is order-dependent within a scope: first-seen fingerprint scores 1, later occurrences 0, missing key 0.5.
- the weak-key helper polarity and ECDSA/RSA threshold issue require disclosure.

The stored `ranking_formula`, P95 normalization, and scored leaf count improve provenance, but no external validation/calibration of this score is committed.

## SAN analytics

The computation extracts parsed names/SANs, counts totals and average, identifies single-name, multi-domain, and wildcard certificates, assigns count buckets, aggregates SAN TLDs, and stores bounded certificate references with `has_more` flags. API methods hydrate these references from the main collection for drill-down views.

## Shared-key analytics

Grouping requires a repeated public-key fingerprint across more than one distinct certificate fingerprint. Each group stores affected certificates/domains/SANs, key details, issuer diversity, sample values, and a LOW/MEDIUM/HIGH exposure label. Metadata provides total groups, certificates at risk, scanned certificates, and key counts. A shared public key demonstrates key reuse; it does not by itself demonstrate private-key compromise or unsafe cross-owner reuse.

The shared-key timeline API is not verified functional: its fast method reads `results_db.certificates` and a top-level `public_key_hash_sha256`, neither of which matches the canonical data model. The active shared-key page does not request this timeline.

## Geographic analytics

Country is inferred from the final label of `domain` through a static TLD-to-country map. This represents domain namespace geography, not verified server location, subject jurisdiction, or issuer location. The UI label “Issuer Countries” can therefore be misleading for the current implementation.

## Standalone exploratory reports

The `reports` folder contains additional investigations for lifecycle, expiration, SAN blast radius/clustering/toxic mix, shared keys, hash/signature algorithms, and ZLint. They are not integrated with the API and their output files are absent. One lifecycle HTML generator appears to expect field names different from those emitted by its aggregation script. These scripts can inform algorithm provenance or appendices, but uncommitted results must not appear as measured findings.
