#!/usr/bin/env python3
"""
Extract valid .pk domains from multiple CSV files and combine into unique list.
Valid .pk domains must end with .pk (e.g., example.pk, domain.com.pk)
"""

import csv
from pathlib import Path

def is_valid_pk_domain(domain):
    """
    Check if domain is a valid .pk domain (must end with .pk)
    
    Args:
        domain: Domain string to check
    
    Returns:
        bool: True if valid .pk domain, False otherwise
    """
    domain = domain.strip().lower()
    
    # Check if domain ends with .pk
    if not domain.endswith('.pk'):
        return False
    
    # Basic validation: must have at least one character before .pk
    # and should not be just ".pk"
    if len(domain) <= 3:  # ".pk" is 3 characters
        return False
    
    # Optional: Check for valid characters (letters, numbers, dots, hyphens)
    # Remove .pk suffix and check remaining part
    domain_without_pk = domain[:-3]  # Remove last 3 chars (.pk)
    
    # Must not start or end with dot or hyphen
    if domain_without_pk.startswith(('.', '-')) or domain_without_pk.endswith(('.', '-')):
        return False
    
    # Check for valid characters: alphanumeric, dots, and hyphens only
    allowed_chars = set('abcdefghijklmnopqrstuvwxyz0123456789.-')
    if not all(c in allowed_chars for c in domain_without_pk):
        return False
    
    return True

def extract_pk_domains_from_file(filename):
    """
    Extract valid .pk domains from a CSV file.
    
    Args:
        filename: Path to CSV file
    
    Returns:
        set: Set of valid .pk domains found in the file
    """
    pk_domains = set()
    
    try:
        with open(filename, 'r', encoding='utf-8') as file:
            csv_reader = csv.reader(file)
            
            for row in csv_reader:
                # Skip empty rows
                if not row or len(row) < 2:
                    continue
                
                # Domain is in the second column (index 1)
                domain = row[1].strip()
                
                # Check if it's a valid .pk domain
                if is_valid_pk_domain(domain):
                    pk_domains.add(domain.lower())
        
        print(f"✓ Processed {filename}: Found {len(pk_domains)} valid .pk domains")
        
    except FileNotFoundError:
        print(f"✗ Error: File '{filename}' not found!")
    except Exception as e:
        print(f"✗ Error processing '{filename}': {str(e)}")
    
    return pk_domains

def main():
    """Main function to process all CSV files and create combined output."""
    
    # Input files
    input_files = [
        '../raw/top-1m.csv',
        '../raw/tranco_W4V99-1m.csv',
        '../raw/tranco_W4V99.csv'
    ]
    
    # Output file
    output_file = '../processed/hell-2.csv'
    
    print("=" * 60)
    print("Valid .pk Domain Extractor")
    print("=" * 60)
    print()
    
    # Collect all unique .pk domains from all files
    all_pk_domains = set()
    
    for filename in input_files:
        domains = extract_pk_domains_from_file(filename)
        all_pk_domains.update(domains)
    
    print()
    print("-" * 60)
    print(f"Total unique .pk domains found: {len(all_pk_domains)}")
    print("-" * 60)
    print()
    
    # Sort domains for better readability
    sorted_domains = sorted(all_pk_domains)
    
    # Write to output file
    try:
        with open(output_file, 'w', encoding='utf-8', newline='') as file:
            csv_writer = csv.writer(file)
            
            # Write each domain with an index
            for index, domain in enumerate(sorted_domains, start=1):
                csv_writer.writerow([index, domain])
        
        print(f"✓ Successfully created '{output_file}'")
        print(f"✓ Total entries written: {len(sorted_domains)}")
        print()
        
        # Display first 10 domains as sample
        if sorted_domains:
            print("Sample of extracted domains (first 10):")
            print("-" * 60)
            for i, domain in enumerate(sorted_domains[:10], start=1):
                print(f"{i}. {domain}")
            if len(sorted_domains) > 10:
                print(f"... and {len(sorted_domains) - 10} more")
        
    except Exception as e:
        print(f"✗ Error writing to '{output_file}': {str(e)}")
    
    print()
    print("=" * 60)
    print("Process completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()