# Report Outline and Documentation Plan

## Evidence-control rule

The official user-supplied title is **SSL Guardian: Large-Scale SSL Certificate Analytics Platform**. Other administrative fields are recorded in `report_metadata.md`.

Every technical paragraph drafted later must carry an internal evidence ID from `evidence_traceability.md` and a file/function citation in the chapter working notes. Evidence IDs may be removed from the final typeset prose only after the chapter consistency review confirms the claim. A section marked **Inference — approval required** cannot be drafted as fact; it must first be approved, narrowed, explicitly qualified, or removed.

## Target length

The original target was 44 pages including preliminary pages, references, and
concise appendices. This allocation is **Inference — approved as a planning
estimate** (I-024): it is based on the supplied template, not a repository
fact, and the compiled report may vary after figure placement.

| Part | Estimated pages |
|---|---:|
| Preliminary pages | 6 |
| Chapter 1 — Introduction | 3 |
| Chapter 2 — Technical Background and Related Work | 4 |
| Chapter 3 — Requirements and System Analysis | 3 |
| Chapter 4 — System Architecture and Data Design | 5 |
| Chapter 5 — Certificate Acquisition and Dataset Construction | 4 |
| Chapter 6 — Certificate Transparency Renewal and Discovery Pipeline | 4 |
| Chapter 7 — Analytics, API, and Dashboard Implementation | 6 |
| Chapter 8 — Verification, Security, and Discussion | 3 |
| Chapter 9 — Conclusion and Future Work | 2 |
| References | 2 |
| Appendices | 2 |
| **Total** | **44** |

## Proposed table of contents

### Preliminary pages

- Title Page
- Declaration
- Certification
- Acknowledgements
- Dedication
- Abstract
- Table of Contents
- List of Figures
- List of Tables
- List of Abbreviations

### Chapter 1 — Introduction

- 1.1 Background and Motivation
- 1.2 Problem Statement
- 1.3 Project Objectives
- 1.4 Implemented Contributions
- 1.5 Scope and Boundaries
- 1.6 Report Organization

### Chapter 2 — Technical Background and Related Work

- 2.1 TLS and X.509 Certificate Ecosystem
- 2.2 Certificate Transparency and Freshness
- 2.3 Certificate and Public-Key Reuse
- 2.4 Stale Certificates and Validity Periods
- 2.5 Related-Work Comparison
- 2.6 Repository-Grounded Research Gap

### Chapter 3 — Requirements and System Analysis

- 3.1 Stakeholders and Research Use Cases
- 3.2 Derived Functional Requirements
- 3.3 Derived Quality Attributes and Constraints
- 3.4 Technology Stack
- 3.5 Repository Module Decomposition
- 3.6 System Context

“Derived” is intentional: no formal requirements specification or stakeholder study is committed.

### Chapter 4 — System Architecture and Data Design

- 4.1 Architectural Overview
- 4.2 Component Responsibilities and Interfaces
- 4.3 Runtime/Deployment Topology
- 4.4 End-to-End Data Flow
- 4.5 MongoDB Data Model
- 4.6 Logical Scope Model
- 4.7 Indexing and Cache Strategy
- 4.8 Request and Response Sequence
- 4.9 Architectural Constraints

### Chapter 5 — Certificate Acquisition and Dataset Construction

- 5.1 Domain Dataset Preparation
- 5.2 Domain-Based Crawler Architecture
- 5.3 TLS Retrieval and zcertificate Parsing
- 5.4 Queue, Concurrency, Monitoring, and Recovery
- 5.5 Scope and Leaf Enrichment
- 5.6 Pakistan Domain Dataset Evidence
- 5.7 Experimental IP-Based Crawler
- 5.8 Acquisition Limitations and Ethics Gap

### Chapter 6 — Certificate Transparency Renewal and Discovery Pipeline

- 6.1 CT Collection Configuration and Checkpoints
- 6.2 WebSocket-to-Mongo Ingestion
- 6.3 Eight-Stage Orchestrator
- 6.4 Known-Domain Renewal Detection and Crawl
- 6.5 Checkpointed Renewal Merge
- 6.6 New-Domain Discovery and Corpus Growth
- 6.7 Precompute Integration
- 6.8 Failure Recovery and Correctness Limitations

### Chapter 7 — Analytics, API, and Dashboard Implementation

- 7.1 Generic Precomputation Framework
- 7.2 Validity and Geographic Analytics
- 7.3 Signature, Hash, and Encryption Analytics
- 7.4 SAN Analytics
- 7.5 Shared-Key Analytics
- 7.6 CA Analytics and Ranking Formula
- 7.7 Vulnerability Risk Model
- 7.8 Live Trend Analytics
- 7.9 Django API Design and Filtering
- 7.10 Frontend Architecture and State Management
- 7.11 Dashboard Pages and Certificate Drill-Down

### Chapter 8 — Verification, Security, and Discussion

- 8.1 Verification Method
- 8.2 Static and Structural Check Results
- 8.3 Repository Experiment Evidence
- 8.4 Security Analysis
- 8.5 Performance/Scalability Mechanisms Without Benchmark Claims
- 8.6 Implementation Limitations and Configuration Drift
- 8.7 Threats to Validity

### Chapter 9 — Conclusion and Future Work

- 9.1 Conclusion
- 9.2 Repository-Supported Future Work

### References

IEEE-style bibliography using verified metadata only.

### Appendices

- Appendix A — API Endpoint Reference
- Appendix B — Configuration, Collections, and Selected Code Listings

## Chapter mapping

| Chapter | Folders/files | APIs | Collections | Images/resources |
|---|---|---|---|---|
| 1 | root README/config plus verified modules | high-level catalog | all at context level | system context diagram |
| 2 | `research-papers`, CT/crawler/analytics code for project comparison | none | none | related-work comparison table |
| 3 | entire first-party hierarchy, manifests/config | grouped API capabilities | data-store inventory | system context; module/stack tables |
| 4 | `db.py`, middleware, cache, settings, index script, serializers | shared request flow/scope endpoints | main, six results, CT/staging, Redis, SQLite | architecture, deployment, schema, request sequence |
| 5 | both crawler folders and dataset scripts/files | none | main/queue and separate IP stores | crawler/dataset/IP diagrams; data tables |
| 6 | all CT pipeline scripts/config/checkpoint | none directly; precompute invoked | go-server, data-renew, new-data, main/checkpoint | existing automation figure plus new sequence |
| 7 | feature backend packages, precompute scripts, frontend `src` | full active endpoint set | main and results | four recording stills plus analytics/frontend diagrams |
| 8 | settings, lint/type results, IP `results.txt`, limitations across code | security/API review | runtime shape verification only | verification/security/limitations tables |
| 9 | verified gaps in code/config/tests/deployment | none | none | no new figure required |
| Appendices | URL/config/module files | full endpoint table | field/collection summaries | selected short listings only |

## Planned code listings

Only short, explanatory excerpts should be used:

1. atomic domain queue claim and state transition;
2. scoped collection query injection;
3. checkpointed renewal replacement batch;
4. precomputed scope document selection;
5. vulnerability signal scoring or CA formula description.

Every later listing must have a caption, label, language, and file/function attribution. Full files will not be pasted.

## Section-level evidence traceability

| Section | Classification | Evidence IDs and repository source | Drafting constraint |
|---|---|---|---|
| 1.1 Background and Motivation | Inference — approved and bounded | I-001; V-001, V-034 | Motive is project framing, not a measured need |
| 1.2 Problem Statement | Inference — approved and bounded | I-001; acquisition/CT/analytics modules | Formal problem statement does not exist in repository |
| 1.3 Project Objectives | Inference — approved and bounded | I-002; V-001 | Objectives are reconstructed from implementation |
| 1.4 Implemented Contributions | Inference — approved and bounded | I-003; V-001, V-009–V-025 | “Contribution” is evaluative; implementation items are verified |
| 1.5 Scope and Boundaries | Verified from repository | V-001, V-008, V-015, V-027–V-030 | State only implemented and explicitly absent elements |
| 1.6 Report Organization | Inference — approved and bounded | I-024; this outline | Planning statement only |
| 2.1 TLS and X.509 Certificate Ecosystem | Verified from repository | V-034; local paper PDFs | Restrict factual claims to verified citations |
| 2.2 Certificate Transparency and Freshness | Verified from repository | V-009–V-013, V-034 | Separate CT implementation facts from freshness benefit I-008 |
| 2.3 Certificate and Public-Key Reuse | Verified from repository | V-025, V-034 | Do not equate reuse with compromise without approved I-021 citation |
| 2.4 Stale Certificates and Validity Periods | Verified from repository | V-025, V-034 | Standards/policy claims require exact paper/standard citation |
| 2.5 Related-Work Comparison | Verified from repository | V-034; three local PDFs | Compare only documented methods/findings |
| 2.6 Repository-Grounded Research Gap | Inference — approved and bounded | I-028; V-001, V-034 | Repository-grounded synthesis; no measured outcome claim |
| 3.1 Stakeholders and Research Use Cases | Inference — approved and bounded | I-004; frontend/analytics behavior | Roles are derived; no stakeholder study or authorization-role claim |
| 3.2 Derived Functional Requirements | Inference — approved and bounded | I-005; V-001–V-025 | Titled and worded as derived requirements |
| 3.3 Derived Quality Attributes and Constraints | Inference — approved and bounded | I-006, I-009; indexes/cache/checkpoints/UI | Mechanisms are verified; outcomes remain unmeasured |
| 3.4 Technology Stack | Verified from repository | package/requirements/import/config evidence; V-018, V-022 | Versions only where manifests specify them |
| 3.5 Repository Module Decomposition | Verified from repository | V-001; `repository_structure.md`, `module_analysis.md` | Preserve active/legacy/experimental boundaries |
| 3.6 System Context | Inference — approved and bounded | I-025; V-001, V-004–V-005, V-009, V-016–V-020, V-022 | Generated arrows were reviewed against code evidence; no production topology claim |
| 4.1 Architectural Overview | Inference — approved and bounded | I-007; V-001, V-018, V-022 | Architecture label is interpretive; component boundaries and arrows were checked against repository interfaces |
| 4.2 Component Responsibilities and Interfaces | Verified from repository | V-004, V-009–V-022 | Map each component to concrete files |
| 4.3 Runtime/Deployment Topology | Inference — approved and bounded | I-025; V-002, V-020, configured ports | Called repository-configured local topology, not deployed production |
| 4.4 End-to-End Data Flow | Verified from repository | V-004, V-009–V-015, V-018–V-022 | Show implemented calls/files only |
| 4.5 MongoDB Data Model | Verified from repository | V-016, V-017; crawler/precompute/query code | Exclude uncommitted runtime counts |
| 4.6 Logical Scope Model | Verified from repository | V-003, V-019 | Distinguish physical database pair from logical scope |
| 4.7 Indexing and Cache Strategy | Verified from repository | V-014, V-020 | Describe mechanisms; benefit claims move to I-009 |
| 4.8 Request and Response Sequence | Verified from repository | V-018–V-022 | Do not imply request isolation not present in code |
| 4.9 Architectural Constraints | Inference — approved and bounded | I-010–I-016, I-022; V-027–V-030 | Repository facts and inferred consequences are explicitly separated and qualified |
| 5.1 Domain Dataset Preparation | Inference — approved and bounded | I-018; dataset scripts and V-031 | Describes available scripts and committed outputs; explicitly excludes a complete final-CSV lineage claim |
| 5.2 Domain-Based Crawler Architecture | Verified from repository | V-004, V-006 | Implemented control structure only |
| 5.3 TLS Retrieval and zcertificate Parsing | Verified from repository | V-004, V-005 | Rationale for disabled verification is I-013 |
| 5.4 Queue, Concurrency, Monitoring, and Recovery | Verified from repository | V-004, V-006 | Say “implemented recovery logic,” not proven recovery guarantee |
| 5.5 Scope and Leaf Enrichment | Verified from repository | V-003, V-007 | Use exact extraction/classification code |
| 5.6 Pakistan Domain Dataset Evidence | Verified from repository | V-031 | Report committed row counts only |
| 5.7 Experimental IP-Based Crawler | Verified from repository | V-008, V-032 | Separate code description from result interpretation I-017 |
| 5.8 Acquisition Limitations and Ethics Gap | Inference — approved and bounded | I-013, I-018, I-022; absence evidence V-029–V-030 | Separates verified absences and drift from conditional deployment guidance; SNI result interpretation I-017 is excluded |
| 6.1 CT Collection Configuration and Checkpoints | Verified from repository | V-009; `config.yml`, `ct_index.json` | Do not claim checkpoint effectiveness beyond implemented state |
| 6.2 WebSocket-to-Mongo Ingestion | Verified from repository | V-009 | Use exact endpoint, batch, index, and fields |
| 6.3 Eight-Stage Orchestrator | Verified from repository | V-010 | Present source order exactly |
| 6.4 Known-Domain Renewal Detection and Crawl | Verified from repository | V-011, V-004 | Use intended branch behavior, no success-rate claim |
| 6.5 Checkpointed Renewal Merge | Verified from repository | V-012 | Retry/correctness benefits require qualification |
| 6.6 New-Domain Discovery and Corpus Growth | Verified from repository | V-013 | “Growth” means implemented insertion/CSV update, not measured growth |
| 6.7 Precompute Integration | Verified from repository | V-010, V-014 | Invocation and result contracts only |
| 6.8 Failure Recovery and Correctness Limitations | Inference — approved and bounded | I-011, I-012; V-009–V-014 | Chapter 6 reports static-analysis risks conditionally and makes no observed-failure or recovery-effectiveness claim |
| 7.1 Generic Precomputation Framework | Verified from repository | V-014, V-015 | No performance claim |
| 7.2 Validity and Geographic Analytics | Verified from repository | V-025, V-026 | Chapter 7 reports domain-suffix grouping directly and does not make the I-019 critique |
| 7.3 Signature, Hash, and Encryption Analytics | Verified from repository | V-025 | Formula is project-defined; validation judgment is I-020 |
| 7.4 SAN Analytics | Verified from repository | V-015, V-025 | Use exact buckets/references from code |
| 7.5 Shared-Key Analytics | Verified from repository | V-025 | Chapter 7 describes public-key-fingerprint grouping only; no compromise/ownership conclusion is made |
| 7.6 CA Analytics and Ranking Formula | Verified from repository | V-025 | Exact application-defined formula is presented; methodological evaluation remains outside Chapter 7 |
| 7.7 Vulnerability Risk Model | Verified from repository | V-025 | Presented as an application-defined score, not an externally standardized or validated score |
| 7.8 Live Trend Analytics | Verified from repository | V-015 | Do not call forecasts predictive models beyond query behavior |
| 7.9 Django API Design and Filtering | Verified from repository | V-018, V-019, V-021, V-028 | Distinguish routed endpoints from statically inconsistent ones |
| 7.10 Frontend Architecture and State Management | Verified from repository | V-022–V-024 | Use actual contexts/client/pages |
| 7.11 Dashboard Pages and Certificate Drill-Down | Verified from repository | V-022, V-033 | Description is source-derived; recording screenshots were excluded because I-026 remains unapproved |
| 8.1 Verification Method | Verified from repository | V-036; recorded commands | Clarify static versus runtime checks |
| 8.2 Static and Structural Check Results | Verified from repository | V-028, V-036 | No claim that passing parse/type checks proves behavior |
| 8.3 Repository Experiment Evidence | Inference — approved and bounded | I-017; V-031, V-032 | Chapter 8 transcribes the committed counts but makes no causal, population, or general SNI claim |
| 8.4 Security Analysis | Inference — approved and bounded | I-010, I-022; V-005, V-019, V-027 | Settings/behavior facts are separated from conditional impact and controls |
| 8.5 Performance/Scalability Mechanisms Without Benchmark Claims | Inference — approved and bounded | I-009; V-006, V-009, V-014, V-020 | Mechanisms only; source-comment timings and improvement magnitudes are excluded |
| 8.6 Implementation Limitations and Configuration Drift | Inference — approved and bounded | I-011–I-020; V-028, V-029 | Direct inconsistencies are verified; unexecuted consequences remain conditional |
| 8.7 Threats to Validity | Inference — approved and bounded | I-017–I-021, I-028 | Explicit analytical discussion introduces no new implementation or outcome claim |
| 9.1 Conclusion | Inference — approved and bounded | I-028; approved preceding findings | Synthesis introduces no new implementation, runtime, performance, or scientific claim |
| 9.2 Repository-Supported Future Work | Inference — approved and bounded | I-023; V-023–V-030; Chapter 8 limitations | Every item remains an explicitly proposed action rather than an implemented capability |
| Appendix A — API Endpoint Reference | Verified from repository | V-021, V-028 | Mark known inconsistent routes |
| Appendix B — Configuration, Collections, and Listings | Verified from repository | V-002, V-016, V-017, V-029 | Exact excerpts/paths only |
