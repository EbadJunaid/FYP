# Resource Analysis

## Evidence classification

File existence, dimensions, text/content, and recording properties are **Verified from repository** (V-031–V-034, V-037 where applicable). Decisions to include, exclude, call a recording “current,” or treat an existing diagram as sufficiently accurate are editorial **Inference**. Screenshot currentness and reuse of `automation-lucid.png` therefore await approval under I-026 and I-027.

## Diagrams and images

| Resource | Assessment | Decision |
|---|---|---|
| `figures/automation-lucid.png` (4621x3311) | Clear current eight-step renewal pipeline and active 792k database label; aligns most closely with `main.py` | Include once in CT chapter, with code-verified caption and limitations noted |
| `automation-excali-dark/light.*` | Editable/high-resolution but contains older naming/flow details | Use only as a design source if redrawn; do not include unchanged |
| `automation-mermaid.*` | Useful editable structure but older orchestration statements | Redraw from current code |
| `domain-based.png` | Concise crawler flow but states unique SHA-256 behavior not guaranteed by `crawler-args.py` | Exclude unchanged; replace with verified vector flow |
| `domain-based-crawler.*` | High resolution but labels parsing as ZLint and visually joins IP output to the main database, unlike code | Exclude unchanged; replace |
| `go-server.*` | Explains CT collection but contains a broad certificate-log statement without local source attribution | Exclude unchanged; redraw with exact config/code |
| `pk-dataset-story.*` | Historical dataset-story visual; omits some current sources/integration | Use editable source only for a corrected dataset-provenance diagram |
| `397-days.png` | Time-sensitive policy timeline ending in 2029; not established by repository code/papers | Exclude unless independently verified from an authoritative citation during report writing |
| `icons/locked-padlock.png` | Application branding/icon | Optional title/header branding only; not a technical figure |
| default Next/Vercel SVG assets | Scaffold assets, not project evidence | Exclude |
| `poster.pdf` | Project poster resource; headless local rasterization produced a blank preview and Word rejected its oversized page | Do not use as a report figure without a reliable visual/content review |

## Recordings and screenshot sources

| Recording | Technical properties | Content | Decision |
|---|---|---|---|
| `fyp-1-presentation.mp4` | H.264/AAC, 1920x1080, 97.22 s | current dark UI: dashboard overview/table, validity views, certificate detail, trends | Include four cropped high-resolution stills |
| `fyp-rec-edit.mp4` | H.264/AAC, 854x480, 155.99 s | older green interface and database view | Exclude as obsolete |

Planned stills from the current recording are dashboard overview, validity analytics, certificate detail, and trend analytics. Exact timestamps/crops should be selected during the LaTeX chapter stage and checked against current page code.

## Data resources

- `global-dataset.csv`: usable as corpus-size/input evidence; 707,084 data rows at scan time.
- `pk-domains.csv`: usable as processed Pakistan-domain evidence; 8,185 data rows.
- APNIC global/Pakistan/CIDR files: usable to explain deterministic IP range preparation.
- `mini-dataset.csv` and mini IP ranges: development/test inputs, not research-scale results.
- `failed-domains.csv`: a local failure sample without run metadata; exclude from quantitative findings.
- `ct_index.json`: useful to explain checkpoint persistence, not suitable as a figure.
- `config.yml`/JSON files: include selected fields in tables/listings, not screenshots.

## Research papers

1. *Measuring and Characterizing Propagation of Reuse RSA Certificates and Keys across PKI Ecosystem* — relevant to certificate/public-key reuse motivation and ecosystem-scale context.
2. *Analyzing shared keys in X.509 certificates with domain ownership* (International Journal of Information Security, 2025; DOI present in the PDF) — directly relevant to distinguishing shared keys from unsafe cross-owner reuse.
3. *Stale TLS Certificates: Investigating Precarious Third-Party Access to Valid TLS Keys* (IMC 2023) — relevant to certificate freshness, CT monitoring, and shorter lifetimes.

Only bibliographic facts and findings directly supported by the local PDFs may be cited. Exact BibTeX metadata must be verified when the bibliography is generated.

## Standalone report resources

The `reports` directory contains analysis source, not committed finished results. It can support descriptions of explored dimensions—expiry, SAN blast radius, shared keys, signatures, hashes, and ZLint—but numerical charts/tables must not be invented. The final report should prefer dashboard/precompute implementations over disconnected exploratory scripts.
