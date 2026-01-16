#!/usr/bin/env python3
"""
Hybrid Certificate Parser - Best of Both Worlds
1. Try cryptography first (fast, handles 95%+ certificates)
2. Fallback to zcertificate for failures (slower but more lenient)
"""

import csv
import os
import json
import subprocess
import tempfile
from cryptography import x509
from cryptography.hazmat.backends import default_backend
import base64

# ============================================================================
# CRYPTOGRAPHY PARSING (Fast)
# ============================================================================

def extract_cn_cryptography(pem_data):
    """
    Extract common name using cryptography library (fast but strict)
    Returns: (common_name, error_msg)
    """
    try:
        # Add PEM headers if missing
        if "-----BEGIN CERTIFICATE-----" not in pem_data:
            pem_data = (
                "-----BEGIN CERTIFICATE-----\n"
                + pem_data.strip()
                + "\n-----END CERTIFICATE-----\n"
            )
        
        cert = x509.load_pem_x509_certificate(pem_data.encode('utf-8'), default_backend())
        subject = cert.subject
        common_names = [attr.value for attr in subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)]
        
        if common_names:
            return (common_names[0], None)
        else:
            return (None, "No common_name in certificate")
    
    except Exception as e:
        return (None, f"Cryptography parse failed: {type(e).__name__}")

# ============================================================================
# ZCERTIFICATE PARSING (Slow but lenient)
# ============================================================================

def extract_cn_zcertificate(pem_data, zcert_path="./zcertificate"):
    """
    Extract common name using zcertificate (slower but handles malformed certs)
    Returns: (common_name, error_msg)
    """
    try:
        # Ensure proper PEM format
        if "-----BEGIN CERTIFICATE-----" not in pem_data:
            pem_data = (
                "-----BEGIN CERTIFICATE-----\n"
                + pem_data.strip()
                + "\n-----END CERTIFICATE-----"
            )
        
        # Run zcertificate
        process = subprocess.Popen(
            [zcert_path, '-format', 'pem'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=pem_data, timeout=10)
        
        if process.returncode != 0:
            return (None, f"zcertificate error: {stderr[:100]}")
        
        # Parse JSON output
        cert_json = json.loads(stdout)
        
        if 'parsed' in cert_json:
            parsed = cert_json['parsed']
            if 'subject' in parsed and 'common_name' in parsed['subject']:
                common_names = parsed['subject']['common_name']
                if isinstance(common_names, list) and len(common_names) > 0:
                    return (common_names[0], None)
                elif isinstance(common_names, str):
                    return (common_names, None)
        
        return (None, "No common_name in zcertificate output")
    
    except json.JSONDecodeError as e:
        return (None, f"JSON parse error: {str(e)[:100]}")
    except subprocess.TimeoutExpired:
        return (None, "zcertificate timeout")
    except Exception as e:
        return (None, f"zcertificate error: {str(e)[:100]}")

# ============================================================================
# BATCH ZCERTIFICATE PROCESSING (For multiple failures at once)
# ============================================================================

def process_batch_zcertificate(failed_certs, zcert_path="./zcertificate"):
    """
    Process multiple failed certificates in a single zcertificate call
    Returns: dict of {line_num: (common_name, error)}
    """
    if not failed_certs:
        return {}
    
    results = {}
    
    # Create temp file with all failed certificates
    with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as tmp:
        tmp_path = tmp.name
        cert_map = []  # Track which cert is which
        
        for line_num, fingerprint, pem_data in failed_certs:
            # Ensure proper PEM format
            if "-----BEGIN CERTIFICATE-----" not in pem_data:
                pem_data = (
                    "-----BEGIN CERTIFICATE-----\n"
                    + pem_data.strip()
                    + "\n-----END CERTIFICATE-----"
                )
            tmp.write(pem_data + "\n")
            cert_map.append((line_num, fingerprint))
    
    try:
        # Process entire batch with zcertificate
        process = subprocess.Popen(
            [zcert_path, '-format', 'pem', '-workers', '4'],
            stdin=open(tmp_path, 'r'),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(timeout=60)
        
        if process.returncode != 0:
            # Batch failed
            for line_num, _ in cert_map:
                results[line_num] = (None, f"Batch zcertificate failed: {stderr[:100]}")
        else:
            # Parse JSON outputs
            json_lines = stdout.strip().split('\n')
            
            for (line_num, fingerprint), json_line in zip(cert_map, json_lines):
                if json_line.strip():
                    try:
                        cert_json = json.loads(json_line)
                        
                        if 'parsed' in cert_json:
                            parsed = cert_json['parsed']
                            if 'subject' in parsed and 'common_name' in parsed['subject']:
                                common_names = parsed['subject']['common_name']
                                if isinstance(common_names, list) and len(common_names) > 0:
                                    results[line_num] = (common_names[0], None)
                                elif isinstance(common_names, str):
                                    results[line_num] = (common_names, None)
                                else:
                                    results[line_num] = (None, "No common_name in zcertificate")
                            else:
                                results[line_num] = (None, "No common_name in zcertificate")
                        else:
                            results[line_num] = (None, "Invalid zcertificate JSON")
                    except json.JSONDecodeError as e:
                        results[line_num] = (None, f"JSON parse error: {str(e)[:50]}")
                else:
                    results[line_num] = (None, "Empty zcertificate output")
    
    except subprocess.TimeoutExpired:
        for line_num, _ in cert_map:
            results[line_num] = (None, "Batch timeout")
    except Exception as e:
        for line_num, _ in cert_map:
            results[line_num] = (None, f"Batch error: {str(e)[:100]}")
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except:
            pass
    
    return results

# ============================================================================
# MAIN HYBRID PROCESSING
# ============================================================================

def check_zcertificate_available(zcert_path="./zcertificate"):
    """Check if zcertificate is available"""
    try:
        process = subprocess.Popen(
            [zcert_path, '-help'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        process.communicate(timeout=5)
        return True
    except:
        return False

def process_csv_hybrid(
    input_csv_path,
    output_csv_path,
    zcert_path="./zcertificate",
    failed_log_path="failed-log.log",
    use_zcertificate_fallback=True,
    fallback_batch_size=50,
    show_every=1000
):
    """
    Hybrid certificate extraction:
    1. Try cryptography (fast)
    2. Fallback to zcertificate for failures (slow but thorough)
    
    Args:
        input_csv_path: Input CSV with fingerprint,pem_data
        output_csv_path: Output CSV with index,common_name
        zcert_path: Path to zcertificate binary
        failed_log_path: Log file for failures
        use_zcertificate_fallback: Enable zcertificate for cryptography failures
        fallback_batch_size: Batch size for zcertificate fallback processing
        show_every: Progress update frequency
    """
    if not os.path.exists(input_csv_path):
        print(f"❌ Input file not found: {input_csv_path}")
        return
    
    # Check zcertificate availability if fallback is enabled
    zcert_available = False
    if use_zcertificate_fallback:
        zcert_available = check_zcertificate_available(zcert_path)
        if zcert_available:
            print(f"✅ zcertificate found: Fallback enabled")
        else:
            print(f"⚠️  zcertificate not found: Fallback disabled")
            use_zcertificate_fallback = False
    
    print(f"\n{'='*60}")
    print(f"🚀 HYBRID CERTIFICATE EXTRACTION")
    print(f"{'='*60}")
    print(f"📂 Input: {input_csv_path}")
    print(f"📄 Output: {output_csv_path}")
    print(f"📋 Failed log: {failed_log_path}")
    print(f"⚡ Strategy: Cryptography first → zcertificate fallback")
    print(f"{'='*60}\n")
    
    try:
        # Phase 1: Process with cryptography (fast)
        print(f"{'='*60}")
        print(f"PHASE 1: Fast parsing with cryptography library")
        print(f"{'='*60}\n")
        
        crypto_success = 0
        crypto_failed = 0
        lines_processed = 0
        failed_certs = []  # Store failures for zcertificate fallback
        
        # Temporary storage for results
        temp_results = []
        
        with open(input_csv_path, "r", encoding="utf-8") as infile:
            for line in infile:
                lines_processed += 1
                line = line.strip()
                
                if not line:
                    continue
                
                try:
                    parts = line.split(",", 1)
                    if len(parts) != 2:
                        continue
                    
                    fingerprint, pem_b64 = parts
                    
                    # Try base64 decode if needed
                    pem_str = pem_b64
                    if not pem_b64.startswith("-----BEGIN CERTIFICATE-----"):
                        try:
                            pem_bytes = base64.b64decode(pem_b64, validate=True)
                            pem_str = pem_bytes.decode("utf-8")
                        except:
                            pem_str = pem_b64
                    
                    # Try cryptography first
                    cn, error = extract_cn_cryptography(pem_str)
                    
                    if cn:
                        temp_results.append((lines_processed, cn, None))
                        crypto_success += 1
                    else:
                        # Store for zcertificate fallback
                        failed_certs.append((lines_processed, fingerprint, pem_str))
                        crypto_failed += 1
                    
                    # Progress update
                    if lines_processed % show_every == 0:
                        print(f"📊 Cryptography: {lines_processed:,} lines | ✅ {crypto_success:,} success | ❌ {crypto_failed:,} failed")
                
                except Exception as e:
                    failed_certs.append((lines_processed, "", ""))
                    crypto_failed += 1
        
        print(f"\n✅ Phase 1 Complete:")
        print(f"   Total processed: {lines_processed:,}")
        print(f"   Cryptography success: {crypto_success:,} ({(crypto_success/lines_processed*100):.1f}%)")
        print(f"   Cryptography failed: {crypto_failed:,} ({(crypto_failed/lines_processed*100):.1f}%)")
        
        # Phase 2: Process failures with zcertificate (if enabled)
        zcert_success = 0
        zcert_failed = 0
        
        if use_zcertificate_fallback and failed_certs:
            print(f"\n{'='*60}")
            print(f"PHASE 2: Fallback processing with zcertificate")
            print(f"{'='*60}")
            print(f"Processing {len(failed_certs):,} failed certificates...\n")
            
            # Process failures in batches
            for i in range(0, len(failed_certs), fallback_batch_size):
                batch = failed_certs[i:i + fallback_batch_size]
                batch_results = process_batch_zcertificate(batch, zcert_path)
                
                for line_num, fp, pem in batch:
                    if line_num in batch_results:
                        cn, error = batch_results[line_num]
                        if cn:
                            temp_results.append((line_num, cn, None))
                            zcert_success += 1
                        else:
                            temp_results.append((line_num, None, error or "zcertificate failed"))
                            zcert_failed += 1
                
                # Progress update
                processed_so_far = min(i + fallback_batch_size, len(failed_certs))
                if processed_so_far % (show_every // 10) == 0 or processed_so_far == len(failed_certs):
                    print(f"⚡ zcertificate: {processed_so_far:,}/{len(failed_certs):,} processed | ✅ {zcert_success:,} recovered")
            
            print(f"\n✅ Phase 2 Complete:")
            print(f"   zcertificate recovered: {zcert_success:,} ({(zcert_success/crypto_failed*100):.1f}% of failures)")
            print(f"   Still failed: {zcert_failed:,}")
        
        # Phase 3: Write results
        print(f"\n{'='*60}")
        print(f"PHASE 3: Writing results")
        print(f"{'='*60}\n")
        
        # Sort by line number to maintain order
        temp_results.sort(key=lambda x: x[0])
        
        with open(output_csv_path, "w", encoding="utf-8", newline="") as outfile, \
             open(failed_log_path, "w", encoding="utf-8") as failed_log:
            
            writer = csv.writer(outfile, quoting=csv.QUOTE_MINIMAL)
            output_idx = 1
            
            for line_num, cn, error in temp_results:
                if cn:
                    writer.writerow([output_idx, cn])
                    output_idx += 1
                else:
                    failed_log.write(f"Line {line_num}: {error}\n")
        
        # Final statistics
        total_success = crypto_success + zcert_success
        total_failed = crypto_failed - zcert_success + zcert_failed
        
        print(f"{'='*60}")
        print(f"✅ HYBRID EXTRACTION COMPLETE!")
        print(f"{'='*60}")
        print(f"📊 STATISTICS:")
        print(f"   Total lines processed: {lines_processed:,}")
        print(f"   ✅ Cryptography success: {crypto_success:,}")
        print(f"   ⚡ zcertificate recovered: {zcert_success:,}")
        print(f"   📝 Total extracted: {total_success:,} ({(total_success/lines_processed*100):.1f}%)")
        print(f"   ❌ Total failed: {total_failed:,} ({(total_failed/lines_processed*100):.1f}%)")
        print(f"\n📄 Output: {output_csv_path}")
        print(f"📋 Failed log: {failed_log_path}")
        print(f"{'='*60}\n")
    
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    input_file = "raw/2023-12-25-1703466479-https_get_443_certs"  # Your input CSV
    output_file = "processed/hell-no.csv"  # Output CSV
    zcert_path = "../zcertificate/zcertificate"  # zcertificate binary path
    failed_log = "logs/check2.log"  # Failed certificates log
    
    # Run hybrid extraction
    process_csv_hybrid(
        input_csv_path=input_file,
        output_csv_path=output_file,
        zcert_path=zcert_path,
        failed_log_path=failed_log,
        use_zcertificate_fallback=True,  # Enable zcertificate fallback
        fallback_batch_size=50,  # Process 50 failures at once with zcertificate
        show_every=1000  # Progress every 1000 lines
    )