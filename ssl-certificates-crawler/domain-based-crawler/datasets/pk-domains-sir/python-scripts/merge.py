import pandas as pd
import os

def merge_pk_domains(file1: str, file2: str, output_file: str):
    """
    Merge two CSV files containing .pk domains and create a new CSV with all unique domains
    
    Args:
        file1: Path to my-pk-urls.csv (has headers: index, domain)
        file2: Path to pk_urls.csv (no headers: index, domain)
        output_file: Path to output merged CSV file
    """
    print("="*60)
    print("PK DOMAIN CSV MERGER")
    print("="*60)
    
    # Check if files exist
    if not os.path.exists(file1):
        print(f" File not found: {file1}")
        return
    
    if not os.path.exists(file2):
        print(f" File not found: {file2}")
        return
    
    try:
        # Read first CSV (my-pk-urls.csv with headers)
        print(f"\n Reading: {file1}")
        df1 = pd.read_csv(file1)
        domains_from_file1 = set(df1['domain'].str.strip().str.lower())
        print(f" Loaded {len(domains_from_file1)} domains from {file1}")
        
        # Read second CSV (pk_urls.csv without headers)
        print(f"\n Reading: {file2}")
        df2 = pd.read_csv(file2, header=None, names=['index', 'domain'])
        domains_from_file2 = set(df2['domain'].str.strip().str.lower())
        print(f"  Loaded {len(domains_from_file2)} domains from {file2}")
        
        # Merge and get unique domains
        print(f"\n Merging domains...")
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
        print(f" Domains in {file1}: {len(domains_from_file1)}")
        print(f" Domains in {file2}: {len(domains_from_file2)}")
        print(f" Total combined domains: {len(domains_from_file1) + len(domains_from_file2)}")
        print(f" Unique domains after merge: {len(all_unique_domains)}")
        print(f" Duplicates removed: {len(domains_from_file1) + len(domains_from_file2) - len(all_unique_domains)}")
        print(f"\n Successfully saved merged domains to: {output_file}")
        print(f"{'='*60}")
        
        # Show first 10 domains as preview
        print(f"\n Preview of merged domains (first 10):")
        print(f"{'='*60}")
        for idx, domain in enumerate(sorted_domains[:10], 1):
            print(f"{idx}. {domain}")
        if len(sorted_domains) > 10:
            print(f"... and {len(sorted_domains) - 10} more domains")
        
    except Exception as e:
        print(f" Error during merge: {str(e)}")
        import traceback
        traceback.print_exc()

def main():
    """Main execution function"""
    
    # Define file paths
    my_pk_file = 'my-pk-urls.csv'
    existing_pk_file = 'pk_urls.csv'
    output_merged_file = '1.csv'
    
    # Perform merge
    merge_pk_domains(my_pk_file, existing_pk_file, output_merged_file)
    
    print(f"\n{'='*60}")
    print("PROCESS COMPLETED ")
    print(f"{'='*60}")
    print(f"Output file: {output_merged_file}")

if __name__ == "__main__":
    main()