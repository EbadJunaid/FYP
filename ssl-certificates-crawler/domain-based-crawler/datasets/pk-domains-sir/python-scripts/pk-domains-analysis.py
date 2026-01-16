import pandas as pd
import os
from typing import Set

def is_valid_pk_domain(domain: str) -> bool:
    """Check if domain is a valid .pk domain"""
    if not isinstance(domain, str):
        return False
    domain = domain.strip().lower()
    return domain.endswith('.pk')

def extract_pk_domains_from_csv(csv_path: str, domain_column: str, existing_domains: Set[str]) -> tuple[Set[str], int, int]:
    """
    Extract unique .pk domains from a CSV file
    Returns: (new_domains_set, success_count, failure_count)
    """
    print(f"\n{'='*60}")
    print(f"Processing: {csv_path}")
    print(f"{'='*60}")
    
    if not os.path.exists(csv_path):
        print(f" File not found: {csv_path}")
        return set(), 0, 0
    
    success_count = 0
    failure_count = 0
    new_domains = set()
    
    try:
        # Read CSV in chunks for memory efficiency
        chunk_size = 50000
        total_rows = 0
        
        for chunk in pd.read_csv(csv_path, chunksize=chunk_size, low_memory=False):
            total_rows += len(chunk)
            
            # Check if domain column exists
            if domain_column not in chunk.columns:
                print(f" Column '{domain_column}' not found in {csv_path}")
                print(f"Available columns: {', '.join(chunk.columns)}")
                failure_count += len(chunk)
                continue
            
            # Process each domain
            for domain in chunk[domain_column]:
                if is_valid_pk_domain(domain):
                    domain_clean = domain.strip().lower()
                    
                    # Check if domain is unique (not in existing or newly found)
                    if domain_clean not in existing_domains and domain_clean not in new_domains:
                        new_domains.add(domain_clean)
                        print(f" SUCCESS: Found new .pk domain - {domain_clean}")
                        success_count += 1
                    else:
                        print(f" DUPLICATE: {domain_clean} (already exists)")
                        failure_count += 1
        
        print(f"\n Summary for {os.path.basename(csv_path)}:")
        print(f"   Total rows processed: {total_rows}")
        print(f"   New unique .pk domains: {success_count}")
        print(f"   Duplicates/Failed: {failure_count}")
        
    except Exception as e:
        print(f" Error processing {csv_path}: {str(e)}")
        failure_count += 1
    
    return new_domains, success_count, failure_count

def save_pk_domains_to_csv(domains: Set[str], output_file: str):
    """Save unique .pk domains to CSV with index"""
    print(f"\n{'='*60}")
    print(f"Saving to: {output_file}")
    print(f"{'='*60}")
    
    sorted_domains = sorted(domains)
    df = pd.DataFrame({
        'index': range(1, len(sorted_domains) + 1),
        'domain': sorted_domains
    })
    
    df.to_csv(output_file, index=False)
    print(f" Successfully saved {len(sorted_domains)} unique .pk domains to {output_file}")

def compare_with_existing_pk_urls(my_pk_file: str, existing_pk_file: str):
    """Compare my-pk-urls.csv with pk_urls.csv and find missing domains"""
    print(f"\n{'='*60}")
    print(f"Comparing with: {existing_pk_file}")
    print(f"{'='*60}")
    
    if not os.path.exists(my_pk_file):
        print(f" File not found: {my_pk_file}")
        return
    
    if not os.path.exists(existing_pk_file):
        print(f" File not found: {existing_pk_file}")
        return
    
    try:
        # Read our extracted domains
        my_domains_df = pd.read_csv(my_pk_file)
        my_domains = set(my_domains_df['domain'].str.strip().str.lower())
        
        # Read existing pk_urls.csv (no headers, first column is index, second is domain)
        existing_df = pd.read_csv(existing_pk_file, header=None, names=['index', 'domain'])
        existing_domains = set(existing_df['domain'].str.strip().str.lower())
        
        # Find domains in our file but not in existing file
        not_found_in_existing = my_domains - existing_domains
        
        print(f"\n Comparison Results:")
        print(f"   Domains in my-pk-urls.csv: {len(my_domains)}")
        print(f"   Domains in pk_urls.csv: {len(existing_domains)}")
        print(f"   Domains NOT FOUND in pk_urls.csv: {len(not_found_in_existing)}")
        
        if not_found_in_existing:
            print(f"\n Domains present in my-pk-urls.csv but NOT in pk_urls.csv:")
            print(f"{'='*60}")
            for idx, domain in enumerate(sorted(not_found_in_existing), 1):
                print(f"{idx}. {domain}")
        else:
            print("\n All domains in my-pk-urls.csv are already present in pk_urls.csv")
        
        return not_found_in_existing
        
    except Exception as e:
        print(f" Error during comparison: {str(e)}")
        return set()

def main():
    """Main execution function"""
    print("="*60)
    print("PK DOMAIN EXTRACTOR & COMPARATOR")
    print("="*60)
    
    # Define CSV files
    csv_files = [
        ('cloudflare-radar_top-100-domains_pk_20251023-20251030.csv', 'domain'),
        ('cloudflare-radar_top-1000000-domains_20251023-20251030(1).csv', 'domain'),
        ('majestic_million.csv', 'Domain')  # Note: Capital 'D' based on your structure
    ]
    
    output_file = 'my-pk-urls.csv'
    comparison_file = 'pk_urls.csv'
    
    # Track all unique domains and counts
    all_pk_domains = set()
    total_success = 0
    total_failure = 0
    
    # Process each CSV file
    for csv_file, domain_col in csv_files:
        new_domains, success, failure = extract_pk_domains_from_csv(
            csv_file, domain_col, all_pk_domains
        )
        all_pk_domains.update(new_domains)
        total_success += success
        total_failure += failure
    
    # Save all unique .pk domains to file
    if all_pk_domains:
        save_pk_domains_to_csv(all_pk_domains, output_file)
    else:
        print("\n  No .pk domains found in any CSV files!")
        return
    
    # Print overall summary
    print(f"\n{'='*60}")
    print(f"OVERALL SUMMARY")
    print(f"{'='*60}")
    print(f" Total successful appends: {total_success}")
    print(f" Total failed/duplicate appends: {total_failure}")
    print(f" Total unique .pk domains extracted: {len(all_pk_domains)}")
    
    # Compare with existing pk_urls.csv
    compare_with_existing_pk_urls(output_file, comparison_file)
    
    print(f"\n{'='*60}")
    print("PROCESS COMPLETED")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()