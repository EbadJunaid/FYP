# Figure Plan

## Planned figures and exact placement

| No. | Chapter/section | Figure | Source/type | Classification | Evidence/approval note |
|---:|---|---|---|---|---|
| 1 | Ch. 3, System Context | Project system context: acquisition, CT, analytics, API, dashboard | new vector diagram | Inference — approved and bounded | I-025; arrows reviewed against V-004–V-005, V-009, V-016–V-020, and V-022 |
| 2 | Ch. 4, Overall Architecture | End-to-end component architecture | new vector diagram | Inference — approved and bounded | I-007, I-025; generated from verified component interfaces and presented as an architectural abstraction |
| 3 | Ch. 4, Runtime Topology | Repository-configured local runtime topology and ports | new deployment-style diagram | Inference — approved and bounded | I-025; ports/config are verified and the caption explicitly avoids a production-deployment claim |
| 4 | Ch. 4, Data Design | Logical MongoDB collection/schema diagram | new database diagram | Verified from repository | V-016, V-017; use code-built schemas, no local document counts |
| 5 | Ch. 4, Request Processing | Scoped request, cache, live/precomputed query sequence | new sequence diagram | Verified from repository | V-018–V-022; exact call path only |
| 6 | Ch. 5, Domain Acquisition | Implemented crawler activity and recovery-control flow | new activity diagram | Verified from repository | V-004–V-007; no guarantee that recovery succeeds in every failure mode |
| 7 | Ch. 5, Dataset Construction | Possible dataset-preparation/provenance flow | not generated | Inference — excluded | I-018; scripts exist, but final CSV lineage is not recorded, so Chapter 5 uses a bounded evidence table instead |
| 8 | Ch. 5, IP Experiment | APNIC-to-CIDR and implemented SNI/no-SNI scan flow | new flow diagram | Verified from repository | V-008; result interpretation excluded from diagram |
| 9 | Ch. 6, Orchestration | Eight-step CT renewal automation | new vector diagram | Verified from repository | V-010; redrawn from the active orchestrator rather than reusing `automation-lucid.png` |
| 10 | Ch. 6, Detailed CT Flow | Implemented known-renewal versus new-domain branch sequence | new sequence diagram | Verified from repository | V-009–V-013 |
| 11 | Ch. 7, Analytics Materialization | Indexing and six-family precompute pipeline | new component/data-flow diagram | Verified from repository | V-014, V-015 |
| 12 | Ch. 7, Frontend Architecture | pages, contexts, client, components, API | new component diagram | Verified from repository | V-022–V-024 |
| 13 | Ch. 7, Dashboard | Dashboard overview and certificate table | not included | Inference — excluded | I-026 remains unapproved; no recording still was used |
| 14 | Ch. 7, Validity Analytics | validity statistics/trend interface | not included | Inference — excluded | I-026 remains unapproved; no recording still was used |
| 15 | Ch. 7, Certificate Detail | parsed certificate/ZLint detail interface | not included | Inference — excluded | I-026 remains unapproved; no recording still was used |
| 16 | Ch. 7, Trend Analytics | trends interface | not included | Inference — excluded | I-026 remains unapproved; no recording still was used |
| 17 | Ch. 7, Shared-Key Analysis | public-key grouping and drill-down data flow | new sequence/data diagram | Verified from repository | V-025; no compromise/ownership interpretation |
| 18 | Ch. 7, Vulnerability Model | implemented additive signals and thresholds | new decision/activity diagram | Verified from repository | V-025; label as application-defined |

## Diagrams list

- system context diagram;
- component architecture diagram;
- deployment/runtime topology diagram;
- MongoDB logical schema diagram;
- API/request sequence diagram;
- domain crawler activity diagram;
- dataset construction flowchart;
- IP crawler flowchart;
- CT renewal/discovery sequence diagram;
- analytics precompute data-flow diagram;
- frontend component diagram;
- shared-key data-flow diagram;
- vulnerability scoring activity/decision diagram.

## Exclusions

- No conventional class diagram is planned because the important structure is package/data-flow oriented and most behavior is in static query/controller helpers; a forced class diagram would add little beyond the module table.
- No cloud deployment diagram is planned because no cloud/container deployment exists in the repository.
- `397-days.png`, the old recording, inaccurate crawler images, and unverified poster are excluded.

## Figures awaiting explicit approval

- **Figure 1:** approved and generated for Chapter 3 with the bounded context described above.
- **Figures 2–3:** approved and generated for Chapter 4 as bounded abstractions; neither is presented as evidence of a production deployment.
- **Figures 6 and 8:** generated for Chapter 5 from the verified crawler and APNIC/IP-scanner control paths.
- **Figure 7:** excluded from Chapter 5 because actual final-CSV lineage is unproven (I-018); a table separates implemented utilities from committed output evidence.
- **Figures 9–10:** generated for Chapter 6 directly from the active CT ingestion,
  orchestration, renewal, and discovery source paths (V-009–V-013). The existing
  `automation-lucid.png` was not reused, so I-027 does not affect the chapter.
- **Figures 11, 12, 17, and 18:** generated for Chapter 7 from the verified
  materialization, frontend, shared-key, and vulnerability paths. Their captions
  avoid benchmark, compromise, ownership, or scientific-validation claims.
- **Figures 13–16:** excluded from Chapter 7 because I-026 remains unapproved;
  no unversioned recording still was treated as current repository evidence.
