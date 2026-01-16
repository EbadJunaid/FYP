import json
import os
import datetime

# ==========================================
# CONFIGURATION
# ==========================================
# Ensure these match your actual JSON filenames
FILE_SOON = "expiring-soon.json"
FILE_EXPIRED = "expired.json"
OUTPUT_FILENAME = "SSL_Expiration_Report.html"

# ==========================================
# 1. LOAD DATA
# ==========================================
def load_json(filename):
    if not os.path.exists(filename):
        print(f"Note: '{filename}' not found. Section will be empty.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

data_soon = load_json(FILE_SOON)
data_expired = load_json(FILE_EXPIRED)

print(f"Loaded {len(data_soon)} expiring certificates and {len(data_expired)} expired certificates.")

# ==========================================
# 2. HELPER: DATE FORMATTER
# ==========================================
def format_pretty_date(iso_date_str):
    """
    Input: "2025-12-10T14:14:49Z"
    Output: "2025-12-10 [10 December 2025]"
    """
    try:
        if "T" in iso_date_str:
            clean_date_str = iso_date_str.split("T")[0]
        else:
            clean_date_str = iso_date_str
            
        date_obj = datetime.datetime.strptime(clean_date_str, "%Y-%m-%d")
        
        simple_format = date_obj.strftime("%Y-%m-%d")
        fancy_format = date_obj.strftime("%d %B %Y")
        
        # Use a small span for the fancy date so it fits nicely
        return f"{simple_format} <div style='color:#78909c; font-size:12px; margin-top:2px;'>{fancy_format}</div>"
    except:
        return iso_date_str 

# ==========================================
# 3. HTML GENERATOR
# ==========================================
current_date = datetime.datetime.now().strftime("%d %B %Y")

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>SSL Expiration Monitor</title>
    <style>
        /* MAIN SCREEN STYLES */
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f8; color: #333; padding: 40px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        
        h1 {{ color: #263238; border-bottom: 2px solid #eceff1; padding-bottom: 15px; margin-bottom: 10px; }}
        .timestamp {{ color: #78909c; font-size: 14px; margin-bottom: 40px; }}
        
        h2 {{ margin-top: 50px; font-size: 22px; display: flex; align-items: center; gap: 10px; }}
        .section-icon {{ font-size: 24px; }}
        .criteria-text {{ font-size: 14px; color: #78909c; font-weight: normal; margin-left: 10px; }}
        
        /* Summary Cards */
        .summary {{ display: flex; gap: 20px; margin-bottom: 40px; }}
        .card {{ flex: 1; padding: 25px; border-radius: 10px; color: white; text-align: center; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
        .card-orange {{ background: linear-gradient(135deg, #ff9800 0%, #f57c00 100%); }}
        .card-red {{ background: linear-gradient(135deg, #ef5350 0%, #c62828 100%); }}
        .card-number {{ font-size: 42px; font-weight: 800; }}
        .card-label {{ font-size: 14px; text-transform: uppercase; letter-spacing: 1px; opacity: 0.9; }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; background: white; border: 1px solid #eee; }}
        th {{ background-color: #eceff1; text-align: left; padding: 15px; font-weight: 700; color: #455a64; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #eee; vertical-align: middle; }}
        tr:hover {{ background-color: #fafafa; }}
        
        /* Specific Data Styles */
        .days-left {{ font-weight: bold; color: #e65100; font-family: monospace; font-size: 15px; }}
        .days-gone {{ font-weight: bold; color: #c62828; font-family: monospace; font-size: 15px; }}
        
        /* Badges */
        .badge {{ padding: 5px 10px; border-radius: 15px; font-size: 11px; font-weight: bold; display: inline-block; text-align: center; min-width: 30px; }}
        .badge-dv {{ background: #e3f2fd; color: #1565c0; border: 1px solid #bbdefb; }}
        .badge-ov {{ background: #e8f5e9; color: #2e7d32; border: 1px solid #c8e6c9; }}
        .badge-ev {{ background: #f3e5f5; color: #7b1fa2; border: 1px solid #e1bee7; }}
        
        a {{ text-decoration: none; color: #1565c0; font-weight: 600; }}
        a:hover {{ text-decoration: underline; }}

        /* ========================================= */
        /* PRINT SPECIFIC FIXES (LANDSCAPE MODE)     */
        /* ========================================= */
        @media print {{
            @page {{
                size: A4 landscape;   /* Force Landscape Orientation */
                margin: 5mm;          /* Minimize margins */
            }}
            
            body {{
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
                zoom: 90%;            /* Scale down slightly to fit columns */
                background-color: white !important;
                padding: 0 !important;
            }}

            .container {{
                width: 100% !important;
                max-width: none !important;
                box-shadow: none !important;
                margin: 0 !important;
                padding: 10px !important;
                border: none !important;
            }}

            table {{
                page-break-inside: auto;
                width: 100% !important;
            }}
            
            tr {{
                page-break-inside: avoid;
                page-break-after: auto;
            }}
            
            .timestamp {{ display: none; }}
            
            /* Print links clearly */
            a {{ text-decoration: none !important; color: #333 !important; }}
        }}
    </style>
</head>
<body>

<div class="container">
    <h1>Expiration Report</h1>    
    <div class="summary">
        <div class="card card-orange">
            <div class="card-number">{len(data_soon)}</div>
            <div class="card-label">Expiring Soon (30 Days)</div>
        </div>
        <div class="card card-red">
            <div class="card-number">{len(data_expired)}</div>
            <div class="card-label">Already Expired</div>
        </div>
    </div>

    <h2 style="color: #e65100;">
        <span class="section-icon">⚠️</span> Expiring Soon 
        <span class="criteria-text">(Criteria: Expires in &le; 30 Days)</span>
    </h2>
    <p>These certificates are valid but require immediate renewal.</p>
    <table>
        <thead>
            <tr>
                <th style="width: 12%">Days Left</th>
                <th style="width: 30%">Domain</th>
                <th style="width: 25%">Common Name (CN)</th>
                <th style="width: 10%; text-align:center;">Validation</th>
                <th style="width: 23%">Expiration Date</th>
            </tr>
        </thead>
        <tbody>
"""

# Fill Expiring Soon Table
if not data_soon:
    html_content += "<tr><td colspan='5' style='text-align:center; padding:20px; color:#888;'>No certificates match this criteria.</td></tr>"
else:
    for row in data_soon:
        formatted_date = format_pretty_date(row['Expiration Date'])
        val_level = row.get('Validation Level', 'UNK')
        
        badge_class = "badge-dv"
        if val_level == "OV": badge_class = "badge-ov"
        if val_level == "EV": badge_class = "badge-ev"

        html_content += f"""
            <tr>
                <td class="days-left">{row['Days Left']} Days</td>
                <td><a href="http://{row['Domain']}" target="_blank">{row['Domain']}</a></td>
                <td>{row['Common Name']}</td>
                <td style="text-align:center;"><span class="badge {badge_class}">{val_level}</span></td>
                <td>{formatted_date}</td>
            </tr>
        """

html_content += """
        </tbody>
    </table>

    <h2 style="color: #c62828; margin-top: 60px;">
        <span class="section-icon">⛔</span> Expired Certificates
        <span class="criteria-text">(Criteria: 0 Days Left)</span>
    </h2>
    <p>These certificates have already expired. Users visiting these sites likely see security warnings.</p>
    <table>
        <thead>
            <tr>
                <th style="width: 12%">Days Ago</th>
                <th style="width: 30%">Domain</th>
                <th style="width: 25%">Common Name (CN)</th>
                <th style="width: 10%; text-align:center;">Validation</th>
                <th style="width: 23%">Expired On</th>
            </tr>
        </thead>
        <tbody>
"""

# Fill Expired Table
if not data_expired:
    html_content += "<tr><td colspan='5' style='text-align:center; padding:20px; color:#888;'>No certificates match this criteria. Good job!</td></tr>"
else:
    for row in data_expired:
        formatted_date = format_pretty_date(row['Expiration Date'])
        val_level = row.get('Validation Level', 'UNK')
        
        badge_class = "badge-dv"
        if val_level == "OV": badge_class = "badge-ov"
        if val_level == "EV": badge_class = "badge-ev"

        html_content += f"""
            <tr>
                <td class="days-gone">{row['Days Gone']} Days ago</td>
                <td><a href="http://{row['Domain']}" target="_blank">{row['Domain']}</a></td>
                <td>{row['Common Name']}</td>
                <td style="text-align:center;"><span class="badge {badge_class}">{val_level}</span></td>
                <td>{formatted_date}</td>
            </tr>
        """

html_content += """
        </tbody>
    </table>
</div>

</body>
</html>
"""

# ==========================================
# 4. SAVE FILE
# ==========================================
with open(OUTPUT_FILENAME, "w", encoding='utf-8') as f:
    f.write(html_content)

print(f"Report generated! Open '{OUTPUT_FILENAME}' to view.")