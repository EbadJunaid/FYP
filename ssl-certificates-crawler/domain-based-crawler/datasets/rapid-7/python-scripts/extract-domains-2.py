import csv
import os
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64

def extract_common_name_from_pem(pem_data):
    try:
        if "-----BEGIN CERTIFICATE-----" not in pem_data:
            pem_data = (
                "-----BEGIN CERTIFICATE-----\n"
                + pem_data.strip()
                + "\n-----END CERTIFICATE-----\n"
            )
        cert = x509.load_pem_x509_certificate(pem_data.encode('utf-8'), default_backend())
        subject = cert.subject
        common_names = [attr.value for attr in subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)]
        return common_names[0] if common_names else ""
    except Exception as e:
        raise e  # Re-raise so we can log it

def process_csv_extract_cn(input_csv_path, output_csv_path, failed_log_path="failed-log.log", show_every=100000):
    if not os.path.exists(input_csv_path):
        print(f"❌ Input file not found: {input_csv_path}")
        return
    try:
        with open(input_csv_path, "r", encoding="utf-8") as infile, \
             open(output_csv_path, "w", encoding="utf-8", newline="") as outfile, \
             open(failed_log_path, "w", encoding="utf-8") as failed_log:
            writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            idx = 1
            lines_processed = 0
            failed_count = 0
            
            for line in infile:
                lines_processed += 1
                if lines_processed % show_every == 0:
                    print(f"📊 Processed {lines_processed} lines, {idx-1} valid common_names written, {failed_count} failed...")
                
                line = line.strip()
                if not line:
                    continue
                
                try:
                    parts = line.split(",", 1)
                    if len(parts) != 2:
                        failed_log.write(f"Line {lines_processed}: Invalid format (no comma separator)\n")
                        failed_count += 1
                        continue
                    
                    fingerprint, pem_b64 = parts
                    pem_str = pem_b64
                    
                    if not pem_b64.startswith("-----BEGIN CERTIFICATE-----"):
                        try:
                            pem_bytes = base64.b64decode(pem_b64, validate=True)
                            pem_str = pem_bytes.decode("utf-8")
                        except Exception as e:
                            pem_str = pem_b64
                    
                    cn = extract_common_name_from_pem(pem_str)
                    
                    if cn:
                        writer.writerow([idx, cn])
                        idx += 1
                    else:
                        # No common_name found (certificate valid but no CN field)
                        failed_log.write(f"Line {lines_processed}: No common_name in certificate (fingerprint: {fingerprint[:20]}...)\n")
                        failed_count += 1
                        
                except Exception as e:
                    # Certificate parsing failed
                    failed_log.write(f"Line {lines_processed}: Certificate parsing failed - {type(e).__name__}: {str(e)[:100]}\n")
                    failed_count += 1
                    continue
            
            print(f"\n{'='*60}")
            print(f"✅ Finished! Total lines processed: {lines_processed}")
            print(f"✅ Total common_names extracted: {idx-1}")
            print(f"⚠️  Total failed/skipped: {failed_count}")
            print(f"📄 Results written in: {output_csv_path}")
            print(f"📋 Failed entries logged in: {failed_log_path}")
            print(f"{'='*60}")
            
    except Exception as e:
        print(f"❌ Error opening or writing files: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    large_csv_path = "raw/2023-12-25-1703466479-https_get_443_certs"  # Your huge input CSV file path
    output_path = "processed/common_names-2.csv"  # Your desired output CSV (headerless)
    failed_log_path = "logs/failed-log-2.log"  # Log file for failed certificates
    process_csv_extract_cn(large_csv_path, output_path, failed_log_path, show_every=100000)
