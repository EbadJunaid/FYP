import { jsPDF } from 'jspdf';
import autoTable from 'jspdf-autotable';
import Papa from 'papaparse';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// ── Types ──────────────────────────────────────────────────────────────

export interface ExportColumn {
    header: string;
    key: string;
    formatter?: (value: unknown, row: Record<string, unknown>) => string;
}

export interface ActiveFilter {
    type: string;
    value?: string;
    month?: string;
    year?: string;
}

// ── CSV (client-side) ──────────────────────────────────────────────────

export function downloadCSV(
    data: Record<string, unknown>[],
    columns: ExportColumn[],
    filename: string,
) {
    const headerRow = columns.map((c) => c.header);
    const rows = data.map((row) =>
        columns.map((c) => {
            const raw = row[c.key];
            return c.formatter ? c.formatter(raw, row) : String(raw ?? '');
        }),
    );

    const csvContent = [headerRow, ...rows]
        .map((row) =>
            row
                .map((cell) => `"${String(cell).replace(/"/g, '""')}"`)
                .join(','),
        )
        .join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ── PDF (client-side) ──────────────────────────────────────────────────

export function downloadPDF(
    data: Record<string, unknown>[],
    columns: ExportColumn[],
    title: string,
    filename: string,
) {
    const doc = new jsPDF({ orientation: columns.length > 6 ? 'landscape' : 'portrait' });

    // Title
    doc.setFontSize(14);
    doc.text(title, 14, 20);

    // Date
    doc.setFontSize(9);
    doc.text(`Exported ${new Date().toLocaleDateString()}`, 14, 27);

    autoTable(doc, {
        startY: 32,
        head: [columns.map((c) => c.header)],
        body: data.map((row) =>
            columns.map((c) => {
                const raw = row[c.key];
                return c.formatter ? c.formatter(raw, row) : String(raw ?? '');
            }),
        ),
        styles: { fontSize: 7, cellPadding: 2 },
        headStyles: { fillColor: [55, 65, 81] },
        alternateRowStyles: { fillColor: [245, 245, 245] },
        margin: { left: 14, right: 14 },
    });

    doc.save(`${filename}.pdf`);
}

// ── Fetch CSV from server & parse ──────────────────────────────────────

export async function fetchCSVAsData(
    url: string,
): Promise<Record<string, unknown>[]> {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);
    const csvText = await response.text();

    return new Promise((resolve, reject) => {
        Papa.parse(csvText, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => resolve(results.data as Record<string, unknown>[]),
            error: (err: Error) => reject(err),
        });
    });
}

// ── Build server export URL from filter ────────────────────────────────

export function buildExportUrl(activeFilter: ActiveFilter): string {
    const params = new URLSearchParams();

    switch (activeFilter.type) {
        case 'active':
            params.append('status', 'VALID');
            break;
        case 'expired':
            params.append('status', 'EXPIRED');
            break;
        case 'expiringSoon':
            params.append('status', 'EXPIRING_SOON');
            break;
        case 'vulnerabilities':
            params.append('has_vulnerabilities', 'true');
            break;
        case 'ca':
            if (activeFilter.value) params.append('issuer', activeFilter.value);
            break;
        case 'geographic':
            if (activeFilter.value) params.append('country', activeFilter.value);
            break;
        case 'encryption':
            if (activeFilter.value) params.append('encryption_type', activeFilter.value);
            break;
        case 'validityTrend':
            if (activeFilter.value) {
                const monthNames = [
                    'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                    'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec',
                ];
                const parts = activeFilter.value.split(' ');
                const monthName = parts[0];
                const year = parseInt(parts[1] || '2026');
                const monthIndex = monthNames.indexOf(monthName) + 1;
                if (monthIndex > 0) {
                    params.append('expiring_month', monthIndex.toString());
                    params.append('expiring_year', year.toString());
                }
            }
            break;
        case 'bucket':
            if (activeFilter.value) params.append('validity_bucket', activeFilter.value);
            break;
        case 'expiringDays':
            if (activeFilter.value) params.append('expiring_days', activeFilter.value);
            break;
        case 'issuedMonth':
            if (activeFilter.value) {
                const [year, month] = activeFilter.value.split('-').map(Number);
                if (month > 0 && year > 0) {
                    params.append('issued_month', month.toString());
                    params.append('issued_year', year.toString());
                }
            }
            break;
        case 'issuedWithinDays':
            if (activeFilter.value) params.append('issued_within_days', activeFilter.value);
            break;
        case 'expiringMonth':
            if (activeFilter.value) {
                const [year, month] = activeFilter.value.split('-').map(Number);
                if (month > 0 && year > 0) {
                    params.append('expiring_month', month.toString());
                    params.append('expiring_year', year.toString());
                }
            }
            break;
        case 'expiringRange':
            if (activeFilter.value) {
                const parts = activeFilter.value.split('::');
                if (parts.length >= 2) {
                    params.append('expiring_start', parts[0]);
                    params.append('expiring_end', parts[1]);
                }
            }
            break;
        case 'expiredMonth':
            if (activeFilter.value) {
                const [year, month] = activeFilter.value.split('-').map(Number);
                if (month > 0 && year > 0) {
                    params.append('expiring_month', month.toString());
                    params.append('expiring_year', year.toString());
                }
            }
            break;
        case 'weakHash':
            params.append('weak_hash', 'true');
            break;
        case 'selfSigned':
            params.append('self_signed', 'true');
            break;
        case 'signatureAlgorithm':
            if (activeFilter.value) params.append('signature_algorithm', activeFilter.value);
            break;
        case 'hashType':
            if (activeFilter.value) params.append('hash_type', activeFilter.value);
            break;
        case 'keySize':
            if (activeFilter.value) params.append('encryption_type', activeFilter.value);
            break;
        case 'heatmap':
            if (activeFilter.value) {
                const [issuer, second] = activeFilter.value.split('::');
                if (issuer) params.append('issuer', issuer);
                if (second) {
                    if (['DV', 'OV', 'EV', 'Unknown'].includes(second)) {
                        params.append('validation_level', second);
                    } else {
                        params.append('encryption_type', second.replace('-', ' '));
                    }
                }
            }
            break;
        case 'issuer':
            if (activeFilter.value) params.append('issuer', activeFilter.value);
            break;
        case 'san':
            if (activeFilter.value) {
                if (activeFilter.value === 'wildcard') {
                    params.append('san_type', 'wildcard');
                } else if (activeFilter.value === 'standard') {
                    params.append('san_type', 'standard');
                } else if (activeFilter.value.startsWith('tld:')) {
                    params.append('san_tld', activeFilter.value.substring(4));
                } else if (activeFilter.value.startsWith('count:')) {
                    const [min, max] = activeFilter.value.substring(6).split('-').map(Number);
                    if (!isNaN(min)) params.append('san_count_min', min.toString());
                    if (!isNaN(max)) params.append('san_count_max', max.toString());
                } else if (activeFilter.value === 'multidomain') {
                    params.append('san_count_min', '5');
                    params.append('san_count_max', '1000');
                }
            }
            break;
        case 'all':
        default:
            break;
    }

    const qs = params.toString();
    return `${API_BASE_URL}/certificates/download/${qs ? `?${qs}` : ''}`;
}

// ── Certificate columns (used by DataTable pages) ──────────────────────

export const CERTIFICATE_COLUMNS: ExportColumn[] = [
    { header: 'Domain', key: 'Domain' },
    { header: 'Start Date', key: 'Start Date' },
    { header: 'End Date', key: 'End Date' },
    { header: 'SSL Grade', key: 'SSL Grade' },
    { header: 'Encryption', key: 'Encryption' },
    { header: 'Vulnerabilities', key: 'Vulnerabilities' },
    { header: 'Issuer', key: 'Issuer' },
    { header: 'Country', key: 'Country' },
    { header: 'Status', key: 'Status' },
];
