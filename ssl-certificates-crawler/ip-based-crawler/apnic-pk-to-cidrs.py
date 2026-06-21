#!/usr/bin/env python3
# apnic_pk_to_cidrs.py
import sys, ipaddress

def ranges_from_apnic(file_in, file_out):
    prefixes = set()
    with open(file_in, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split('|')
            if len(parts) < 5:
                continue
            cc = parts[1].upper()
            typ = parts[2].lower()
            start = parts[3]
            value = parts[4]
            if cc != 'PK' or typ != 'ipv4':
                continue
            count = int(value)
            start_ip = ipaddress.IPv4Address(start)
            end_ip = ipaddress.IPv4Address(int(start_ip) + count - 1)
            for net in ipaddress.summarize_address_range(start_ip, end_ip):
                prefixes.add(str(net))
    with open(file_out, 'w', encoding='utf-8') as out:
        for p in sorted(prefixes, key=lambda x: (ipaddress.IPv4Network(x).network_address, ipaddress.IPv4Network(x).prefixlen)):
            out.write(p + "\n")
    print(f"Wrote {len(prefixes)} prefixes to {file_out}")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python apnic_pk_to_cidrs.py nirsoft-ip-range.csv nirsoft.txt")
        sys.exit(1)
    ranges_from_apnic(sys.argv[1], sys.argv[2])
