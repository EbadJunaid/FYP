import csv
import os
import json
import subprocess
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import tempfile

def extract_common_name_from_json(cert_json_str):
    """
    Parse zcertificate JSON output and extract common_name
    Path: parsed -> subject -> common_name
    """
    try:
        cert_json = json.loads(cert_json_str)
        
        if 'parsed' in cert_json:
            parsed = cert_json['parsed']
            if 'subject' in parsed and 'common_name' in parsed['subject']:
                common_names = parsed['subject']['common_name']
                if isinstance(common_names, list) and len(common_names) > 0:
                    return common_names[0]
                elif isinstance(common_names, str):
                    return common_names
        
        return ""
    except json.JSONDecodeError as e:
        raise Exception(f"JSON parse error: {str(e)[:100]}")
    except Exception as e:
        raise Exception(f"Certificate extraction error: {str(e)[:100]}")

def format_pem(pem_data):
    """Ensure PEM has proper headers/footers"""
    pem_data = pem_data.strip()
    if "-----BEGIN CERTIFICATE-----" not in pem_data:
        pem_data = (
            "-----BEGIN CERTIFICATE-----\n"
            + pem_data
            + "\n-----END CERTIFICATE-----"
        )
    return pem_data

def process_batch_with_zcertificate(batch_data, zcert_path="./zcertificate"):
    """
    Process a batch of certificates using a single zcertificate call
    Returns list of (line_num, fingerprint, common_name, error)
    """
    results = []
    
    # Create temporary file with all certificates in batch
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tmp:
        tmp_path = tmp.name
        cert_boundaries = []
        current_pos = 0
        
        for line_num, fingerprint, pem_data in batch_data:
            formatted_pem = format_pem(pem_data)
            tmp.write(formatted_pem + "\n")
            cert_boundaries.append((line_num, fingerprint, current_pos))
            current_pos += 1
    
    try:
        # Run zcertificate once for entire batch with multiple workers
        process = subprocess.Popen(
            [zcert_path, '-format', 'pem', '-workers', '4'],
            stdin=open(tmp_path, 'r'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            # If batch failed, mark all as failed
            for line_num, fingerprint, _ in cert_boundaries:
                results.append((line_num, fingerprint, "", f"Batch failed: {stderr[:100]}"))
        else:
            # Parse JSON output line by line (zcertificate outputs one JSON per line)
            json_lines = stdout.strip().split('\n')
            
            for idx, ((line_num, fingerprint, _), json_line) in enumerate(zip(cert_boundaries, json_lines)):
                if json_line.strip():
                    cn = extract_common_name_from_json(json_line)
                    if cn:
                        results.append((line_num, fingerprint, cn, None))
                    else:
                        results.append((line_num, fingerprint, "", "No common_name in certificate"))
                else:
                    results.append((line_num, fingerprint, "", "Empty JSON output"))
    
    except subprocess.TimeoutExpired:
        for line_num, fingerprint, _ in cert_boundaries:
            results.append((line_num, fingerprint, "", "Batch timeout"))
    except Exception as e:
        for line_num, fingerprint, _ in cert_boundaries:
            results.append((line_num, fingerprint, "", f"Batch error: {str(e)[:100]}"))
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
    
    return results

def check_zcertificate_available(zcert_path="./zcertificate"):
    """Check if zcertificate binary is available and executable"""
    try:
        process = subprocess.Popen(
            [zcert_path, '-help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.communicate(timeout=5)
        return True
    except Exception as e:
        return False

def process_csv_extract_cn_optimized(
    input_csv_path, 
    output_csv_path, 
    zcert_path="./zcertificate", 
    failed_log_path="failed-log.log", 
    batch_size=100,
    show_every=1000
):
    """
    Process CSV file using zcertificate with batch processing for maximum speed
    
    Args:
        input_csv_path: Input CSV with fingerprint,pem_data
        output_csv_path: Output CSV with index,common_name
        zcert_path: Path to zcertificate binary
        failed_log_path: Log file for failed certificates
        batch_size: Number of certificates to process in one zcertificate call
        show_every: Show progress every N lines
    """
    if not os.path.exists(input_csv_path):
        print(f"❌ Input file not found: {input_csv_path}")
        return
    
    if not check_zcertificate_available(zcert_path):
        print(f"❌ zcertificate not found at: {zcert_path}")
        print(f"   Please ensure zcertificate binary is in the current directory")
        print(f"   Download from: https://github.com/zmap/zcertificate")
        return
    
    print(f"✅ zcertificate found at: {zcert_path}")
    
    try:
        with open(input_csv_path, "r", encoding="utf-8") as infile, \
             open(output_csv_path, "w", encoding="utf-8", newline="") as outfile, \
             open(failed_log_path, "w", encoding="utf-8") as failed_log:
            
            writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            output_idx = 1
            lines_processed = 0
            failed_count = 0
            success_count = 0
            
            print(f"\n{'='*60}")
            print(f"🚀 Starting OPTIMIZED certificate extraction")
            print(f"   Input: {input_csv_path}")
            print(f"   Output: {output_csv_path}")
            print(f"   Log: {failed_log_path}")
            print(f"   Batch size: {batch_size}")
            print(f"   Progress update: every {show_every} lines")
            print(f"{'='*60}\n")
            
            batch = []
            
            for line in infile:
                lines_processed += 1
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    # Split CSV at first comma
                    parts = line.split(",", 1)
                    if len(parts) != 2:
                        failed_log.write(f"Line {lines_processed}: Invalid format (no comma separator)\n")
                        failed_count += 1
                        continue
                    
                    fingerprint, pem_b64 = parts
                    batch.append((lines_processed, fingerprint, pem_b64))
                    
                    # Process batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        results = process_batch_with_zcertificate(batch, zcert_path)
                        
                        for line_num, fp, cn, error in results:
                            if cn:
                                writer.writerow([output_idx, cn])
                                output_idx += 1
                                success_count += 1
                            else:
                                failed_log.write(f"Line {line_num}: {error or 'No common_name'} (fp: {fp[:20]}...)\n")
                                failed_count += 1
                        
                        batch = []
                        
                        # Show progress
                        if lines_processed % show_every == 0:
                            print(f"📊 Progress: {lines_processed:,} lines | ✅ {success_count:,} extracted | ❌ {failed_count:,} failed")
                
                except Exception as e:
                    failed_log.write(f"Line {lines_processed}: Unexpected error - {str(e)[:100]}\n")
                    failed_count += 1
                    continue
            
            # Process remaining batch
            if batch:
                results = process_batch_with_zcertificate(batch, zcert_path)
                
                for line_num, fp, cn, error in results:
                    if cn:
                        writer.writerow([output_idx, cn])
                        output_idx += 1
                        success_count += 1
                    else:
                        failed_log.write(f"Line {line_num}: {error or 'No common_name'} (fp: {fp[:20]}...)\n")
                        failed_count += 1
            
            print(f"\n{'='*60}")
            print(f"✅ PROCESS COMPLETED!")
            print(f"{'='*60}")
            print(f"📊 Total lines processed: {lines_processed:,}")
            print(f"✅ Common names extracted: {success_count:,}")
            print(f"❌ Failed/skipped: {failed_count:,}")
            print(f"📄 Output file: {output_csv_path}")
            print(f"📋 Failed log: {failed_log_path}")
            print(f"{'='*60}\n")
            
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    large_csv_path = "raw/2023-12-25-1703466479-https_get_443_certs"  # Your input CSV file path
    output_path = "processed/common_names.csv"  # Output CSV
    zcert_path = "../zcertificate/zcertificate"  # Path to zcertificate binary
    failed_log_path = "logs/check1.txt"  # Log file
    
    # Optimized parameters:
    # batch_size=100 means process 100 certs per zcertificate call (adjust based on testing)
    # show_every=1000 means show progress every 1000 lines
    process_csv_extract_cn_optimized(
        large_csv_path, 
        output_path, 
        zcert_path, 
        failed_log_path, 
        batch_size=500,
        show_every=10000
    )