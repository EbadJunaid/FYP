// Controllers for dashboard pages - Real API integration
// Replaces mock data with actual API calls

import { apiClient, Certificate, DashboardMetrics, EncryptionStrength, ValidityTrend, CALeaderboardEntry, GeographicEntry, FutureRisk, UniqueFilters } from '@/services/apiClient';
import { ScanEntry, SSLGrade, CertificateStatus } from '@/types/dashboard';

// Convert API Certificate to ScanEntry for table display
function certificateToScanEntry(cert: Certificate): ScanEntry {
    // Format date to YYYY-MM-DD (date only, no time)
    const formatDateOnly = (dateStr: string): string => {
        try {
            const date = new Date(dateStr);
            return date.toISOString().split('T')[0];
        } catch {
            return dateStr;
        }
    };

    return {
        id: cert.id,
        domain: cert.domain,
        scanDate: formatDateOnly(cert.scanDate),
        endDate: formatDateOnly(cert.validTo),
        sslGrade: cert.grade as SSLGrade,
        vulnerabilities: cert.vulnerabilities,
        issuer: cert.issuer,
        status: cert.status as CertificateStatus,
        country: cert.country,
        encryptionType: cert.encryptionType,
    };
}

// Fetch dashboard metrics from API
export async function fetchDashboardMetrics(): Promise<DashboardMetrics> {
    try {
        return await apiClient.getGlobalHealth();
    } catch (error) {
        console.error('Error fetching dashboard metrics:', error);
        // Return default values on error
        return {
            globalHealth: { score: 0, maxScore: 100, status: 'CRITICAL', lastUpdated: 'N/A' },
            activeCertificates: { count: 0, total: 0 },
            expiringSoon: { count: 0, daysThreshold: 30, actionNeeded: false },
            criticalVulnerabilities: { count: 0, new: 0 },
        };
    }
}

// Global filter params type
export interface GlobalFilterParams {
    startDate?: string;
    endDate?: string;
    countries?: string[];
    issuers?: string[];
    statuses?: string[];
    validationLevels?: string[];
}

// Fetch certificates with filters and pagination
export async function fetchCertificates(params?: {
    page?: number;
    pageSize?: number;
    status?: string;
    country?: string;
    issuer?: string;
    search?: string;
    encryptionType?: string;
    hasVulnerabilities?: boolean;
    expiringMonth?: number;
    expiringYear?: number;
    expiringDays?: number;
    validityBucket?: string;
    issuedMonth?: number;
    issuedYear?: number;
    issuedWithinDays?: number;  // Filter for certificates issued within N days
    expiringStart?: string;
    expiringEnd?: string;
    // Signature/Hash page filters
    signature_algorithm?: string;
    weak_hash?: string;
    self_signed?: string;
    key_size?: number;
    hash_type?: string;
    encryption_type?: string;  // Alternative naming
    // SAN Analytics filters
    has_wildcard?: string;
    min_sans?: number;
    max_sans?: number;
    san_tld?: string;
    san_type?: string;
    san_count_min?: number;
    san_count_max?: number;
} & GlobalFilterParams): Promise<{ certificates: ScanEntry[]; pagination: { page: number; total: number; totalPages: number } }> {
    try {
        const result = await apiClient.getCertificates(params);
        return {
            certificates: result.certificates.map(certificateToScanEntry),
            pagination: {
                page: result.pagination.page,
                total: result.pagination.total,
                totalPages: result.pagination.totalPages,
            },
        };
    } catch (error) {
        console.error('Error fetching certificates:', error);
        return { certificates: [], pagination: { page: 1, total: 0, totalPages: 0 } };
    }
}

// Fetch single certificate by ID
export async function fetchCertificateById(id: string): Promise<Certificate | null> {
    try {
        return await apiClient.getCertificateById(id);
    } catch (error) {
        console.error('Error fetching certificate:', error);
        return null;
    }
}

// Fetch unique filter options
export async function fetchUniqueFilters(): Promise<UniqueFilters> {
    try {
        return await apiClient.getUniqueFilters();
    } catch (error) {
        console.error('Error fetching filters:', error);
        return { issuers: [], countries: [], statuses: [], grades: [], validationLevels: [] };
    }
}

// Fetch encryption strength distribution
export async function fetchEncryptionStrength(params?: GlobalFilterParams): Promise<EncryptionStrength[]> {
    try {
        return await apiClient.getEncryptionStrength(params);
    } catch (error) {
        console.error('Error fetching encryption strength:', error);
        return [];
    }
}

// Fetch validity trends
export async function fetchValidityTrends(months: number = 12): Promise<ValidityTrend[]> {
    try {
        return await apiClient.getValidityTrends(months);
    } catch (error) {
        console.error('Error fetching validity trends:', error);
        return [];
    }
}

// Fetch CA leaderboard
export async function fetchCALeaderboard(limit: number = 10, params?: GlobalFilterParams): Promise<CALeaderboardEntry[]> {
    try {
        return await apiClient.getCAAnalytics(limit, params);
    } catch (error) {
        console.error('Error fetching CA leaderboard:', error);
        return [];
    }
}

// Fetch geographic distribution
export async function fetchGeographicDistribution(limit: number = 10, params?: GlobalFilterParams): Promise<GeographicEntry[]> {
    try {
        return await apiClient.getGeographicDistribution(limit, params);
    } catch (error) {
        console.error('Error fetching geographic distribution:', error);
        return [];
    }
}

// Fetch future risk prediction
export async function fetchFutureRisk(): Promise<FutureRisk> {
    try {
        return await apiClient.getFutureRisk();
    } catch (error) {
        console.error('Error fetching future risk:', error);
        return {
            confidenceLevel: 0,
            riskLevel: 'Low',
            projectedThreats: [],
        };
    }
}

// Fetch vulnerabilities
export async function fetchVulnerabilities(page: number = 1, pageSize: number = 10) {
    try {
        return await apiClient.getVulnerabilities(page, pageSize);
    } catch (error) {
        console.error('Error fetching vulnerabilities:', error);
        return { certificates: [], summary: { critical: 0, warning: 0, total: 0 }, pagination: { page: 1, pageSize: 10, total: 0, totalPages: 0 } };
    }
}

// Legacy functions for backwards compatibility with existing pages
// These will use real API data

export function generatePageMetrics(pageType: string) {
    // Return empty metrics - will be fetched from API
    return {
        total: 0,
        active: 0,
        expired: 0,
        expiringSoon: 0,
        trend: '0',
    };
}

export function generateChartData(pageType: string, count: number = 6) {
    // Return empty data - will be fetched from API
    return [];
}

export function generateTableData(pageType: string, count: number = 10): ScanEntry[] {
    // Return empty data - will be fetched from API
    return [];
}

export function generateGeographicData(count: number = 10) {
    return [];
}

export function generateCAData(count: number = 8) {
    return [];
}

export function generateSANData(count: number = 10) {
    return [];
}

// Async fetch function for page data (now uses real API)
export async function fetchPageData(pageType: string): Promise<{
    metrics: ReturnType<typeof generatePageMetrics>;
    chartData: ReturnType<typeof generateChartData>;
    tableData: ScanEntry[];
}> {
    try {
        // Fetch real data from API
        const [metricsData, certificatesData] = await Promise.all([
            fetchDashboardMetrics(),
            fetchCertificates({ page: 1, pageSize: 25 }),
        ]);

        return {
            metrics: {
                total: certificatesData.pagination.total,
                active: metricsData.activeCertificates.count,
                expired: metricsData.expiredCertificates?.count || 0,
                expiringSoon: metricsData.expiringSoon.count,
                trend: '0',
            },
            chartData: [],
            tableData: certificatesData.certificates,
        };
    } catch (error) {
        console.error('Error fetching page data:', error);
        return {
            metrics: generatePageMetrics(pageType),
            chartData: [],
            tableData: [],
        };
    }
}
