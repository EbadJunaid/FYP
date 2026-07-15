import json
import os

# ==========================================
# CONFIGURATION
# ==========================================
MAIN_DATA_FILE = "report.json"      # Your main aggregation export
ISSUER_DATA_FILE = "who-error.json" # Your "Sherlock" aggregation export
OUTPUT_FILENAME = "report.html"

# ==========================================
# 1. LOAD DATA
# ==========================================
def load_json(filename):
    if not os.path.exists(filename):
        print(f"Warning: Could not find '{filename}'. Section will be empty.")
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        return json.load(f)

main_data = load_json(MAIN_DATA_FILE)
issuer_data = load_json(ISSUER_DATA_FILE)

print(f"Loaded {len(main_data)} certificates and {len(issuer_data)} issuers.")

# ==========================================
# 2. CALCULATE METRICS
# ==========================================
count_both = sum(1 for d in main_data if d.get('Error Count', 0) > 0 and d.get('Warning Count', 0) > 0)
count_only_errors = sum(1 for d in main_data if d.get('Error Count', 0) > 0 and d.get('Warning Count', 0) == 0)
count_only_warnings = sum(1 for d in main_data if d.get('Error Count', 0) == 0 and d.get('Warning Count', 0) > 0)

# ==========================================
# 3. HTML GENERATION
# ==========================================

html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Zlint Test Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f0f2f5; color: #333; padding: 40px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
        
        /* Headers */
        h1 {{ color: #1a237e; border-bottom: 2px solid #e8eaf6; padding-bottom: 15px; margin-bottom: 30px; }}
        h2 {{ color: #283593; margin-top: 40px; font-size: 20px; }}
        
        /* Summary Cards */
        .summary {{ display: flex; gap: 20px; margin-bottom: 40px; }}
        .card {{ flex: 1; padding: 25px; border-radius: 10px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }}
        .card-red {{ background: linear-gradient(135deg, #ffcdd2 0%, #ffebee 100%); color: #b71c1c; border: 1px solid #ffcdd2; }}
        .card-orange {{ background: linear-gradient(135deg, #ffe0b2 0%, #fff3e0 100%); color: #e65100; border: 1px solid #ffe0b2; }}
        .card-yellow {{ background: linear-gradient(135deg, #fff9c4 0%, #fffde7 100%); color: #f57f17; border: 1px solid #fff9c4; }}
        .card-number {{ font-size: 36px; font-weight: 800; margin-bottom: 5px; }}
        .card-label {{ font-size: 13px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600; opacity: 0.8; }}

        /* Glossary Section */
        .glossary-box {{ background-color: #e8eaf6; padding: 20px; border-radius: 8px; border-left: 5px solid #3949ab; margin-bottom: 30px; }}
        .glossary-item {{ margin-bottom: 15px; }}
        .glossary-title {{ font-size: 18px; font-weight:bold font-family: 'Courier New', monospace; color: #c62828;margin-bottom: 5px; }}
        .glossary-desc {{ margin-left: 0px; margin-top: 4px; line-height: 1.5; }}

        /* Tables */
        table {{ width: 100%; border-collapse: collapse; margin-top: 15px; font-size: 14px; background: white; }}
        th {{ background-color: #f5f5f5; text-align: left; padding: 15px; border-bottom: 2px solid #ddd; color: #555; font-weight: 700; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid #eee; vertical-align: top; }}
        tr:hover {{ background-color: #f9fafb; }}
        
        /* Badges */
        .badge {{ padding: 4px 8px; border-radius: 4px; font-size: 11px; font-family: monospace; display: inline-block; margin-right: 5px; margin-bottom: 5px; }}
        .badge-err {{ background-color: #ffebee; color: #c62828; border: 1px solid #ffcdd2; }}
        .badge-warn {{ background-color: #fff8e1; color: #f57f17; border: 1px solid #ffe0b2; }}
        
        /* Links */
        a {{ text-decoration: none; color: #1565c0; transition: color 0.2s; }}
        a:hover {{ color: #0d47a1; text-decoration: underline; }}
    </style>
</head>
<body>

<div class="container">
    <h1>Zlint Test Report</h1>
    
    <div class="summary">
        <div class="card card-red">
            <div class="card-number">{count_only_errors}</div>
            <div class="card-label">Errors Only</div>
        </div>
        <div class="card card-orange">
            <div class="card-number">{count_both}</div>
            <div class="card-label">Both Errors and Warnings</div>
        </div>
        <div class="card card-yellow">
            <div class="card-number">{count_only_warnings}</div>
            <div class="card-label">Warnings Only</div>
        </div>
    </div>

    <h2> Understanding Errors and Warnings</h2>
    <div class="glossary-box">
        <div class="glossary-item">
            <div class="glossary-title" style="color:#c62828">e_sub_cert_aia_does_not_contain_ocsp_url : </div>
            <div class="glossary-desc">The certificate is missing a link that allows browsers to check if it has been revoked. <br><em>Note: This is standard behavior for "Let's Encrypt" certificates and is usually safe.</em></div>
        </div>
        <div class="glossary-item">
            <div class="glossary-title" style="color:#c62828">e_dnsname_not_valid_tld : </div>
            <div class="glossary-desc"> The domain name ends in a suffix that doesn't exist (e.g., .local instead of .com or .pk). This certificate will not work publicly.</div>
        </div>
        <div class="glossary-item">
            <div class="glossary-title" style="color:#f57f17">w_tls_server_cert_valid_time_longer_than_397_days : </div>
            <div class="glossary-desc">This certificate was purchased for 2+ years. Modern browsers (Apple, Google) now require certificates to be 1 year or less. It may be rejected soon.</div>
        </div>
        <div class="glossary-item">
            <div class="glossary-title" style="color:#f57f17">w_ext_subject_key_identifier_missing_sub_cert : </div>
            <div class="glossary-desc"> The certificate is missing a specific ID tag (Subject Key Identifier) that helps computers sort and organize certificates efficiently.</div>
        </div>
    </div>

    <h2>The "Analysis": Who is responsible?</h2>
    <p>This table shows which Certificate Authorities (Issuers) are generating the most errors and warnings .</p>
    <table style="width: 70%; margin-bottom: 40px;">
        <thead>
            <tr>
                <th>Issuer Name</th>
                <th>Total Bad Certs</th>
                <th>Example Domain</th>
            </tr>
        </thead>
        <tbody>
"""

# Inject Issuer Data
for issuer in issuer_data:
    html_content += f"""
            <tr>
                <td style="font-weight:bold;">{issuer.get('_id', 'Unknown')}</td>
                <td>{issuer.get('Total Bad Certs', 0)}</td>
                <td style="font-family: monospace; color: #666;">{issuer.get('Example Domain', '-')}</td>
            </tr>
    """

html_content += """
        </tbody>
    </table>

    <h2> Detailed Domain Report</h2>
    <table>
        <thead>
            <tr>
                <th style="width: 25%">Domain</th>
                <th style="width: 5%; text-align: center;">Errors</th>
                <th style="width: 5%; text-align: center;">Warnings</th>
                <th style="width: 65%">Technical Details</th>
            </tr>
        </thead>
        <tbody>
"""

# Inject Main Data
for row in main_data:
    err_count = row.get('Error Count', 0)
    warn_count = row.get('Warning Count', 0)
    domain = row.get('Domain', 'Unknown')
    
    if err_count == 0 and warn_count == 0:
        continue

    # Format badges
    errors = row.get('Error Details', [])
    warnings = row.get('Warning Details', [])
    
    if not isinstance(errors, list): errors = []
    if not isinstance(warnings, list): warnings = []

    error_badges = "".join([f'<span class="badge badge-err">{e}</span>' for e in errors])
    warning_badges = "".join([f'<span class="badge badge-warn">{w}</span>' for w in warnings])
    
    details_html = ""
    if err_count > 0:
        # CHANGED: Removed <br>, added space, used flex-like layout if needed
        details_html += f"<div style='margin-bottom:8px'><strong>Errors:</strong> &nbsp;{error_badges}</div>"
    
    if warn_count > 0:
        # CHANGED: Removed <br>, added space
        details_html += f"<div><strong>Warnings:</strong> &nbsp;{warning_badges}</div>"

    html_content += f"""
            <tr>
                <td class="domain-name">
                    <a href="http://{domain}" target="_blank">{domain}</a>
                </td>
                <td style="text-align: center;" class="{'count-high' if err_count > 0 else ''}">{err_count}</td>
                <td style="text-align: center;">{warn_count}</td>
                <td>{details_html}</td>
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

print(f"Report generated successfully: {OUTPUT_FILENAME}")