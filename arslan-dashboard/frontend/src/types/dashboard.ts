// SSL Guardian Dashboard Types

// SSL Certificate Grade
export type SSLGrade = 'A+' | 'A' | 'A-' | 'B' | 'B+' | 'C' | 'D' | 'F';

// Certificate Status
export type CertificateStatus = 'VALID' | 'EXPIRED' | 'WEAK' | 'EXPIRING_SOON';

// Vulnerability Severity
export type VulnerabilitySeverity = 'Critical' | 'High' | 'Medium' | 'Low' | 'None';

// Certificate Issuer
export interface CertificateIssuer {
    id: string;
    name: string;
    percentage?: number;
}

// Recent Scan Entry
export interface ScanEntry {
    id: string;
    domain: string;
    scanDate: string;
    endDate?: string;
    sslGrade: SSLGrade;
    vulnerabilities: string;
    issuer: string;
    status: CertificateStatus;
    country?: string;
    encryptionType?: string;
}

// Dashboard Metrics
export interface DashboardMetrics {
    globalHealth: {
        score: number;
        maxScore: number;
        status: 'SECURE' | 'AT_RISK' | 'CRITICAL';
        lastUpdated: string;
    };
    activeCertificates: {
        count: number;
        total: number;
    };
    expiringSoon: {
        count: number;
        daysThreshold: number;
        actionNeeded: boolean;
    };
    criticalVulnerabilities: {
        count: number;
        new: number;
    };
    expiredCertificates?: {
        count: number;
    };
}

// Encryption Strength Data
export interface EncryptionStrength {
    id: string;
    name: string;
    type: 'Strong' | 'Standard' | 'Modern' | 'Weak' | 'Deprecated';
    percentage: number;
    color: string;
}

// Future Risk Prediction
export interface FutureRisk {
    confidenceLevel: number;
    riskLevel: 'High' | 'Medium' | 'Low';
    projectedThreats: ProjectedThreat[];
}

export interface ProjectedThreat {
    id: string;
    title: string;
    description: string;
    timeframe: string;
    icon: 'key' | 'signature' | 'warning' | 'certificate';
}

// CA Leaderboard Entry
export interface CALeaderboardEntry {
    id: string;
    name: string;
    count: number;
    maxCount: number;
    percentage: number;
    color: string;
}

// Geographic Distribution
export interface GeographicEntry {
    id: string;
    country: string;
    percentage: number;
    color: string;
}

// Validity Trend Data Point
export interface ValidityTrendPoint {
    month: string;
    expirations: number;
}

// Filter Options
export interface FilterOptions {
    dateRange: {
        start: Date | null;
        end: Date | null;
    };
    status: CertificateStatus[];
    vulnerabilityType: VulnerabilitySeverity[];
    issuer: string[];
    sslGrade: SSLGrade[];
}

// Search State
export interface SearchState {
    query: string;
    isActive: boolean;
    results: ScanEntry[];
}

// Dashboard State
export interface DashboardState {
    metrics: DashboardMetrics | null;
    encryptionStrength: EncryptionStrength[];
    futureRisk: FutureRisk | null;
    caLeaderboard: CALeaderboardEntry[];
    geographicDistribution: GeographicEntry[];
    validityTrend: ValidityTrendPoint[];
    recentScans: ScanEntry[];
    filters: FilterOptions;
    search: SearchState;
    isLoading: boolean;
    error: string | null;
}

// Theme Type
export type Theme = 'light' | 'dark';

// Navigation Item
export interface NavItem {
    id: string;
    label: string;
    icon: string;
    href: string;
    isActive?: boolean;
    badge?: number;
}

// Card Props
export interface CardProps {
    title?: string;
    subtitle?: string;
    headerAction?: React.ReactNode;
    children: React.ReactNode;
    className?: string;
    onClick?: () => void;
    isClickable?: boolean;
}

// Metric Card Props
export interface MetricCardProps {
    icon: React.ReactNode;
    iconBgColor?: string;
    value: string | number;
    label: string;
    trend?: number;
    trendLabel?: string;
    badge?: {
        text: string;
        variant: 'success' | 'warning' | 'error' | 'info';
    };
    onClick?: () => void;
}
