import csv

def extract_domains(filepath):
    domains = set()
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        first_row = next(csv.reader(csvfile))
        csvfile.seek(0)
        has_header = all(cell.isalpha() for cell in first_row)
        reader = csv.reader(csvfile)
        if has_header:
            header = next(reader)
            domain_idx = None
            for col in header:
                if col.lower() in ("domain", "domains", "host", "hostname"):
                    domain_idx = header.index(col)
                    break
            if domain_idx is None:
                domain_idx = 0
        else:
            if len(first_row) == 1:
                domain_idx = 0
            elif len(first_row) == 2:
                domain_idx = 0
            else:
                raise ValueError(f"Unexpected CSV structure in {filepath}")
        for row in reader:
            if not row or len(row) <= domain_idx:
                continue
            domains.add(row[domain_idx].strip().lower())  # <--- Lowercase domains here
    return domains

csv1_path = "temp.csv"
csv2_path = "pk-domains-rapid-7.csv"

domains_csv1 = extract_domains(csv1_path)
domains_csv2 = extract_domains(csv2_path)

print("temp.csv domains ",len(domains_csv1))
print("pk-domains-rapid-7.csv domains ",len(domains_csv2))

# for val in domains_csv1:
#     print(val)


unique_domains = domains_csv1 - domains_csv2

print("Unique domains in CSV-1 not present in CSV-2 (case-insensitive):")
for domain in sorted(unique_domains):
    print(domain)
