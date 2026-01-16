import json
import os
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
INPUT_FILENAME = "certificate-lifecycle.json"
OUTPUT_FILENAME = "certificate-lifecycle.html"

# ==========================================
# 1. LOAD DATA
# ==========================================
def load_json(filename):
    if not os.path.exists(filename):
        print(f"Error: Could not find '{filename}'. Please export your MongoDB aggregation first.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

data = load_json(INPUT_FILENAME)

# ==========================================
# 2. CALCULATE SUMMARY STATS
# ==========================================
# We count based on the "Agility Status" string in your JSON

count_excellent = sum(1 for d in data if "Excellent" in d.get("Agility Status", ""))
count_standard = sum(1 for d in data if "Standard" in d.get("Agility Status", ""))
count_critical = sum(1 for d in data if "CRITICAL" in d.get("Agility Status", ""))

print(f"Loaded {len(data)} records. (Excellent: {count_excellent}, Standard: {count_standard}, Critical: {count_critical})")

# ==========================================
# 3. HELPER: DUAL DATE FORMATTER
# ==========================================
def format_dual_date(iso_date_str):
    """
    Input: "2024-12-09T14:17:28Z"
    Output: "2024-12-09 <div class='sub-date'>09 December 2024</div>"
    """
    try:
        if not iso_date_str: return "-"
        
        # Clean the string (remove time if needed for parsing)
        clean_str = iso_date_str.split("T")[0] if "T" in iso_date_str else iso_date_str
        date_obj = datetime.datetime.strptime(clean_str, "%Y-%m-%d")
        
        technical_fmt = date_obj.strftime("%Y-%m-%d")
        friendly_fmt = date_obj.strftime("%d %B %Y")
        
        return f"{technical_fmt}<div class='sub-date'>{friendly_fmt}</div>"
    except:
        return iso_date_str 

# ==========================================
# 4. HTML GENERATOR
# ==========================================
current_date = datetime.datetime.now().strftime("%d %B %Y")

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Crypto-Agility & Lifecycle Audit</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; padding: 40px; }}
        .container {{ max-width: 1250px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        
        h1 {{ color: #263238; margin-bottom: 5px; }}
        .timestamp {{ color: #78909c; font-size: 14px; margin-bottom: 30px; border-bottom: 2px solid #eceff1; padding-bottom: 20px; }}
        
        /* Summary Cards */
        .summary {{ display: flex; gap: 20px; margin-bottom: 40px; }}
        .card {{ flex: 1; padding: 20px; border-radius: 10px; color: white; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        
        .card-green {{ background: linear-gradient(135deg, #66bb6a 0%, #43a047 100%); }}
        .card-yellow {{ background: linear-gradient(135deg, #ffa726 0%, #f57c00 100%); }}
        .card-red {{ background: linear-gradient(135deg, #ef5350 0%, #c62828 100%); }}
        
        .card-number {{ font-size: 36px; font-weight: 800; }}
        .card-label {{ font-size: 13px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.95; }}

        /* Rules Info Box */
        .rules-box {{ background-color: #e3f2fd; border-left: 5px solid #2196f3; padding: 20px; margin-bottom: 40px; border-radius: 4px; }}
        .rules-title {{ font-weight: bold; color: #0d47a1; margin-bottom: 10px; font-size: 16px; }}
        .rule-item {{ margin-bottom: 8px; font-size: 14px; line-height: 1.5; }}
        .rule-tag {{ font-weight: bold; padding: 2px 6px; border-radius: 4px; font-size: 12px; margin-right: 8px; color: white; }}
        
        /* Table Styles */
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; font-size: 13px; background: white; }}
        th {{ background-color: #eceff1; text-align: left; padding: 12px; font-weight: 700; color: #455a64; border-bottom: 2px solid #cfd8dc; }}
        td {{ padding: 10px 12px; border-bottom: 1px solid #eee; vertical-align: top; }}
        tr:hover {{ background-color: #fafafa; }}
        
        /* Typography */
        .domain-link {{ font-weight: 600; color: #1565c0; text-decoration: none; font-size: 14px; }}
        .sub-date {{ color: #90a4ae; font-size: 11px; margin-top: 3px; font-weight: 500; }}
        .lifespan {{ font-weight: bold; font-family: monospace; font-size: 14px; }}
        
        /* Status Badges */
        .status-badge {{ padding: 5px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; display: inline-block; }}
        .status-green {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }}
        .status-yellow {{ background: #fff3e0; color: #ef6c00; border: 1px solid #ffe0b2; }}
        .status-red {{ background: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }}

        /* Section Headings */
        h2 {{ color: #263238; margin-top: 40px; margin-bottom: 20px; font-size: 22px; border-bottom: 1px solid #eceff1; padding-bottom: 10px; }}

        /* PRINT FIXES (Landscape) */
        @media print {{
            @page {{ size: A1 landscape; margin: 5mm; }}
            body {{ -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; zoom: 85%; padding: 0 !important; background: white !important; }}
            .container {{ width: 100% !important; max-width: none !important; box-shadow: none !important; padding: 10px !important; margin: 0 !important; }}
            a {{ text-decoration: none !important; color: #333 !important; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <h1>Crypto-Agility & Lifecycle Audit</h1>


    <div class="rules-box">
        <div class="rules-title">ℹ️ Audit Criteria: Certificate Lifecycle Rules</div>
        <div class="rule-item">
            <span class="rule-tag" style="background:#43a047;">&lt; 95 Days</span>
            <strong>Excellent (Agile):</strong> Indicates "Automated Security" (e.g., Let's Encrypt). Keys rotate frequently, reducing risk.
        </div>
        <div class="rule-item">
            <span class="rule-tag" style="background:#fb8c00;">&lt; 397 Days</span>
            <strong>Standard (Commercial):</strong> The current maximum allowed by Apple/Google policies for commercial certificates (approx 1 year).
        </div>
        <div class="rule-item">
            <span class="rule-tag" style="background:#c62828;">&gt; 398 Days</span>
            <strong>CRITICAL (Broken):</strong> Modern browsers (Chrome, Safari, Edge) will <u>reject</u> these certificates. Effectively dead on arrival.
        </div>
    </div>

    <div class="summary">
        <div class="card card-green">
            <div class="card-number">{count_excellent}</div>
            <div class="card-label">Excellent (Automated)</div>
        </div>
        <div class="card card-yellow">
            <div class="card-number">{count_standard}</div>
            <div class="card-label">Standard (1 Year)</div>
        </div>
        <div class="card card-red">
            <div class="card-number">{count_critical}</div>
            <div class="card-label">Critical (>398 Days)</div>
        </div>
    </div>
"""

# ==========================================
# 5. FILL SECTIONED TABLES
# ==========================================
# Helper function to generate table HTML for a given category
def generate_table_rows(rows):
    table_rows = ""
    for row in rows:
        domain = row.get("Domain", "Unknown")
        issuer = row.get("Issuer", "Unknown Issuer")
        start_date = format_dual_date(row.get("Validity Start", ""))
        end_date = format_dual_date(row.get("Validity End", ""))
        lifespan = row.get("Lifespan (Days)", 0)
        
        table_rows += f"""
            <tr>
                <td>
                    <a href="http://{domain}" target="_blank" class="domain-link">{domain}</a>
                </td>
                <td>{issuer}</td>
                <td>{start_date}</td>
                <td>{end_date}</td>
                <td style="text-align:center;" class="lifespan">{lifespan} Days</td>
            </tr>
        """
    return table_rows

# Filter data into categories
excellent_rows = [d for d in data if "Excellent" in d.get("Agility Status", "")]
standard_rows = [d for d in data if "Standard" in d.get("Agility Status", "")]
critical_rows = [d for d in data if "CRITICAL" in d.get("Agility Status", "")]

# Excellent Section
html_content += """
    <h2>Excellent (Agile)</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 25%">Domain</th>
                <th style="width: 25%">Issuer</th>
                <th style="width: 20%">Validity Start</th>
                <th style="width: 20%">Validity End</th>
                <th style="width: 10%; text-align:center;">Lifespan</th>
            </tr>
        </thead>
        <tbody>
"""
if excellent_rows:
    html_content += generate_table_rows(excellent_rows)
else:
    html_content += "<tr><td colspan='5' style='text-align:center; padding:20px'>No data found.</td></tr>"
html_content += """
        </tbody>
    </table>
"""

# Standard Section
html_content += """
    <h2>Standard (Commercial)</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 25%">Domain</th>
                <th style="width: 25%">Issuer</th>
                <th style="width: 20%">Validity Start</th>
                <th style="width: 20%">Validity End</th>
                <th style="width: 10%; text-align:center;">Lifespan</th>
            </tr>
        </thead>
        <tbody>
"""
if standard_rows:
    html_content += generate_table_rows(standard_rows)
else:
    html_content += "<tr><td colspan='5' style='text-align:center; padding:20px'>No data found.</td></tr>"
html_content += """
        </tbody>
    </table>
"""

# Critical Section
html_content += """
    <h2>Critical (Broken)</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 25%">Domain</th>
                <th style="width: 25%">Issuer</th>
                <th style="width: 20%">Validity Start</th>
                <th style="width: 20%">Validity End</th>
                <th style="width: 10%; text-align:center;">Lifespan</th>
            </tr>
        </thead>
        <tbody>
"""
if critical_rows:
    html_content += generate_table_rows(critical_rows)
else:
    html_content += "<tr><td colspan='5' style='text-align:center; padding:20px'>No data found.</td></tr>"
html_content += """
        </tbody>
    </table>
"""

html_content += """
</div>

</body>
</html>
"""

# ==========================================
# 6. SAVE FILE
# ==========================================
with open(OUTPUT_FILENAME, "w", encoding='utf-8') as f:
    f.write(html_content)

print(f"Success! Report generated: {OUTPUT_FILENAME}")