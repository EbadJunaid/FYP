// Frontend API Client for SSL Guardian Dashboard
// Handles all API calls to Django backend

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

// Types for API responses
export interface ApiResponse<T> {
    data: T | null;
    error: string | null;
    loading: boolean;
}

export interface PaginationInfo {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
}

export interface CertificateListResponse {
    certificates: Certificate[];
    pagination: PaginationInfo;
}

export interface Certificate {
    id: string;
    domain: string;
    issuer: string;
    issuerDn: string;
    validFrom: string;
    validTo: string;
    status: 'VALID' | 'EXPIRED' | 'EXPIRING_SOON' | 'WEAK';
    grade: string;
    encryptionType: string;
    keyLength: number;
    signatureAlgorithm: string;
    vulnerabilities: string;
    vulnerabilityCount: { errors: number; warnings: number };
    san: string[];
    country: string;
    scanDate: string;
    validationLevel: string;
    zlintDetails?: Record<string, { result: string; details?: string }>;
}

export interface DashboardMetrics {
    globalHealth: {
        score: number;
        maxScore: number;
        status: 'SECURE' | 'AT_RISK' | 'CRITICAL';
        lastUpdated: string;
    };
    activeCertificates: { count: number; total: number };
    expiringSoon: { count: number; daysThreshold: number; actionNeeded: boolean };
    criticalVulnerabilities: { count: number; new: number };
    expiredCertificates?: { count: number };
}

export interface UniqueFilters {
    issuers: string[];
    countries: string[];
    statuses: string[];
    grades: string[];
    validationLevels: string[];
}

export interface EncryptionStrength {
    id: string;
    name: string;
    type: string;
    count: number;
    percentage: number;
    color: string;
}

export interface ValidityTrend {
    month: string;
    expirations: number;
}

export interface CALeaderboardEntry {
    id: string;
    name: string;
    count: number;
    maxCount: number;
    percentage: number;
    color: string;
}

export interface GeographicEntry {
    id: string;
    country: string;
    count: number;
    percentage: number;
    color: string;
}

export interface FutureRisk {
    confidenceLevel: number;
    riskLevel: 'High' | 'Medium' | 'Low';
    projectedThreats: Array<{
        id: string;
        title: string;
        description: string;
        timeframe: string;
        icon: string;
    }>;
}

// API Client class
class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = API_BASE_URL) {
        this.baseUrl = baseUrl;
    }

    private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
        const url = `${this.baseUrl}${endpoint}`;

        try {
            const response = await fetch(url, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options?.headers,
                },
                ...options,
            });

            if (!response.ok) {
                throw new Error(`API Error: ${response.status} ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API call failed for ${url}:`, error);
            throw error;
        }
    }

    // Dashboard Metrics
    async getGlobalHealth(): Promise<DashboardMetrics> {
        return this.fetch<DashboardMetrics>('/dashboard/global-health/');
    }

    // Certificates
    async getCertificates(params?: {
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
        // Global filter params
        startDate?: string;
        endDate?: string;
        countries?: string[];
        issuers?: string[];
        statuses?: string[];
        validationLevels?: string[];
    }): Promise<CertificateListResponse> {
        const queryParams = new URLSearchParams();
        if (params?.page) queryParams.append('page', params.page.toString());
        if (params?.pageSize) queryParams.append('page_size', params.pageSize.toString());
        if (params?.status) queryParams.append('status', params.status);
        if (params?.country) queryParams.append('country', params.country);
        if (params?.issuer) queryParams.append('issuer', params.issuer);
        if (params?.search) queryParams.append('search', params.search);
        if (params?.encryptionType) queryParams.append('encryption_type', params.encryptionType);
        if (params?.hasVulnerabilities) queryParams.append('has_vulnerabilities', 'true');
        if (params?.expiringMonth) queryParams.append('expiring_month', params.expiringMonth.toString());
        if (params?.expiringYear) queryParams.append('expiring_year', params.expiringYear.toString());
        // Global filter params
        if (params?.startDate) queryParams.append('start_date', params.startDate);
        if (params?.endDate) queryParams.append('end_date', params.endDate);
        if (params?.countries?.length) queryParams.append('countries', params.countries.join(','));
        if (params?.issuers?.length) queryParams.append('issuers', params.issuers.join(','));
        if (params?.statuses?.length) queryParams.append('statuses', params.statuses.join(','));
        if (params?.validationLevels?.length) queryParams.append('validation_levels', params.validationLevels.join(','));

        const query = queryParams.toString();
        return this.fetch<CertificateListResponse>(`/certificates/${query ? `?${query}` : ''}`);
    }

    async getCertificateById(id: string): Promise<Certificate> {
        return this.fetch<Certificate>(`/certificates/${id}/`);
    }

    // Filters
    async getUniqueFilters(): Promise<UniqueFilters> {
        return this.fetch<UniqueFilters>('/unique-filters/');
    }

    // Global filter params type
    // Analytics - with optional global filter params
    async getEncryptionStrength(params?: {
        startDate?: string;
        endDate?: string;
        countries?: string[];
        issuers?: string[];
        statuses?: string[];
        validationLevels?: string[];
    }): Promise<EncryptionStrength[]> {
        const queryParams = new URLSearchParams();
        if (params?.startDate) queryParams.append('start_date', params.startDate);
        if (params?.endDate) queryParams.append('end_date', params.endDate);
        if (params?.countries?.length) queryParams.append('countries', params.countries.join(','));
        if (params?.issuers?.length) queryParams.append('issuers', params.issuers.join(','));
        if (params?.statuses?.length) queryParams.append('statuses', params.statuses.join(','));
        if (params?.validationLevels?.length) queryParams.append('validation_levels', params.validationLevels.join(','));
        const query = queryParams.toString();
        return this.fetch<EncryptionStrength[]>(`/encryption-strength/${query ? `?${query}` : ''}`);
    }

    async getValidityTrends(months: number = 12): Promise<ValidityTrend[]> {
        return this.fetch<ValidityTrend[]>(`/validity-trends/?months=${months}`);
    }

    async getCAAnalytics(limit: number = 10, params?: {
        startDate?: string;
        endDate?: string;
        countries?: string[];
        issuers?: string[];
        statuses?: string[];
        validationLevels?: string[];
    }): Promise<CALeaderboardEntry[]> {
        const queryParams = new URLSearchParams();
        queryParams.append('limit', limit.toString());
        if (params?.startDate) queryParams.append('start_date', params.startDate);
        if (params?.endDate) queryParams.append('end_date', params.endDate);
        if (params?.countries?.length) queryParams.append('countries', params.countries.join(','));
        if (params?.issuers?.length) queryParams.append('issuers', params.issuers.join(','));
        if (params?.statuses?.length) queryParams.append('statuses', params.statuses.join(','));
        if (params?.validationLevels?.length) queryParams.append('validation_levels', params.validationLevels.join(','));
        return this.fetch<CALeaderboardEntry[]>(`/ca-analytics/?${queryParams.toString()}`);
    }

    async getGeographicDistribution(limit: number = 10, params?: {
        startDate?: string;
        endDate?: string;
        countries?: string[];
        issuers?: string[];
        statuses?: string[];
        validationLevels?: string[];
    }): Promise<GeographicEntry[]> {
        const queryParams = new URLSearchParams();
        queryParams.append('limit', limit.toString());
        if (params?.startDate) queryParams.append('start_date', params.startDate);
        if (params?.endDate) queryParams.append('end_date', params.endDate);
        if (params?.countries?.length) queryParams.append('countries', params.countries.join(','));
        if (params?.issuers?.length) queryParams.append('issuers', params.issuers.join(','));
        if (params?.statuses?.length) queryParams.append('statuses', params.statuses.join(','));
        if (params?.validationLevels?.length) queryParams.append('validation_levels', params.validationLevels.join(','));
        return this.fetch<GeographicEntry[]>(`/geographic-distribution/?${queryParams.toString()}`);
    }

    async getFutureRisk(): Promise<FutureRisk> {
        return this.fetch<FutureRisk>('/future-risk/');
    }

    async getVulnerabilities(page: number = 1, pageSize: number = 10): Promise<{
        certificates: Certificate[];
        summary: { critical: number; warning: number; total: number };
        pagination: PaginationInfo;
    }> {
        return this.fetch(`/vulnerabilities/?page=${page}&page_size=${pageSize}`);
    }

    async getNotifications(): Promise<NotificationResponse> {
        return this.fetch<NotificationResponse>('/notifications/');
    }
}

// Notification types
export interface NotificationItem {
    id: string;
    type: 'error' | 'warning' | 'success' | 'info';
    category: string;
    title: string;
    description: string;
    count: number;
    filterParams: Record<string, unknown>;
    timestamp: string;
    read: boolean;
}

export interface NotificationResponse {
    notifications: NotificationItem[];
    unreadCount: number;
    totalCount: number;
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export default
export default apiClient;
