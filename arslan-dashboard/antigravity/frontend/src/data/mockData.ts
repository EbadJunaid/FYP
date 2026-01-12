// SSL Guardian - Mock Data for Dashboard

import {
    ScanEntry,
    DashboardMetrics,
    EncryptionStrength,
    FutureRisk,
    CALeaderboardEntry,
    GeographicEntry,
    ValidityTrendPoint,
} from '@/types/dashboard';

// Dashboard Metrics
export const mockDashboardMetrics: DashboardMetrics = {
    globalHealth: {
        score: 85,
        maxScore: 100,
        status: 'SECURE',
        lastUpdated: '2m ago',
    },
    activeCertificates: {
        count: 1248,
        total: 1300,
    },
    expiringSoon: {
        count: 12,
        daysThreshold: 30,
        actionNeeded: true,
    },
    criticalVulnerabilities: {
        count: 3,
        new: 1,
    },
};

// Encryption Strength Distribution
export const mockEncryptionStrength: EncryptionStrength[] = [
    {
        id: 'rsa-2048',
        name: 'RSA 2048',
        type: 'Standard',
        percentage: 65,
        color: '#3b82f6',
    },
    {
        id: 'rsa-4096',
        name: 'RSA 4096',
        type: 'Strong',
        percentage: 25,
        color: '#10b981',
    },
    {
        id: 'ecdsa',
        name: 'ECDSA',
        type: 'Modern',
        percentage: 8,
        color: '#06b6d4',
    },
    {
        id: 'weak-sha1',
        name: 'Weak / Deprecated (SHA-1)',
        type: 'Deprecated',
        percentage: 2,
        color: '#ef4444',
    },
];

// Future Risk Prediction
export const mockFutureRisk: FutureRisk = {
    confidenceLevel: 92,
    riskLevel: 'High',
    projectedThreats: [
        {
            id: 'weak-key',
            title: 'Weak Key Rotation',
            description: 'Predicted in 3 months',
            timeframe: '3 months',
            icon: 'key',
        },
        {
            id: 'sig-expiry',
            title: 'Signature Expiry',
            description: 'Weak In: SHA-1/SHA',
            timeframe: '6 months',
            icon: 'signature',
        },
    ],
};

// CA Leaderboard
export const mockCALeaderboard: CALeaderboardEntry[] = [
    { id: 'digicert', name: 'DigiCert Inc.', count: 86, maxCount: 100, percentage: 25.5, color: '#3b82f6' },
    { id: 'globalsign', name: 'GlobalSign', count: 94, maxCount: 100, percentage: 22.3, color: '#10b981' },
    { id: 'entrust', name: 'Entrust Datacard', count: 91, maxCount: 100, percentage: 18.7, color: '#8b5cf6' },
    { id: 'letsencrypt', name: "Let's Encrypt", count: 85, maxCount: 100, percentage: 15.8, color: '#06b6d4' },
    { id: 'godaddy', name: 'GoDaddy', count: 72, maxCount: 100, percentage: 10.2, color: '#f59e0b' },
];

// Geographic Distribution
export const mockGeographicDistribution: GeographicEntry[] = [
    { id: 'us', country: 'United States (53%)', percentage: 53, color: '#3b82f6' },
    { id: 'uk', country: 'United Kingdom (42%)', percentage: 42, color: '#8b5cf6' },
    { id: 'de', country: 'Germany (35%)', percentage: 35, color: '#10b981' },
    { id: 'jp', country: 'Japan (18%)', percentage: 18, color: '#f59e0b' },
    { id: 'others', country: 'Others (32%)', percentage: 32, color: '#64748b' },
];

// Validity Trend Data (18 months for better visualization)
export const mockValidityTrend: ValidityTrendPoint[] = [
    { month: 'Jan 23', expirations: 45 },
    { month: 'Feb', expirations: 52 },
    { month: 'Mar', expirations: 38 },
    { month: 'Apr', expirations: 65 },
    { month: 'May', expirations: 48 },
    { month: 'Jun', expirations: 72 },
    { month: 'Jul', expirations: 58 },
    { month: 'Aug', expirations: 42 },
    { month: 'Sep', expirations: 55 },
    { month: 'Oct', expirations: 68 },
    { month: 'Nov', expirations: 45 },
    { month: 'Dec', expirations: 82 },
    { month: 'Jan 24', expirations: 62 },
    { month: 'Feb', expirations: 55 },
    { month: 'Mar', expirations: 78 },
    { month: 'Apr', expirations: 48 },
    { month: 'May', expirations: 85 },
    { month: 'Jun', expirations: 92 },
];

// Recent Scans Table Data
export const mockRecentScans: ScanEntry[] = [
    {
        id: '1',
        domain: 'api.stripe.com',
        scanDate: 'Oct 24, 2023 10:42 AM',
        sslGrade: 'A+',
        vulnerabilities: '0 Found',
        issuer: 'DigiCert Inc.',
        status: 'VALID',
    },
    {
        id: '2',
        domain: 'staging.app.io',
        scanDate: 'Oct 24, 2023 09:15 AM',
        sslGrade: 'B',
        vulnerabilities: '2 Low',
        issuer: "Let's Encrypt",
        status: 'VALID',
    },
    {
        id: '3',
        domain: 'legacy-portal.net',
        scanDate: 'Oct 23, 2023 11:30 PM',
        sslGrade: 'F',
        vulnerabilities: '3 Critical',
        issuer: 'GoDaddy',
        status: 'EXPIRED',
    },
    {
        id: '4',
        domain: 'mail.corporate.com',
        scanDate: 'Oct 23, 2023 09:05 PM',
        sslGrade: 'A',
        vulnerabilities: '0 Found',
        issuer: 'GlobalSign',
        status: 'VALID',
    },
    {
        id: '5',
        domain: 'dev-test-01.cloud',
        scanDate: 'Oct 23, 2023 04:45 PM',
        sslGrade: 'C',
        vulnerabilities: '1 Medium',
        issuer: 'Internal CA',
        status: 'WEAK',
    },
    {
        id: '6',
        domain: 'shop.mysite.org',
        scanDate: 'Oct 23, 2023 02:12 PM',
        sslGrade: 'A+',
        vulnerabilities: '0 Found',
        issuer: 'Sectigo',
        status: 'VALID',
    },
    {
        id: '7',
        domain: 'support.helpdesk.io',
        scanDate: 'Oct 23, 2023 01:00 PM',
        sslGrade: 'A',
        vulnerabilities: '0 Found',
        issuer: 'DigiCert Inc.',
        status: 'VALID',
    },
    {
        id: '8',
        domain: 'blog.techstart.com',
        scanDate: 'Oct 23, 2023 11:15 AM',
        sslGrade: 'A+',
        vulnerabilities: '0 Found',
        issuer: "Let's Encrypt",
        status: 'VALID',
    },
    {
        id: '9',
        domain: 'crm.salesforce-connect.com',
        scanDate: 'Oct 23, 2023 09:30 AM',
        sslGrade: 'A+',
        vulnerabilities: '0 Found',
        issuer: 'DigiCert Inc.',
        status: 'VALID',
    },
    {
        id: '10',
        domain: 'vpn.access-point.net',
        scanDate: 'Oct 23, 2023 08:45 AM',
        sslGrade: 'B+',
        vulnerabilities: '1 Low',
        issuer: 'Entrust Datacard',
        status: 'VALID',
    },
];

// Generate random scan data for demo purposes
export function generateRandomScans(count: number = 10): ScanEntry[] {
    const domains = [
        'api.example.com',
        'secure.banking.io',
        'shop.store.net',
        'app.saas.io',
        'portal.enterprise.com',
        'cdn.media.net',
        'auth.identity.io',
        'dashboard.admin.com',
        'staging.dev.io',
        'production.live.net',
    ];

    const issuers = ['DigiCert Inc.', 'GlobalSign', "Let's Encrypt", 'Sectigo', 'Entrust Datacard', 'GoDaddy'];
    const grades: Array<'A+' | 'A' | 'A-' | 'B' | 'B+' | 'C' | 'F'> = ['A+', 'A', 'A-', 'B', 'B+', 'C', 'F'];
    const statuses: Array<'VALID' | 'EXPIRED' | 'WEAK' | 'EXPIRING_SOON'> = ['VALID', 'VALID', 'VALID', 'EXPIRED', 'WEAK', 'EXPIRING_SOON'];

    return Array.from({ length: count }, (_, i) => ({
        id: `scan-${i + 1}`,
        domain: domains[Math.floor(Math.random() * domains.length)],
        scanDate: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000).toLocaleString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true,
        }),
        sslGrade: grades[Math.floor(Math.random() * grades.length)],
        vulnerabilities: ['0 Found', '1 Low', '2 Medium', '3 Critical'][Math.floor(Math.random() * 4)],
        issuer: issuers[Math.floor(Math.random() * issuers.length)],
        status: statuses[Math.floor(Math.random() * statuses.length)],
    }));
}
