'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useMemo, useEffect } from 'react';
import {
    DashboardState,
    ScanEntry,
    FilterOptions,
    EncryptionStrength,
    CALeaderboardEntry,
    GeographicEntry,
    DashboardMetrics,
    FutureRisk,
    ValidityTrendPoint,
} from '@/types/dashboard';
import {
    fetchDashboardMetrics,
    fetchCertificates,
    fetchEncryptionStrength,
    fetchFutureRisk,
    fetchCALeaderboard,
    fetchGeographicDistribution,
    fetchValidityTrends,
} from '@/controllers/pageController';

// Pagination state
interface PaginationState {
    currentPage: number;
    itemsPerPage: number;
    totalItems: number;
}

interface DashboardContextType {
    state: DashboardState;
    pagination: PaginationState;
    paginatedScans: ScanEntry[];
    totalPages: number;
    handleSearch: (query: string) => void;
    handleFilter: (filters: FilterOptions) => void;
    handleCardClick: (cardType: string, data?: unknown) => void;
    setPage: (page: number) => void;
    resetFilters: () => void;
    refreshData: () => void;
}

const initialFilters: FilterOptions = {
    dateRange: { start: null, end: null },
    status: [],
    vulnerabilityType: [],
    issuer: [],
    sslGrade: [],
};

const initialState: DashboardState = {
    metrics: null,
    encryptionStrength: [],
    futureRisk: null,
    caLeaderboard: [],
    geographicDistribution: [],
    validityTrend: [],
    recentScans: [],
    filters: initialFilters,
    search: {
        query: '',
        isActive: false,
        results: [],
    },
    isLoading: true,
    error: null,
};

const initialPagination: PaginationState = {
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: 0,
};

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

interface DashboardProviderProps {
    children: ReactNode;
}

// Active filter type for card clicks
interface ActiveFilter {
    type: 'all' | 'active' | 'expiringSoon' | 'vulnerabilities' | 'ca' | 'geographic' | 'encryption' | 'validityTrend';
    value?: string;
}

export function DashboardProvider({ children }: DashboardProviderProps) {
    const [state, setState] = useState<DashboardState>(initialState);
    const [pagination, setPagination] = useState<PaginationState>(initialPagination);
    const [activeFilter, setActiveFilter] = useState<ActiveFilter>({ type: 'all' });

    // Fetch initial data from APIs
    const loadDashboardData = useCallback(async () => {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        try {
            // Fetch all dashboard data in parallel
            const [
                metrics,
                certificatesData,
                encryptionData,
                futureRiskData,
                caData,
                geoData,
                trendsData,
            ] = await Promise.all([
                fetchDashboardMetrics(),
                fetchCertificates({ page: 1, pageSize: 10 }),
                fetchEncryptionStrength(),
                fetchFutureRisk(),
                fetchCALeaderboard(10),
                fetchGeographicDistribution(10),
                fetchValidityTrends(18),
            ]);

            setState((prev) => ({
                ...prev,
                metrics: metrics as DashboardMetrics,
                recentScans: certificatesData.certificates,
                encryptionStrength: encryptionData.map((e) => ({
                    ...e,
                    type: e.type as 'Strong' | 'Standard' | 'Modern' | 'Weak' | 'Deprecated',
                })),
                futureRisk: futureRiskData as FutureRisk,
                caLeaderboard: caData as CALeaderboardEntry[],
                geographicDistribution: geoData as GeographicEntry[],
                validityTrend: trendsData as ValidityTrendPoint[],
                isLoading: false,
            }));

            setPagination((prev) => ({
                ...prev,
                totalItems: certificatesData.pagination.total,
            }));
        } catch (error) {
            console.error('Error loading dashboard data:', error);
            setState((prev) => ({
                ...prev,
                isLoading: false,
                error: 'Failed to load dashboard data. Please try again.',
            }));
        }
    }, []);

    // Load data on mount
    useEffect(() => {
        loadDashboardData();
    }, [loadDashboardData]);

    // Paginated scans - data is already paginated from API, no local slicing needed
    const paginatedScans = useMemo(() => {
        // Return API-fetched data directly (already paginated by backend)
        return state.recentScans;
    }, [state.recentScans]);

    // Calculate total pages from API's total count
    const totalPages = useMemo(() => {
        // Use pagination.totalItems (from API response) divided by itemsPerPage
        return Math.max(1, Math.ceil(pagination.totalItems / pagination.itemsPerPage));
    }, [pagination.totalItems, pagination.itemsPerPage]);

    // Handle search functionality with API call
    const handleSearch = useCallback(async (query: string) => {
        if (!query.trim()) {
            // Reset to original data
            const certificatesData = await fetchCertificates({ page: 1, pageSize: 50 });
            setState((prev) => ({
                ...prev,
                search: { query: '', isActive: false, results: [] },
                recentScans: certificatesData.certificates,
            }));
            setPagination((prev) => ({ ...prev, currentPage: 1 }));
            return;
        }

        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            const result = await fetchCertificates({ page: 1, pageSize: 50, search: query });
            setState((prev) => ({
                ...prev,
                search: { query, isActive: true, results: result.certificates },
                recentScans: result.certificates,
                isLoading: false,
            }));
            setPagination((prev) => ({ ...prev, currentPage: 1 }));
        } catch (error) {
            console.error('Search error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, []);

    // Handle filter application with API call
    const handleFilter = useCallback(async (filters: FilterOptions) => {
        setState((prev) => ({ ...prev, isLoading: true, filters }));

        try {
            const result = await fetchCertificates({
                page: 1,
                pageSize: 50,
                status: filters.status.length > 0 ? filters.status[0] : undefined,
                issuer: filters.issuer.length > 0 ? filters.issuer[0] : undefined,
            });

            setState((prev) => ({
                ...prev,
                recentScans: result.certificates,
                isLoading: false,
            }));
            setPagination((prev) => ({ ...prev, currentPage: 1 }));
        } catch (error) {
            console.error('Filter error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, []);

    // Handle card clicks - fetch related data with proper filters
    const handleCardClick = useCallback(async (cardType: string, data?: unknown) => {
        console.log(`Card clicked: ${cardType}`, data);
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            let result;
            const pageSize = 10; // Consistent pagination

            switch (cardType) {
                case 'globalHealth':
                    // Fetch ALL certificates with pagination (no filter)
                    setActiveFilter({ type: 'all' });
                    result = await fetchCertificates({ page: 1, pageSize });
                    break;

                case 'activeCertificates':
                    // Fetch only VALID certificates (not expired)
                    setActiveFilter({ type: 'active' });
                    result = await fetchCertificates({ page: 1, pageSize, status: 'VALID' });
                    break;

                case 'expiringSoon':
                    // Fetch only certificates expiring within 30 days
                    setActiveFilter({ type: 'expiringSoon' });
                    result = await fetchCertificates({ page: 1, pageSize, status: 'EXPIRING_SOON' });
                    break;

                case 'vulnerabilities':
                    // Fetch certificates with vulnerabilities using SERVER-SIDE filtering
                    setActiveFilter({ type: 'vulnerabilities' });
                    result = await fetchCertificates({ page: 1, pageSize, hasVulnerabilities: true });
                    break;

                case 'encryption':
                case 'encryptionBar':
                    // Fetch certificates with specific encryption type (e.g., "RSA 2048")
                    const encData = data as EncryptionStrength;
                    setActiveFilter({ type: 'encryption', value: encData?.name });
                    result = await fetchCertificates({
                        page: 1,
                        pageSize,
                        encryptionType: encData?.name
                    });
                    break;

                case 'caLeaderboard':
                    // Fetch certificates from specific CA
                    const caData = data as CALeaderboardEntry;
                    setActiveFilter({ type: 'ca', value: caData?.name });
                    result = await fetchCertificates({
                        page: 1,
                        pageSize,
                        issuer: caData?.name
                    });
                    break;

                case 'geographic':
                    // Fetch certificates from specific country
                    const geoData = data as GeographicEntry;
                    setActiveFilter({ type: 'geographic', value: geoData?.country });
                    result = await fetchCertificates({
                        page: 1,
                        pageSize,
                        country: geoData?.country
                    });
                    break;

                case 'validityTrend':
                    // Fetch certificates expiring in specific month
                    const trendData = data as ValidityTrendPoint;
                    setActiveFilter({ type: 'validityTrend', value: trendData?.month });

                    // Parse month name and year from string like "Jan 2026"
                    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    const parts = trendData?.month?.split(' ') || [];
                    const monthName = parts[0];
                    const year = parseInt(parts[1] || '2026');
                    const monthIndex = monthNames.indexOf(monthName) + 1; // 1-based month

                    result = await fetchCertificates({
                        page: 1,
                        pageSize,
                        expiringMonth: monthIndex || undefined,
                        expiringYear: year || undefined
                    });
                    break;

                default:
                    setActiveFilter({ type: 'all' });
                    result = await fetchCertificates({ page: 1, pageSize });
            }

            setState((prev) => ({
                ...prev,
                recentScans: result.certificates,
                isLoading: false,
            }));
            // Use API pagination total for accurate page count
            setPagination((prev) => ({
                ...prev,
                currentPage: 1,
                itemsPerPage: 10,
                totalItems: result.pagination?.total || result.certificates.length,
            }));
        } catch (error) {
            console.error('Card click error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, []);

    // Set page for pagination - fetches new page data from API
    const setPage = useCallback(async (page: number) => {
        const maxPage = Math.ceil(pagination.totalItems / pagination.itemsPerPage);
        const newPage = Math.max(1, Math.min(page, maxPage));

        if (newPage === pagination.currentPage) return;

        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            let result;
            const pageSize = 10;

            // Fetch based on active filter type
            switch (activeFilter.type) {
                case 'all':
                    result = await fetchCertificates({ page: newPage, pageSize });
                    break;
                case 'active':
                    result = await fetchCertificates({ page: newPage, pageSize, status: 'VALID' });
                    break;
                case 'expiringSoon':
                    result = await fetchCertificates({ page: newPage, pageSize, status: 'EXPIRING_SOON' });
                    break;
                case 'vulnerabilities':
                    // Use server-side filtering for vulnerabilities
                    result = await fetchCertificates({ page: newPage, pageSize, hasVulnerabilities: true });
                    break;
                case 'ca':
                    result = await fetchCertificates({ page: newPage, pageSize, issuer: activeFilter.value });
                    break;
                case 'geographic':
                    result = await fetchCertificates({ page: newPage, pageSize, country: activeFilter.value });
                    break;
                case 'encryption':
                    result = await fetchCertificates({ page: newPage, pageSize, encryptionType: activeFilter.value });
                    break;
                case 'validityTrend':
                    // Parse month/year from value like "Jan 2026"
                    const vMonthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    const vParts = (activeFilter.value as string)?.split(' ') || [];
                    const vMonthName = vParts[0];
                    const vYear = parseInt(vParts[1] || '2026');
                    const vMonthIndex = vMonthNames.indexOf(vMonthName) + 1;
                    result = await fetchCertificates({ page: newPage, pageSize, expiringMonth: vMonthIndex || undefined, expiringYear: vYear || undefined });
                    break;
                default:
                    result = await fetchCertificates({ page: newPage, pageSize });
            }

            setState((prev) => ({
                ...prev,
                recentScans: result.certificates,
                isLoading: false,
            }));
            setPagination((prev) => ({
                ...prev,
                currentPage: newPage,
            }));
        } catch (error) {
            console.error('Pagination error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, [activeFilter, pagination.totalItems, pagination.itemsPerPage, pagination.currentPage]);

    // Reset filters and refresh data
    const resetFilters = useCallback(() => {
        setState((prev) => ({
            ...prev,
            filters: initialFilters,
            search: { query: '', isActive: false, results: [] },
        }));
        setPagination(initialPagination);
        loadDashboardData();
    }, [loadDashboardData]);

    // Manual refresh
    const refreshData = useCallback(() => {
        loadDashboardData();
    }, [loadDashboardData]);

    return (
        <DashboardContext.Provider
            value={{
                state,
                pagination,
                paginatedScans,
                totalPages,
                handleSearch,
                handleFilter,
                handleCardClick,
                setPage,
                resetFilters,
                refreshData,
            }}
        >
            {children}
        </DashboardContext.Provider>
    );
}

export function useDashboard() {
    const context = useContext(DashboardContext);
    if (context === undefined) {
        throw new Error('useDashboard must be used within a DashboardProvider');
    }
    return context;
}
