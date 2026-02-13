'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useMemo, useEffect, useRef } from 'react';
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
    tableTitle: string; // Dynamic table title based on active filter
    activeFilter: ActiveFilter; // Exposed for download modal
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
    // Track loading state per component for progressive rendering
    loadingStates: {
        metrics: true,
        certificates: true,
        encryption: true,
        futureRisk: true,
        ca: true,
        geographic: true,
        trends: true,
    },
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

// Active filter type for card clicks (exported for DownloadModal)
export interface ActiveFilter {
    type: 'all' | 'active' | 'expiringSoon' | 'vulnerabilities' | 'ca' | 'geographic' | 'encryption' | 'validityTrend';
    value?: string;
}

export function DashboardProvider({ children }: DashboardProviderProps) {
    const [state, setState] = useState<DashboardState>(initialState);
    const [pagination, setPagination] = useState<PaginationState>(initialPagination);
    const [activeFilter, setActiveFilter] = useState<ActiveFilter>({ type: 'all' });

    // Use refs for values needed in callbacks to avoid recreating callbacks
    const activeFilterRef = useRef(activeFilter);
    const paginationRef = useRef(pagination);
    
    // Update refs when state changes
    useEffect(() => {
        activeFilterRef.current = activeFilter;
    }, [activeFilter]);
    
    useEffect(() => {
        paginationRef.current = pagination;
    }, [pagination]);

    // Page cache to avoid re-fetching previously loaded pages
    // Key format: "filterType:filterValue:page" -> cached result
    const pageCacheRef = useRef<Map<string, { certificates: ScanEntry[]; total: number }>>(new Map());

    // Generate cache key from current filter and page
    const getCacheKey = useCallback((filterType: string, filterValue: string | undefined, page: number) => {
        return `${filterType}:${filterValue || 'none'}:${page}`;
    }, []);

    // Fetch initial data from APIs - PROGRESSIVE LOADING (loads independently)
    const loadDashboardData = useCallback(async () => {
        setState((prev) => ({ ...prev, isLoading: true, error: null }));

        try {
            // ✅ OPTIMIZED: Load fast APIs first, then slow ones independently
            // Instead of Promise.all (which waits for ALL), we load progressively
            
            // Phase 1: Load FAST APIs first (these should return in < 5 seconds)
            Promise.all([
                fetchCertificates({ page: 1, pageSize: 10 }),
                fetchEncryptionStrength(),
                fetchCALeaderboard(10),
                fetchGeographicDistribution(10),
                fetchValidityTrends(18),
            ]).then(([certificatesData, encryptionData, caData, geoData, trendsData]) => {
                // Update state with fast data immediately
                setState((prev) => ({
                    ...prev,
                    recentScans: certificatesData.certificates,
                    encryptionStrength: encryptionData.map((e) => ({
                        ...e,
                        type: e.type as 'Strong' | 'Standard' | 'Modern' | 'Weak' | 'Deprecated',
                    })),
                    caLeaderboard: caData as CALeaderboardEntry[],
                    geographicDistribution: geoData as GeographicEntry[],
                    validityTrend: trendsData as ValidityTrendPoint[],
                    isLoading: false, // Mark as loaded so UI can render
                    loadingStates: {
                        ...prev.loadingStates!,
                        certificates: false,
                        encryption: false,
                        ca: false,
                        geographic: false,
                        trends: false,
                    },
                }));

                setPagination((prev) => ({
                    ...prev,
                    totalItems: certificatesData.pagination.total,
                }));
            }).catch((error) => {
                console.error('Error loading fast APIs:', error);
                setState((prev) => ({ ...prev, isLoading: false }));
            });

            // Phase 2: Load SLOW APIs independently (global-health, future-risk)
            // These load in the background without blocking the UI
            fetchDashboardMetrics().then((metrics) => {
                setState((prev) => ({
                    ...prev,
                    metrics: metrics as DashboardMetrics,
                    loadingStates: {
                        ...prev.loadingStates!,
                        metrics: false,
                    },
                }));
            }).catch((error) => {
                console.error('Error loading dashboard metrics:', error);
                setState((prev) => ({
                    ...prev,
                    loadingStates: {
                        ...prev.loadingStates!,
                        metrics: false,
                    },
                }));
            });

            fetchFutureRisk().then((futureRiskData) => {
                setState((prev) => ({
                    ...prev,
                    futureRisk: futureRiskData as FutureRisk,
                    loadingStates: {
                        ...prev.loadingStates!,
                        futureRisk: false,
                    },
                }));
            }).catch((error) => {
                console.error('Error loading future risk:', error);
                setState((prev) => ({
                    ...prev,
                    loadingStates: {
                        ...prev.loadingStates!,
                        futureRisk: false,
                    },
                }));
            });

        } catch (error) {
            console.error('Error loading dashboard data:', error);
            setState((prev) => ({
                ...prev,
                isLoading: false,
                error: 'Failed to load dashboard data. Please try again.',
            }));
        }
    }, []); // Empty deps for stable reference

    // Load data on mount - runs when component mounts
    // Also re-runs if loadDashboardData reference changes (won't happen with empty deps)
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

    // Handle filter application with API call - refetch ALL cards and table with all filter params
    const handleFilter = useCallback(async (filters: FilterOptions) => {
        setState((prev) => ({ ...prev, isLoading: true, filters }));

        // Clear page cache when filter changes
        pageCacheRef.current.clear();
        setActiveFilter({ type: 'all' });

        try {
            // Build ALL global filter params
            const globalFilterParams = {
                startDate: filters.dateRange.start ? filters.dateRange.start.toISOString() : undefined,
                endDate: filters.dateRange.end ? filters.dateRange.end.toISOString() : undefined,
                issuers: filters.issuer?.length > 0 ? filters.issuer : undefined,
                statuses: filters.status?.length > 0 ? filters.status : undefined,
                // Note: sslGrade maps to 'grades' in backend, but we use direct filter for now
                // validationLevel not yet in FilterOptions - can be added later
            };

            // Check if ANY filter is active
            const hasFilters =
                globalFilterParams.startDate ||
                globalFilterParams.endDate ||
                globalFilterParams.issuers?.length ||
                globalFilterParams.statuses?.length;

            // Fetch ALL data in parallel with ALL filter params applied
            const [
                certificatesData,
                encryptionData,
                caData,
                geoData,
            ] = await Promise.all([
                fetchCertificates({
                    page: 1,
                    pageSize: 10,
                    // Pass global filter params for backend filtering
                    startDate: globalFilterParams.startDate,
                    endDate: globalFilterParams.endDate,
                    issuers: globalFilterParams.issuers,
                    statuses: globalFilterParams.statuses,
                }),
                // Refetch analytics with ALL filter params if any filter is set
                hasFilters ? fetchEncryptionStrength(globalFilterParams) : Promise.resolve(state.encryptionStrength),
                hasFilters ? fetchCALeaderboard(10, globalFilterParams) : Promise.resolve(state.caLeaderboard),
                hasFilters ? fetchGeographicDistribution(10, globalFilterParams) : Promise.resolve(state.geographicDistribution),
            ]);

            setState((prev) => ({
                ...prev,
                recentScans: certificatesData.certificates,
                encryptionStrength: hasFilters ? encryptionData.map((e) => ({
                    ...e,
                    type: e.type as 'Strong' | 'Standard' | 'Modern' | 'Weak' | 'Deprecated',
                })) : prev.encryptionStrength,
                caLeaderboard: hasFilters ? caData as CALeaderboardEntry[] : prev.caLeaderboard,
                geographicDistribution: hasFilters ? geoData as GeographicEntry[] : prev.geographicDistribution,
                isLoading: false,
            }));

            setPagination((prev) => ({
                ...prev,
                currentPage: 1,
                totalItems: certificatesData.pagination.total,
            }));
        } catch (error) {
            console.error('Filter error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, [state.encryptionStrength, state.caLeaderboard, state.geographicDistribution]);

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

            // Clear old cache and store page 1 for new filter
            pageCacheRef.current.clear();
            const cacheKey = getCacheKey(activeFilter.type, activeFilter.value, 1);
            pageCacheRef.current.set(cacheKey, {
                certificates: result.certificates,
                total: result.pagination?.total || result.certificates.length,
            });
            console.log(`[PAGE CACHE SET] ${cacheKey} (card click page 1)`);
        } catch (error) {
            console.error('Card click error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, [getCacheKey]);

    // Set page for pagination - fetches new page data from API
    // Using refs to avoid recreating callback on every pagination/filter change
    const setPage = useCallback(async (page: number) => {
        const currentPagination = paginationRef.current;
        const currentActiveFilter = activeFilterRef.current;
        
        const maxPage = Math.ceil(currentPagination.totalItems / currentPagination.itemsPerPage);
        const newPage = Math.max(1, Math.min(page, maxPage));

        if (newPage === currentPagination.currentPage) return;

        // Check page cache first
        const cacheKey = getCacheKey(currentActiveFilter.type, currentActiveFilter.value, newPage);
        const cachedData = pageCacheRef.current.get(cacheKey);

        if (cachedData) {
            // Use cached data - instant response, no API call
            console.log(`[PAGE CACHE HIT] ${cacheKey}`);
            setState((prev) => ({
                ...prev,
                recentScans: cachedData.certificates,
            }));
            setPagination((prev) => ({
                ...prev,
                currentPage: newPage,
            }));
            return;
        }

        console.log(`[PAGE CACHE MISS] ${cacheKey} - fetching from API`);
        setState((prev) => ({ ...prev, isLoading: true }));

        try {
            let result;
            const pageSize = 10;

            // Fetch based on active filter type - use ref value
            switch (currentActiveFilter.type) {
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
                    result = await fetchCertificates({ page: newPage, pageSize, issuer: currentActiveFilter.value });
                    break;
                case 'geographic':
                    result = await fetchCertificates({ page: newPage, pageSize, country: currentActiveFilter.value });
                    break;
                case 'encryption':
                    result = await fetchCertificates({ page: newPage, pageSize, encryptionType: currentActiveFilter.value });
                    break;
                case 'validityTrend':
                    // Parse month/year from value like "Jan 2026"
                    const vMonthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    const vParts = (currentActiveFilter.value as string)?.split(' ') || [];
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

            // Store in page cache
            pageCacheRef.current.set(cacheKey, {
                certificates: result.certificates,
                total: result.pagination?.total || result.certificates.length,
            });
            console.log(`[PAGE CACHE SET] ${cacheKey}`);
        } catch (error) {
            console.error('Pagination error:', error);
            setState((prev) => ({ ...prev, isLoading: false }));
        }
    }, [getCacheKey]); // Only depends on getCacheKey now!

    // Reset filters and refresh data
    const resetFilters = useCallback(() => {
        setState((prev) => ({
            ...prev,
            filters: initialFilters,
            search: { query: '', isActive: false, results: [] },
        }));
        setPagination(initialPagination);
        // Clear page cache on reset
        pageCacheRef.current.clear();
        console.log('[PAGE CACHE CLEAR] Reset filters');
        loadDashboardData();
    }, [loadDashboardData]);

    // Manual refresh
    const refreshData = useCallback(() => {
        loadDashboardData();
    }, [loadDashboardData]);

    // Compute dynamic table title based on active filter
    const tableTitle = useMemo(() => {
        switch (activeFilter.type) {
            case 'active':
                return 'Active Certificates';
            case 'expiringSoon':
                return 'Expiring Soon Certificates';
            case 'vulnerabilities':
                return 'Certificates with Vulnerabilities';
            case 'ca':
                return activeFilter.value === 'Others'
                    ? 'Other CAs Certificates'
                    : `${activeFilter.value || 'CA'} Certificates`;
            case 'geographic':
                return `${activeFilter.value || 'Country'} Certificates`;
            case 'encryption':
                return `${activeFilter.value || 'Encryption'} Certificates`;
            case 'validityTrend':
                return `Certificates Expiring ${activeFilter.value || 'in Selected Month'}`;
            case 'all':
            default:
                return 'Recent Scans';
        }
    }, [activeFilter]);

    return (
        <DashboardContext.Provider
            value={{
                state,
                pagination,
                paginatedScans,
                totalPages,
                tableTitle,
                activeFilter,
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
