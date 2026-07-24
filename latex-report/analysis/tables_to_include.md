# Table Plan

| No. | Chapter/section | Table | Classification | Repository basis/constraint |
|---:|---|---|---|---|
| 1 | Ch. 1, Scope | Implemented project scope and explicit exclusions | Verified from repository | V-001, V-008, V-015, V-027–V-030 |
| 2 | Ch. 2, Related Work | Comparison of three local research papers | Verified from repository | V-034; exact cited claims only |
| 3 | Ch. 3, Requirements | Derived functional requirements and implementing modules | Inference — approved and bounded | I-005; explicitly labelled as derived from implementation |
| 4 | Ch. 3, Quality Attributes | Derived quality attributes, evidence, and limits | Inference — approved and bounded | I-006, I-009; mechanisms separated from unmeasured outcomes |
| 5 | Ch. 3, Technology Stack | languages/frameworks/libraries/services | Verified from repository | manifests/imports/configuration |
| 6 | Ch. 3, Repository Modules | folder responsibilities and relationships | Verified from repository | V-001 and repository inventory |
| 7 | Ch. 4, MongoDB Collections | main/result/staging/cache stores and purpose | Verified from repository | V-016, V-017; code contracts only |
| 8 | Ch. 4, Main Certificate Fields | fields, producer, consumer | Verified from repository | V-016 |
| 9 | Ch. 4, Result Schemas | six result families and field groups | Verified from repository | V-017; exclude local runtime counts |
| 10 | Ch. 4, Index Strategy | index categories and supported query paths | Verified from repository | generic index script |
| 11 | Ch. 5, Crawler Design | active variants plus queue states/transitions | Verified from repository | V-004–V-006 |
| 12 | Ch. 5, Dataset Evidence | committed CSV/APNIC resource rows and role | Verified from repository | V-031 |
| 13 | Ch. 5, IP Experiment Counts | exact SNI/no-SNI recorded outcomes | Inference — excluded | V-032 counts exist, but Chapter 5 excludes them because protocol and reproducibility metadata are incomplete |
| 14 | Ch. 6, CT Orchestration Steps | eight steps, input, output, state | Verified from repository | V-010 |
| 15 | Ch. 6, CT Collections/States | CT/staging fields and lifecycle | Verified from repository | V-009–V-013 |
| 16 | Ch. 7, API Catalog | endpoint groups, methods, consumers | Verified from repository | V-021, V-028; inconsistent routes marked |
| 17 | Ch. 7, Frontend Route/API Map | page, feature, API source | Verified from repository | V-022–V-024 |
| 18 | Ch. 7, Analytics Definitions | metric, formula/bucket, source, freshness mode | Verified from repository | V-025, V-026 |
| 19 | Ch. 7, CA Score Components | implemented component functions and formula caveats | Verified from repository | V-025; scientific evaluation excluded |
| 20 | Ch. 7, Vulnerability Score | implemented signal points and thresholds | Verified from repository | V-025; application-defined label |
| 21 | Ch. 8, Verification Results | Python parse, TypeScript, ESLint, structural checks | Verified from repository | V-036; static scope and unavailable Django runtime stated |
| 22 | Ch. 8, IP Experiment Record | exact committed no-SNI/SNI outcome categories | Inference — approved and bounded | I-017, V-032; descriptive transcription only, no causal or general claim |
| 23 | Ch. 8, Security Review | mechanism, evidence, inferred impact and control boundary | Inference — approved and bounded | I-010, I-022; direct facts separated from conditional analysis |
| 24 | Ch. 8, Performance Mechanisms | batching, indexing, materialization, cache, pagination, SWR | Inference — approved and bounded | I-009; mechanisms reported without benchmark claims |
| 25 | Ch. 8, Known Limitations | verified inconsistency plus inferred consequence | Inference — approved and bounded | V-028–V-030; I-011–I-020; runtime failures not asserted |
| 26 | Ch. 9, Conclusion | Objective assessment against repository evidence | Inference — approved and bounded | I-028; synthesis of previously verified or approved chapter findings; no new outcome claim |
| 27 | Ch. 9, Future Work | Prioritized repository-supported future-work roadmap | Inference — approved and bounded | I-023; V-023–V-030 and Chapter 8 limitations; proposals only |
| 28 | Appendix A | Full endpoint reference | Verified from repository | V-021, V-028 |
| 29 | Appendix B | Configuration/file map | Verified from repository | V-002, V-016, V-017, V-029 |

Hardware requirement and performance-result tables are deliberately omitted because the repository contains neither specified hardware requirements nor reproducible benchmark results.
