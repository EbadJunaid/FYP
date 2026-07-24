# Official FYP-II Template Formatting Audit

## Authority and method

**Verified from supplied document.** The formatting authority is
`C:\Users\Iqra Shafi\Downloads\FYP-II Report.docx` (38,883 bytes, supplied
14 July 2026). Microsoft Word reported 14 rendered pages, one section, 318
paragraphs, no tables, two inline logo instances, no floating shapes, and no
page-number fields. Measurements below were read through Word's document model
and cross-checked against the DOCX package. The former custom LaTeX formatting
is not treated as authoritative.

## Page layout

| Property | Official template | Former LaTeX | Correction |
|---|---:|---:|---|
| Paper | A4, 595.45 x 841.70 pt | A4 | Retained A4 |
| Top margin | 70.90 pt (2.5 cm) | 72 pt (1 in) | Set to 2.5 cm |
| Bottom margin | 70.90 pt (2.5 cm) | 72 pt (1 in) | Set to 2.5 cm |
| Left margin | 85.05 pt (3.0 cm) | 84.96 pt (1.18 in) | Set to 3.0 cm |
| Right margin | 70.90 pt (2.5 cm) | 72 pt (1 in) | Set to 2.5 cm |
| Header distance | 35.45 pt (1.25 cm) | Custom 15 pt header height | Set to the template geometry; no header content |
| Footer distance | 35.45 pt (1.25 cm) | Centred page number | Set to 1.25 cm; centred numbers enabled only where requested |
| Printed page numbers | None | Roman front matter and Arabic chapter numbers printed at centre | User override: none through dedication; Roman from the Table of Contents; Arabic restarted at Chapter One |

## Typography and paragraph formatting

| Property | Official template | Former LaTeX | Correction |
|---|---|---|---|
| Main face | Times New Roman | New TX Times-like face | Retained New TX, the closest standard pdfLaTeX/Overleaf equivalent |
| Body size | 12 pt | 12 pt | Retained |
| Body alignment | Justified | Generally justified but with a 0.5 in first-line indent | Set globally justified with zero first-line indent |
| Body line spacing | 1.5 (18 pt for 12 pt text) | 1.5 | Retained |
| Paragraph spacing | 0 pt before/after | 0 pt | Retained |
| Front-matter headings | 16 pt, bold, centred, uppercase | Generic report-class chapter pages | Replaced with consistent centred headings, balanced 30 pt below the top text margin by user request |
| Technical headings | Template guideline states Times New Roman 16 pt | Sections 14 pt; subsections 12 pt | All heading levels set to 16 pt |
| Captions | 9 pt, italic, regular label, 10 pt after | Small, bold label, centred | Set to 9 pt italic without bold label |

## Front-matter structure

| Page | Official template structure | Former LaTeX difference | Correction |
|---:|---|---|---|
| 1 | Project title; full-width 0.75 pt rules; centred logo; `BSCS COMPUTER SCIENCE`; student rows; department, university, and location | Invented university-first cover, report subtitle, supervisor block, date | Uses the official sequence and rule positions with the two user-supplied students |
| 2 | Centred logo; project title; exact partial-fulfilment wording; student rows; supervisor, co-supervisor, committee | Invented degree/submission page without logo and with different wording | Uses the official sequence with the supplied students, supervisor, co-supervisor, and three committee members |
| 3 | `DECLARATION`; declaration paragraph; student signatures; date | Originally followed a blank third page and contained four student slots | Blank page removed and declaration reduced to the two supplied students |
| 4 | Approval statement with no page heading; supervisor, co-supervisor, committee members, department head | Invented `Certification` heading and different wording/layout | Uses the official heading-free signature layout, extended by user request to three committee members |
| 5 | `ACKNOWLEDGEMENT`; otherwise blank | Plural heading and invented placeholder prose | Uses the singular heading, user-supplied text, and centred Thuluth-style Bismillah below the heading |
| 6 | `DEDICATION`; otherwise blank | Invented placeholder sentence | Uses the user-supplied quotation and dedication text while retaining the template page structure |
| 7-11 | Table of contents, tables, figures, abbreviations, abstract, in that order | Same broad order but generic report styling | Retained order and applied verified heading/list styles |
| 12 | `CHAPTER ONE` in 16 pt bold centred text | `CHAPTER 1` plus a separate uppercase `INTRODUCTION` title | User-requested global style prints the number as a word and the chapter title on the next centred line |

### Verified placement measurements

Word reports vertical positions from the top of the physical A4 page. On the
cover, the title begins at 103.2 pt, the first rule follows the title, the logo
begins at 178.2 pt, the programme line at 440.4 pt, the two student rows at
488.4 and 504.6 pt, the second rule retains its template position, and the three
institutional lines remain at 674.4, 702.0, and 729.6 pt. On the submission page, the logo begins at
70.8 pt, the title at 337.2 pt, the submission statement at 424.8 pt, student
rows at 505.2 and 521.4 pt, supervisor at 601.8 pt, co-supervisor at 649.8 pt, and
committee line at 714.6 pt. In the source template, declaration, acknowledgement,
dedication, contents, list, abstract, and chapter headings begin at the 70.8 pt
top text margin. The final user override places major front-matter headings a
consistent 30 pt below that margin for improved vertical balance. The LaTeX
front-matter files otherwise use fixed vertical measurements derived from these
positions instead of `\vfill`-based redesigns, except for the cover's flexible
gap before its fixed bottom institutional block.

## Contents and list styles

**Verified from the Word style definitions.** TOC levels 1-3 use 12 pt Times
New Roman, regular weight, single line spacing, and 5 pt after each entry.
Levels 2 and 3 have left indents of 12 pt and 24 pt. The `Table of Figures`
style is 12 pt regular. A final user override makes only numbered chapter labels
and titles bold and renders them as `1 Introduction`; section and subsection
entries remain regular. Declaration, Approval/Certification, Acknowledgement,
and Dedication were removed from the contents list by final user request, while
the underlying front-matter pages remain unchanged. The LaTeX `tocloft` settings
reproduce these values and overrides.

## Logo

**Verified from repository and template.** The supplied logo is
`figures-and-poster/Screenshot 2026-07-14 175212.png`. It is copied to
`docs/fyp-report/assets/itu-logo.png`. Both Word logo boxes are centred and
228.8 pt high and 161.35 pt wide. The supplied 217 x 307 pixel logo has a
0.7068 aspect ratio; at the verified height its proportional LaTeX width is
approximately 161.7 pt. This reproduces the Word placement to within less than
half a point without distorting the supplied logo.

## Remaining constrained inferences

1. **Inference:** The template contains no populated section or subsection
   specimen. Its guideline page explicitly states that report headings use
   16 pt Times New Roman. Section and subsection headings therefore use 16 pt,
   bold, left-aligned text while retaining decimal numbering.
2. **Inference:** The template contains no actual caption instance, but its
   built-in `Caption` style is 9 pt Times New Roman italic. LaTeX applies that
   verified style to generated captions.
3. **User-supplied override:** Although the template has no printed page-number
   field, LaTeX suppresses numbering only through dedication, starts visible
   Roman numbering at the Table of Contents, and restarts visible Arabic
   numbering at Chapter One.
4. **User-supplied override:** The report has exactly two students: Ebad Junaid
   (22046) and Muhammad Arslan Shafi (22100), both in session BSCS 2022--2026.
   All third/fourth-student fields were removed. The supplied supervisor,
   co-supervisor, three committee members, and department head are populated;
   the declaration uses the explicitly requested dotted date field.
5. **User-supplied override:** Every numbered chapter prints `CHAPTER` plus the
   number in uppercase words and prints the title on the next centred line. The
   reusable `titlesec` definition applies this to current and future chapters.

The final guideline page from the Word document is an instruction page, not
report content, and is therefore not included in the LaTeX report.
