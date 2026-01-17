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
    // Enhanced fields
    commonName?: string;
    subjectDn?: string;
    selfSigned?: boolean;
    serialNumber?: string;
    fingerprintSha256?: string;
    fingerprintSha1?: string;
    fingerprintMd5?: string;
    validityLength?: number; // in seconds
    isCa?: boolean;
    keyUsage?: {
        digitalSignature?: boolean;
        keyEncipherment?: boolean;
        dataEncipherment?: boolean;
        keyCertSign?: boolean;
        crlSign?: boolean;
    };
    extendedKeyUsage?: {
        serverAuth?: boolean;
        clientAuth?: boolean;
        codeSigning?: boolean;
        emailProtection?: boolean;
    };
    crlDistributionPoints?: string[];
    authorityInfoAccess?: string[];
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

// CA Analytics Types
export interface CAStats {
    total_cas: number;
    total_certs: number;
    top_ca: {
        name: string;
        count: number;
        percentage: number;
    };
    self_signed_count: number;
    unique_countries: number;
}

export interface CADistributionEntry {
    name: string;
    count: number;
    percentage: number;
}

export interface ValidationDistributionEntry {
    level: string;
    count: number;
    percentage: number;
}

export interface IssuerValidationEntry {
    issuer: string;
    validationLevel: string;
    count: number;
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
        expiringDays?: number;
        validityBucket?: string;
        issuedMonth?: number;
        issuedYear?: number;
        // Signature/Hash page filters
        signature_algorithm?: string;
        weak_hash?: string;
        self_signed?: string;
        key_size?: number;
        hash_type?: string;
        encryption_type?: string;
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
        if (params?.encryption_type) queryParams.append('encryption_type', params.encryption_type);
        if (params?.hasVulnerabilities) queryParams.append('has_vulnerabilities', 'true');
        if (params?.expiringMonth) queryParams.append('expiring_month', params.expiringMonth.toString());
        if (params?.expiringYear) queryParams.append('expiring_year', params.expiringYear.toString());
        if (params?.expiringDays) queryParams.append('expiring_days', params.expiringDays.toString());
        if (params?.validityBucket) queryParams.append('validity_bucket', params.validityBucket);
        if (params?.issuedMonth) queryParams.append('issued_month', params.issuedMonth.toString());
        if (params?.issuedYear) queryParams.append('issued_year', params.issuedYear.toString());
        // Signature/Hash filters
        if (params?.signature_algorithm) queryParams.append('signature_algorithm', params.signature_algorithm);
        if (params?.weak_hash) queryParams.append('weak_hash', params.weak_hash);
        if (params?.self_signed) queryParams.append('self_signed', params.self_signed);
        if (params?.key_size) queryParams.append('key_size', params.key_size.toString());
        if (params?.hash_type) queryParams.append('hash_type', params.hash_type);
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

    async getValidityTrends(months: number = 12, granularity: 'monthly' | 'weekly' = 'monthly'): Promise<ValidityTrend[]> {
        return this.fetch<ValidityTrend[]>(`/validity-trends/?months_before=${Math.floor(months / 2)}&months_after=${Math.floor(months / 2)}&granularity=${granularity}`);
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

    // CA Analytics - Stats for metric cards
    async getCAStats(): Promise<CAStats> {
        return this.fetch<CAStats>('/ca-stats/');
    }

    // CA Analytics - Validation level distribution (DV, OV, EV)
    async getValidationDistribution(): Promise<ValidationDistributionEntry[]> {
        return this.fetch<ValidationDistributionEntry[]>('/validation-distribution/');
    }

    // CA Analytics - Issuer x Validation level matrix for heatmap
    async getIssuerValidationMatrix(limit: number = 10): Promise<IssuerValidationEntry[]> {
        return this.fetch<IssuerValidationEntry[]>(`/issuer-validation-matrix/?limit=${limit}`);
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

    // Validity Analysis APIs
    async getValidityStats(): Promise<ValidityStats> {
        return this.fetch<ValidityStats>('/validity-stats/');
    }

    async getValidityDistribution(): Promise<ValidityDistributionEntry[]> {
        return this.fetch<ValidityDistributionEntry[]>('/validity-distribution/');
    }

    async getIssuanceTimeline(): Promise<IssuanceTimelineEntry[]> {
        return this.fetch<IssuanceTimelineEntry[]>('/issuance-timeline/');
    }

    // Signature and Hashes APIs
    async getSignatureStats(): Promise<SignatureStats> {
        return this.fetch<SignatureStats>('/signature-stats/');
    }

    async getHashTrends(months: number = 36, granularity: 'quarterly' | 'yearly' = 'quarterly'): Promise<HashTrendEntry[]> {
        return this.fetch<HashTrendEntry[]>(`/hash-trends/?months=${months}&granularity=${granularity}`);
    }

    async getIssuerAlgorithmMatrix(limit: number = 10): Promise<IssuerAlgorithmEntry[]> {
        return this.fetch<IssuerAlgorithmEntry[]>(`/issuer-algorithm-matrix/?limit=${limit}`);
    }

    // Export certificates as CSV with filters
    async exportCertificates(params?: {
        signature_algorithm?: string;
        weak_hash?: string;
        self_signed?: string;
        key_size?: number;
        hash_type?: string;
        encryption_type?: string;
    }): Promise<void> {
        const queryParams = new URLSearchParams();
        if (params?.signature_algorithm) queryParams.append('signature_algorithm', params.signature_algorithm);
        if (params?.weak_hash) queryParams.append('weak_hash', params.weak_hash);
        if (params?.self_signed) queryParams.append('self_signed', params.self_signed);
        if (params?.key_size) queryParams.append('key_size', params.key_size.toString());
        if (params?.hash_type) queryParams.append('hash_type', params.hash_type);
        if (params?.encryption_type) queryParams.append('encryption_type', params.encryption_type);

        const query = queryParams.toString();
        const url = `${this.baseUrl}/certificates/export/${query ? `?${query}` : ''}`;

        // Trigger download
        const link = document.createElement('a');
        link.href = url;
        link.download = 'certificates.csv';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
}

// Validity Analysis types
export interface ValidityStats {
    averageValidityDays: number;
    shortestValidityDays: number;
    longestValidityDays: number;
    expiring30Days: number;
    expiring60Days: number;
    expiring90Days: number;
    complianceRate: number;
    totalCertificates: number;
}

export interface ValidityDistributionEntry {
    range: string;
    count: number;
    percentage: number;
    color: string;
}

export interface IssuanceTimelineEntry {
    month: string;
    year: number;
    monthNum: number;
    issued: number;
    expiring: number;
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

// Signature and Hashes types
export interface SignatureAlgorithmEntry {
    name: string;
    count: number;
    percentage: number;
    color: string;
}

export interface HashDistributionEntry {
    name: string;
    count: number;
    percentage: number;
    color: string;
    security: 'secure' | 'deprecated' | 'critical' | 'unknown';
}

export interface KeySizeDistributionEntry {
    name: string;
    algorithm: string;
    size: number;
    count: number;
    percentage: number;
    color: string;
}

export interface MaxEncryptionType {
    name: string;
    count: number;
    percentage: number;
}

export interface SignatureStats {
    algorithmDistribution: SignatureAlgorithmEntry[];
    hashDistribution: HashDistributionEntry[];
    keySizeDistribution: KeySizeDistributionEntry[];
    weakHashCount: number;
    hashComplianceRate: number;
    strengthScore: number;
    selfSignedCount: number;
    totalCertificates: number;
    maxEncryptionType: MaxEncryptionType | null;
}

export interface HashTrendEntry {
    period: string;
    year: number;
    quarter: number | null;
    total: number;
    'SHA-256': number;
    'SHA-384': number;
    'SHA-512': number;
    'SHA-1': number;
    'MD5': number;
    'Other': number;
}

export interface IssuerAlgorithmEntry {
    issuer: string;
    algorithm: string;
    algorithmType: string;
    keySize: number;
    count: number;
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export default
export default apiClient;
