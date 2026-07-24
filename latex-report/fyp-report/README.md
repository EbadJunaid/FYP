# SSL Guardian FYP Report - Official-template Chapters 1-9 Build

This Overleaf-compatible project contains the official-template front matter,
the approved Chapters 1 through 9, and only their cited references. The planned
report chapters are now complete; appendices remain ungenerated.

## Overleaf

1. Upload the complete contents of this directory as one Overleaf project.
2. Set `main.tex` as the main document.
3. Select **pdfLaTeX** as the compiler.
4. Compile normally; Overleaf will run BibTeX as required.

The ITU logo used by the report is stored at `assets/itu-logo.png`. It was
copied from `figures-and-poster/Screenshot 2026-07-14 175212.png` and is scaled
proportionally at the two positions used by the official Word template.

## Local compile sequence

```text
pdflatex main.tex
bibtex main
pdflatex main.tex
pdflatex main.tex
```

## Official-template fidelity

The formatting source of truth is `FYP-II Report.docx`. The LaTeX uses its A4
geometry, front-matter wording, logo placements, cover rules,
heading sizes, line spacing, contents-entry styles, and caption style. By the
final user-supplied numbering rule, the cover through dedication remain
unnumbered, the Table of Contents begins Roman numbering at i, and Chapter One
restarts Arabic numbering at 1. The template's blank third page remains removed.
The detailed comparison is recorded
in `../analysis/template_format_audit.md`.

## Administrative metadata

The two supplied students are Ebad Junaid (22046) and Muhammad Arslan Shafi
(22100), both in session BSCS 2022--2026. The supervisor is Dr. Muhammad Umar
Janjua. The committee members are Dr.
Mr Kashif Junaid and Mr. Shoaib Majeed; the Head of
Department is Dr. Ali Ahmed. The declaration retains a dotted date field because
no fixed submission date was requested.
The acknowledgement and dedication contain the text supplied after the initial
template build. The calligraphic acknowledgement invocation is included as
`assets/bismillah.pdf`; its editable LaTeX source is
`assets/bismillah.tex`. The final abstract remains blank beneath its official
heading because no abstract text has yet been supplied.

## Evidence traceability

LaTeX comments in the generated chapter files map every technical paragraph or list
to IDs in `../analysis/evidence_traceability.md` and to repository files. These
comments do not appear in the PDF.
