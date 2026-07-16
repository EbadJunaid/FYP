# Supplied Report Template Analysis

## Files reviewed

- `C:\Users\Iqra Shafi\Downloads\FYP-II Report.docx`
- `C:\Users\Iqra Shafi\Desktop\draft_report_fyp.pdf`

The DOCX is a university-style skeleton/guideline. The PDF is a 65-page report for a different project and was used only to understand applied structure and density. No wording will be copied.

## DOCX formatting requirements

| Property | Observed value/guidance |
|---|---|
| Page size | A4 |
| Margins | approximately 1 inch top/right/bottom and 1.18 inches left |
| Body font | Times New Roman, 12 pt |
| Heading font | Times New Roman, 16 pt |
| Line spacing | 1.5 |
| Referencing | IEEE style |
| Appendices | lettered appendices (for example A and B) |

The template contains basic Word styles rather than an extensive style system. The LaTeX design should reproduce the visible university conventions with stable semantic commands, not mimic Word's internal style names.

## Front-matter order

1. title/degree/student/department page;
2. repeated/formal title page;
3. declaration;
4. certification/signature page;
5. acknowledgements;
6. dedication;
7. table of contents;
8. list of tables;
9. list of figures;
10. list of abbreviations;
11. abstract;
12. Chapter One.

The project title, students and roll numbers, supervisor, co-supervisor,
committee members, Head of Department, department, university, programme, and
session have been supplied by the user and are recorded in
`report_metadata.md`. The submission date remains unprovided. These
administrative details are out-of-band user evidence, not repository findings.

## PDF structural conventions

- Roman numerals are used for front matter; Arabic numbering starts with Chapter 1.
- The table of contents is detailed to subsection level.
- Figures and tables are numbered by chapter (for example Figure 3.1 and Table 4.1).
- Appendix figures/tables use appendix letters.
- Captions are descriptive and figures/tables are placed close to the first explanatory reference.
- The sample uses nine chapters, followed by references and appendices.
- Its project-specific chapters—model fine-tuning, edge deployment, Quranic application evaluation—are not relevant and will not be copied into this project's outline.

## LaTeX implications for the later stage

- Use A4, university margins, Times-compatible fonts, 1.5 spacing, chapter-based numbering, Roman/Arabic page transitions, IEEE BibTeX style, lists of figures/tables, abbreviations, and lettered appendices.
- Keep diagrams as vector graphics/TikZ where practical and screenshots as cropped lossless images.
- Use `booktabs`, `tabularx`/`longtable`, consistent captions/labels/cross-references, and syntax-highlighted code listings.
- Do not create any LaTeX until the documentation plan receives approval.
