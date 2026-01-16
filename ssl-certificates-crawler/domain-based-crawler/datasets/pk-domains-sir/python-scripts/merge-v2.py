import pandas as pd
import os
import csv


def detect_csv_format(csv_path: str):
    """
    Detect if CSV has headers and determine the domain column
    Returns: (has_header, column_to_use)
    """
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            sample = f.read(8192)  # Read first 8KB for detection
            
            # Use CSV Sniffer to detect if file has header
            sniffer = csv.Sniffer()
            has_header = sniffer.has_header(sample)
            
        return has_header
            
    except Exception as e:
        print(f"⚠️  Detection failed for {csv_path}, assuming no header: {str(e)}")
        return False


def read_pk_domains_from_csv(csv_path: str):
    """
    Read domains from a CSV file (auto-detects format)
    Returns: set of domains
    """
    print(f"\n📂 Reading: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"❌ File not found: {csv_path}")
        return set()
    
    try:
        # Detect if CSV has headers
        has_header = detect_csv_format(csv_path)
        
        if has_header:
            print(f"ℹ️  CSV has HEADERS - attempting to find 'domain' column")
            df = pd.read_csv(csv_path)
            
            # Try to find domain column (case-insensitive)
            domain_col = None
            for col in df.columns:
                if 'domain' in str(col).lower():
                    domain_col = col
                    break
            
            if domain_col is None:
                print(f"⚠️  No 'domain' column found. Available columns: {', '.join(map(str, df.columns))}")
                print(f"⚠️  Trying to use second column as domain column...")
                # Fallback to second column (index 1)
                if len(df.columns) >= 2:
                    domain_col = df.columns[1]
                else:
                    domain_col = df.columns[0]
            
            print(f"✅ Using column: '{domain_col}'")
            domains = set(df[domain_col].dropna().astype(str).str.strip().str.lower())
            
        else:
            print(f"ℹ️  CSV has NO HEADERS - using column index 1 (2nd column)")
            df = pd.read_csv(csv_path, header=None)
            
            # Use second column (index 1) as domain column for format: 1,google.com
            if len(df.columns) >= 2:
                domains = set(df[1].dropna().astype(str).str.strip().str.lower())
            else:
                # Fallback to first column if only one column exists
                domains = set(df[0].dropna().astype(str).str.strip().str.lower())
        
        print(f"✅ Loaded {len(domains)} domains from {os.path.basename(csv_path)}")
        return domains
        
    except Exception as e:
        print(f"❌ Error reading {csv_path}: {str(e)}")
        import traceback
        traceback.print_exc()
        return set()


def merge_pk_domains(file1: str, file2: str, output_file: str):
    """
    Merge two CSV files containing .pk domains and create a new CSV with all unique domains
    Automatically detects CSV format (with or without headers)
    
    Args:
        file1: Path to first CSV file
        file2: Path to second CSV file
        output_file: Path to output merged CSV file
    """
    print("="*60)
    print("PK DOMAIN CSV MERGER (AUTO-DETECT FORMAT)")
    print("="*60)
    
    # Read domains from first CSV (auto-detect format)
    domains_from_file1 = read_pk_domains_from_csv(file1)
    
    # Read domains from second CSV (auto-detect format)
    domains_from_file2 = read_pk_domains_from_csv(file2)
    
    if not domains_from_file1 and not domains_from_file2:
        print("\n❌ No domains found in any file!")
        return
    
    # Merge and get unique domains
    print(f"\n🔄 Merging domains...")
    all_unique_domains = domains_from_file1.union(domains_from_file2)
    
    # Sort domains alphabetically
    sorted_domains = sorted(all_unique_domains)
    
    # Create new DataFrame with index starting from 1
    merged_df = pd.DataFrame({
        'index': range(1, len(sorted_domains) + 1),
        'domain': sorted_domains
    })
    
    # Save to new CSV
    merged_df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"MERGE SUMMARY")
    print(f"{'='*60}")
    print(f"📊 Domains in {os.path.basename(file1)}: {len(domains_from_file1)}")
    print(f"📊 Domains in {os.path.basename(file2)}: {len(domains_from_file2)}")
    print(f"📊 Total combined domains: {len(domains_from_file1) + len(domains_from_file2)}")
    print(f"✅ Unique domains after merge: {len(all_unique_domains)}")
    print(f"🗑️  Duplicates removed: {len(domains_from_file1) + len(domains_from_file2) - len(all_unique_domains)}")
    print(f"\n💾 Successfully saved merged domains to: {output_file}")
    print(f"{'='*60}")
    
    # Show first 10 domains as preview
    print(f"\n🔍 Preview of merged domains (first 10):")
    print(f"{'='*60}")
    for idx, domain in enumerate(sorted_domains[:10], 1):
        print(f"{idx}. {domain}")
    if len(sorted_domains) > 10:
        print(f"... and {len(sorted_domains) - 10} more domains")


def merge_multiple_pk_domains(file_list: list, output_file: str):
    """
    Merge multiple CSV files containing .pk domains
    Automatically detects CSV format (with or without headers)
    
    Args:
        file_list: List of CSV file paths to merge
        output_file: Path to output merged CSV file
    """
    print("="*60)
    print("MULTIPLE PK DOMAIN CSV MERGER (AUTO-DETECT FORMAT)")
    print("="*60)
    
    all_domains = set()
    file_stats = {}
    
    # Read domains from all CSV files
    for csv_file in file_list:
        domains = read_pk_domains_from_csv(csv_file)
        file_stats[csv_file] = len(domains)
        all_domains.update(domains)
    
    if not all_domains:
        print("\n❌ No domains found in any file!")
        return
    
    # Sort domains alphabetically
    sorted_domains = sorted(all_domains)
    
    # Create new DataFrame with index starting from 1
    merged_df = pd.DataFrame({
        'index': range(1, len(sorted_domains) + 1),
        'domain': sorted_domains
    })
    
    # Save to new CSV
    merged_df.to_csv(output_file, index=False)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"MERGE SUMMARY")
    print(f"{'='*60}")
    
    total_domains = sum(file_stats.values())
    for file_path, count in file_stats.items():
        print(f"📊 Domains in {os.path.basename(file_path)}: {count}")
    
    print(f"\n📊 Total combined domains: {total_domains}")
    print(f"✅ Unique domains after merge: {len(all_domains)}")
    print(f"🗑️  Duplicates removed: {total_domains - len(all_domains)}")
    print(f"\n💾 Successfully saved merged domains to: {output_file}")
    print(f"{'='*60}")
    
    # Show first 10 domains as preview
    print(f"\n🔍 Preview of merged domains (first 10):")
    print(f"{'='*60}")
    for idx, domain in enumerate(sorted_domains[:10], 1):
        print(f"{idx}. {domain}")
    if len(sorted_domains) > 10:
        print(f"... and {len(sorted_domains) - 10} more domains")


def main():
    """Main execution function"""
    
    # Example 1: Merge TWO CSV files
    print("\n" + "="*60)
    print("EXAMPLE 1: MERGE TWO FILES")
    print("="*60)
    
    my_pk_file = 'pk-domains-rapid-7.csv'
    existing_pk_file = 'merged-pk-tranco.csv'
    output_merged_file = 'merged-pk-tranco-rapid.csv'
    
    merge_pk_domains(my_pk_file, existing_pk_file, output_merged_file)
    
    # Example 2: Merge MULTIPLE CSV files (uncomment to use)
    # print("\n" + "="*60)
    # print("EXAMPLE 2: MERGE MULTIPLE FILES")
    # print("="*60)
    # 
    # file_list = [
    #     'my-pk-urls.csv',
    #     'pk_urls.csv',
    #     '../Tranco/top-1m.csv',
    #     'another-file.csv'
    # ]
    # output_merged_file = 'all-merged.csv'
    # 
    # merge_multiple_pk_domains(file_list, output_merged_file)
    
    print(f"\n{'='*60}")
    print("PROCESS COMPLETED ✅")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
