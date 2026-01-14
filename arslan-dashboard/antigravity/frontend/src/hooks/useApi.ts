/**
 * Custom SWR hooks for API data fetching with caching
 * Uses stale-while-revalidate pattern for instant UI and background refresh
 */

import useSWR, { SWRConfiguration } from 'swr';
import {
    DashboardMetrics,
    EncryptionStrength,
    ValidityTrendPoint,
    CALeaderboardEntry,
    GeographicEntry,
    FutureRisk,
    ScanEntry,
} from '@/types/dashboard';
import { NotificationResponse, PaginationInfo, Certificate } from '@/services/apiClient';

// TTL configurations (in milliseconds)
const TTL = {
    METRICS: 5 * 60 * 1000,         // 5 minutes
    CERTIFICATES: 3 * 60 * 1000,    // 3 minutes
    ANALYTICS: 15 * 60 * 1000,      // 15 minutes
    NOTIFICATIONS: 2 * 60 * 1000,   // 2 minutes
    GEOGRAPHIC: 30 * 60 * 1000,     // 30 minutes
};

// Response type for certificates endpoint
interface CertificatesResponse {
    certificates: Certificate[];
    pagination: PaginationInfo;
}

/**
 * Hook: Fetch dashboard metrics (global health, active certs, etc.)
 * TTL: 5 minutes
 */
export function useDashboardMetrics(options?: SWRConfiguration) {
    return useSWR<DashboardMetrics>(
        '/dashboard/global-health/',
        {
            refreshInterval: TTL.METRICS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch paginated certificates with filters
 * TTL: 3 minutes
 */
export function useCertificates(
    page: number = 1,
    pageSize: number = 10,
    filters?: {
        status?: string;
        issuer?: string;
        search?: string;
        encryptionType?: string;
        hasVulnerabilities?: boolean;
        expiringMonth?: number;
        expiringYear?: number;
    },
    options?: SWRConfiguration
) {
    // Build query string from filters
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('page_size', pageSize.toString());

    if (filters?.status) params.append('status', filters.status);
    if (filters?.issuer) params.append('issuer', filters.issuer);
    if (filters?.search) params.append('search', filters.search);
    if (filters?.encryptionType) params.append('encryption_type', filters.encryptionType);
    if (filters?.hasVulnerabilities !== undefined) {
        params.append('has_vulnerabilities', String(filters.hasVulnerabilities));
    }
    if (filters?.expiringMonth) params.append('expiring_month', filters.expiringMonth.toString());
    if (filters?.expiringYear) params.append('expiring_year', filters.expiringYear.toString());

    const key = `/certificates/?${params.toString()}`;

    return useSWR<CertificatesResponse>(key, {
        revalidateOnFocus: false,
        ...options,
    });
}

/**
 * Hook: Fetch CA leaderboard analytics
 * TTL: 15 minutes (stable data)
 */
export function useCAAnalytics(limit: number = 5, options?: SWRConfiguration) {
    return useSWR<CALeaderboardEntry[]>(
        `/ca-analytics/?limit=${limit}`,
        {
            refreshInterval: TTL.ANALYTICS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch encryption strength distribution
 * TTL: 15 minutes (stable data)
 */
export function useEncryptionStrength(options?: SWRConfiguration) {
    return useSWR<EncryptionStrength[]>(
        '/encryption-strength/',
        {
            refreshInterval: TTL.ANALYTICS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch validity trends (next 12 months)
 * TTL: 15 minutes
 */
export function useValidityTrends(months: number = 12, options?: SWRConfiguration) {
    return useSWR<ValidityTrendPoint[]>(
        `/validity-trends/?months=${months}`,
        {
            refreshInterval: TTL.ANALYTICS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch geographic distribution
 * TTL: 30 minutes (very stable)
 */
export function useGeographicDistribution(limit: number = 10, options?: SWRConfiguration) {
    return useSWR<GeographicEntry[]>(
        `/geographic-distribution/?limit=${limit}`,
        {
            refreshInterval: TTL.GEOGRAPHIC,
            ...options,
        }
    );
}

/**
 * Hook: Fetch future risk prediction
 * TTL: 15 minutes
 */
export function useFutureRisk(options?: SWRConfiguration) {
    return useSWR<FutureRisk>(
        '/future-risk/',
        {
            refreshInterval: TTL.ANALYTICS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch notifications
 * TTL: 2 minutes (time-sensitive)
 */
export function useNotifications(options?: SWRConfiguration) {
    return useSWR<NotificationResponse>(
        '/notifications/',
        {
            refreshInterval: TTL.NOTIFICATIONS,
            ...options,
        }
    );
}

/**
 * Hook: Fetch unique filter values (issuers, countries, etc.)
 * TTL: 30 minutes (very stable)
 */
export function useUniqueFilters(options?: SWRConfiguration) {
    return useSWR<{ issuers: string[]; countries: string[] }>(
        '/unique-filters/',
        {
            refreshInterval: TTL.GEOGRAPHIC,
            ...options,
        }
    );
}
