import json
import os
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch

# --------------------------------------------
# CONFIGURATION
# --------------------------------------------

JSON_FOLDER = "./"

JSON_FILES = [
    "rsa-2048.json",
    "rsa-3072.json",
    "rsa-4096.json",
    "ecdsa-p256.json",
    "ecdsa-p384.json"
]

OUTPUT_PDF = "certificate_domain_report_styled.pdf"

# --------------------------------------------
# PDF STYLES
# --------------------------------------------

styles = getSampleStyleSheet()

section_title = ParagraphStyle(
    "SectionTitle",
    parent=styles["Heading1"],
    fontSize=22,
    textColor=colors.HexColor("#1a237e"),
    spaceAfter=20,
)

count_box_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e65100")),
    ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
    ("FONTSIZE", (0, 0), (-1, -1), 18),
    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.white),
    ("BOX", (0, 0), (-1, -1), 0.3, colors.white),
])

domain_style = ParagraphStyle(
    "DomainStyle",
    parent=styles["Normal"],
    fontSize=12,
    textColor=colors.HexColor("#0d47a1"),
    underline=True,
    spaceAfter=6,
)

divider_style = TableStyle([
    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#cfd8dc"))
])

# --------------------------------------------
# LOAD DOMAINS FROM FILE
# --------------------------------------------

def load_domains(filepath):
    """Load domain list from JSON file."""
    with open(filepath, "r") as f:
        data = json.load(f)
    return [item["domain"] for item in data]

# --------------------------------------------
# MAKE CLICKABLE DOMAIN
# --------------------------------------------

def domain_link(num, domain):
    url = f"http://{domain}"
    return Paragraph(f"{num}. <link href='{url}'>{domain}</link>", domain_style)

# --------------------------------------------
# CREATE BEAUTIFUL COUNT BOX
# --------------------------------------------

def make_count_box(count, title):
    data = [
        [str(count)],
        [title]
    ]

    table = Table(
        data,
        colWidths=[5 * inch],
        rowHeights=[30, 22]
    )

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#e65100")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTSIZE", (0, 0), (0, 0), 24),     # big number
        ("FONTSIZE", (0, 1), (0, 1), 12),     # label
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOX", (0, 0), (-1, -1), 0.3, colors.white),
    ]))

    return table

def generate_pdf():
    story = []

    for json_file in JSON_FILES:

        file_path = os.path.join(JSON_FOLDER, json_file)
        if not os.path.exists(file_path):
            print(f"Skipping missing: {json_file}")
            continue

        domains = load_domains(file_path)
        domain_count = len(domains)

        # Section title
        title_text = f"Domains which used {json_file.replace('.json', '').upper()}"
        story.append(Paragraph(title_text, section_title))
        story.append(Spacer(1, 10))

        # add count box
        story.append(make_count_box(domain_count, "Total Domains"))
        story.append(Spacer(1, 20))

        # divider
        story.append(Table([[" "]], colWidths=[7.5 * inch], style=divider_style))
        story.append(Spacer(1, 20))

        # numbered clickable domains
        for idx, domain in enumerate(domains, start=1):
            story.append(domain_link(idx, domain))

        story.append(Spacer(1, 35))

    pdf = SimpleDocTemplate(OUTPUT_PDF, pagesize=A4)
    pdf.build(story)

    print(f"Styled PDF Generated → {OUTPUT_PDF}")


if __name__ == "__main__":
    generate_pdf()
