import csv

# Initialize counters
both = 0
only_errors = 0
only_warnings = 0
neither = 0
total = 0

# For tracking unique items
errors = {}
warnings = {}

try:
    with open('report.csv', 'r') as f:
        reader = csv.DictReader(f)
        
        # Find error and warning columns
        headers = reader.fieldnames
        error_cols = [h for h in headers if h.startswith('Error Details')]
        warning_cols = [h for h in headers if h.startswith('Warning Details')]
        
        for row in reader:
            total += 1
            
            # Check if has errors or warnings
            has_error = False
            has_warning = False
            
            # Check errors
            for col in error_cols:
                if row[col].strip():
                    has_error = True
                    err = row[col].strip()
                    errors[err] = errors.get(err, 0) + 1
            
            # Check warnings
            for col in warning_cols:
                if row[col].strip():
                    has_warning = True
                    warn = row[col].strip()
                    warnings[warn] = warnings.get(warn, 0) + 1
            
            # Count categories
            if has_error and has_warning:
                both += 1
            elif has_error and not has_warning:
                only_errors += 1
            elif not has_error and has_warning:
                only_warnings += 1
            else:
                neither += 1
    
    # Print results
    print("=" * 40)
    print("ANALYSIS RESULTS")
    print("=" * 40)
    print(f"Total certificates: {total}")
    print()
    print(f"With BOTH errors and warnings: {both}")
    print(f"With ONLY errors: {only_errors}")
    print(f"With ONLY warnings: {only_warnings}")
    print(f"With NEITHER: {neither}")
    print()
    
    print("UNIQUE ERRORS:")
    for err, count in sorted(errors.items()):
        print(f"  {err}: {count}")
    print(f"Total unique errors: {len(errors)}")
    print()
    
    print("UNIQUE WARNINGS:")
    for warn, count in sorted(warnings.items()):
        print(f"  {warn}: {count}")
    print(f"Total unique warnings: {len(warnings)}")
    
except FileNotFoundError:
    print("Error: report.csv not found")