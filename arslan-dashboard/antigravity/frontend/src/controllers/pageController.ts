// Controllers for dashboard pages - Mock data generation and logic

import { ScanEntry, SSLGrade, CertificateStatus } from '@/types/dashboard';

// Generate random metrics for a page
export function generatePageMetrics(pageType: string) {
    const baseMetrics = {
        total: Math.floor(Math.random() * 10000) + 1000,
        active: Math.floor(Math.random() * 8000) + 500,
        expired: Math.floor(Math.random() * 500) + 50,
        expiringSoon: Math.floor(Math.random() * 200) + 20,
        trend: (Math.random() * 10 - 5).toFixed(1),
    };

    switch (pageType) {
        case 'active-vs-expired':
            return {
                ...baseMetrics,
                activePercentage: ((baseMetrics.active / baseMetrics.total) * 100).toFixed(1),
                expiredPercentage: ((baseMetrics.expired / baseMetrics.total) * 100).toFixed(1),
            };
        case 'validity-analytics':
            return {
                ...baseMetrics,
                avgValidityDays: Math.floor(Math.random() * 365) + 30,
                minValidityDays: Math.floor(Math.random() * 30) + 1,
                maxValidityDays: Math.floor(Math.random() * 365) + 365,
            };
        case 'ca-analytics':
            return {
                ...baseMetrics,
                uniqueCAs: Math.floor(Math.random() * 50) + 10,
                topCA: ['DigiCert', 'Let\'s Encrypt', 'GlobalSign', 'Sectigo'][Math.floor(Math.random() * 4)],
            };
        default:
            return baseMetrics;
    }
}

// Generate chart data for different page types
export function generateChartData(pageType: string, count: number = 6) {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

    switch (pageType) {
        case 'trends':
            return months.slice(0, count).map(month => ({
                month,
                certificates: Math.floor(Math.random() * 500) + 100,
                expired: Math.floor(Math.random() * 50) + 5,
            }));
        case 'type-distribution':
            return [
                { name: 'DV (Domain Validated)', value: Math.floor(Math.random() * 60) + 30, color: '#3b82f6' },
                { name: 'OV (Organization Validated)', value: Math.floor(Math.random() * 30) + 10, color: '#10b981' },
                { name: 'EV (Extended Validation)', value: Math.floor(Math.random() * 15) + 5, color: '#8b5cf6' },
            ];
        case 'signature-hash':
            return [
                { name: 'SHA-256', percentage: Math.floor(Math.random() * 30) + 60, color: '#10b981' },
                { name: 'SHA-384', percentage: Math.floor(Math.random() * 20) + 10, color: '#3b82f6' },
                { name: 'SHA-512', percentage: Math.floor(Math.random() * 10) + 5, color: '#8b5cf6' },
                { name: 'SHA-1 (Deprecated)', percentage: Math.floor(Math.random() * 5) + 1, color: '#ef4444' },
            ];
        default:
            return months.slice(0, count).map(month => ({
                month,
                value: Math.floor(Math.random() * 1000) + 100,
            }));
    }
}

// Generate table data for pages
export function generateTableData(pageType: string, count: number = 10): ScanEntry[] {
    const domains = [
        'api.example.com', 'secure.banking.io', 'shop.store.net', 'app.saas.io',
        'portal.enterprise.com', 'cdn.media.net', 'auth.identity.io', 'dashboard.admin.com',
        'staging.dev.io', 'production.live.net', 'mail.corporate.com', 'blog.tech.org',
        'support.help.io', 'docs.api.dev', 'status.monitor.com',
    ];

    const issuers = ['DigiCert Inc.', 'GlobalSign', "Let's Encrypt", 'Sectigo', 'Entrust Datacard', 'GoDaddy', 'Comodo'];
    const grades: SSLGrade[] = ['A+', 'A', 'A-', 'B+', 'B', 'C', 'F'];
    const statuses: CertificateStatus[] = ['VALID', 'VALID', 'VALID', 'EXPIRED', 'WEAK', 'EXPIRING_SOON'];
    const vulns = ['0 Found', '1 Low', '2 Medium', '1 High', '3 Critical'];

    return Array.from({ length: count }, (_, i) => ({
        id: `${pageType}-${i + 1}`,
        domain: domains[Math.floor(Math.random() * domains.length)],
        scanDate: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        }),
        sslGrade: grades[Math.floor(Math.random() * grades.length)],
        vulnerabilities: vulns[Math.floor(Math.random() * vulns.length)],
        issuer: issuers[Math.floor(Math.random() * issuers.length)],
        status: statuses[Math.floor(Math.random() * statuses.length)],
    }));
}

// Generate geographic data
export function generateGeographicData(count: number = 10) {
    const countries = [
        'United States', 'United Kingdom', 'Germany', 'France', 'Japan',
        'Canada', 'Australia', 'Netherlands', 'Singapore', 'India',
        'Brazil', 'South Korea', 'Ireland', 'Sweden', 'Switzerland',
    ];

    return countries.slice(0, count).map((country, i) => ({
        id: `country-${i}`,
        country,
        count: Math.floor(Math.random() * 500) + 50,
        percentage: Math.floor(Math.random() * 30) + (count - i) * 5,
    })).sort((a, b) => b.percentage - a.percentage);
}

// Generate CA leaderboard data
export function generateCAData(count: number = 8) {
    const cas = [
        'DigiCert Inc.', 'Let\'s Encrypt', 'GlobalSign', 'Sectigo (Comodo)',
        'Entrust Datacard', 'GoDaddy', 'Amazon Trust Services', 'Google Trust Services',
    ];

    return cas.slice(0, count).map((name, i) => ({
        id: `ca-${i}`,
        name,
        count: Math.floor(Math.random() * 30) + (count - i) * 10,
        certificates: Math.floor(Math.random() * 500) + 100,
    })).sort((a, b) => b.count - a.count);
}

// Generate SAN analytics data
export function generateSANData(count: number = 10) {
    return Array.from({ length: count }, (_, i) => ({
        id: `san-${i}`,
        domain: `*.example${i + 1}.com`,
        sanCount: Math.floor(Math.random() * 20) + 1,
        type: ['Wildcard', 'Multi-domain', 'Single'][Math.floor(Math.random() * 3)],
        coverage: Math.floor(Math.random() * 50) + 10,
    }));
}

// Async mock fetch function - simulates API call
export async function fetchPageData(pageType: string): Promise<{
    metrics: ReturnType<typeof generatePageMetrics>;
    chartData: ReturnType<typeof generateChartData>;
    tableData: ScanEntry[];
}> {
    // Simulate network delay
    await new Promise(resolve => setTimeout(resolve, 300));

    return {
        metrics: generatePageMetrics(pageType),
        chartData: generateChartData(pageType),
        tableData: generateTableData(pageType, 25),
    };
}
