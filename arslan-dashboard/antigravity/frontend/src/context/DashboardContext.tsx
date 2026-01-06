'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode, useMemo } from 'react';
import {
    DashboardState,
    ScanEntry,
    FilterOptions,
    EncryptionStrength,
    CALeaderboardEntry,
    GeographicEntry,
} from '@/types/dashboard';
import {
    mockDashboardMetrics,
    mockEncryptionStrength,
    mockFutureRisk,
    mockCALeaderboard,
    mockGeographicDistribution,
    mockValidityTrend,
    mockRecentScans,
    generateRandomScans,
} from '@/data/mockData';

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
}

const initialFilters: FilterOptions = {
    dateRange: { start: null, end: null },
    status: [],
    vulnerabilityType: [],
    issuer: [],
    sslGrade: [],
};

const initialState: DashboardState = {
    metrics: mockDashboardMetrics,
    encryptionStrength: mockEncryptionStrength,
    futureRisk: mockFutureRisk,
    caLeaderboard: mockCALeaderboard,
    geographicDistribution: mockGeographicDistribution,
    validityTrend: mockValidityTrend,
    recentScans: mockRecentScans,
    filters: initialFilters,
    search: {
        query: '',
        isActive: false,
        results: [],
    },
    isLoading: false,
    error: null,
};

const initialPagination: PaginationState = {
    currentPage: 1,
    itemsPerPage: 10,
    totalItems: mockRecentScans.length,
};

const DashboardContext = createContext<DashboardContextType | undefined>(undefined);

interface DashboardProviderProps {
    children: ReactNode;
}

export function DashboardProvider({ children }: DashboardProviderProps) {
    const [state, setState] = useState<DashboardState>(initialState);
    const [pagination, setPagination] = useState<PaginationState>(initialPagination);

    // Calculate paginated scans
    const paginatedScans = useMemo(() => {
        const startIndex = (pagination.currentPage - 1) * pagination.itemsPerPage;
        const endIndex = startIndex + pagination.itemsPerPage;
        return state.recentScans.slice(startIndex, endIndex);
    }, [state.recentScans, pagination.currentPage, pagination.itemsPerPage]);

    // Calculate total pages
    const totalPages = useMemo(() => {
        return Math.ceil(state.recentScans.length / pagination.itemsPerPage);
    }, [state.recentScans.length, pagination.itemsPerPage]);

    // Handle search functionality with filtering
    const handleSearch = useCallback((query: string) => {
        setState((prev) => {
            if (!query.trim()) {
                return {
                    ...prev,
                    search: { query: '', isActive: false, results: [] },
                    recentScans: mockRecentScans,
                };
            }

            const lowerQuery = query.toLowerCase();
            const filteredScans = mockRecentScans.filter(
                (scan) =>
                    scan.domain.toLowerCase().includes(lowerQuery) ||
                    scan.issuer.toLowerCase().includes(lowerQuery) ||
                    scan.status.toLowerCase().includes(lowerQuery) ||
                    scan.sslGrade.toLowerCase().includes(lowerQuery)
            );

            return {
                ...prev,
                search: { query, isActive: true, results: filteredScans },
                recentScans: filteredScans,
            };
        });

        // Reset to first page on search
        setPagination((prev) => ({ ...prev, currentPage: 1 }));
    }, []);

    // Handle filter application
    const handleFilter = useCallback((filters: FilterOptions) => {
        setState((prev) => {
            let filteredScans = [...mockRecentScans];

            // Filter by status
            if (filters.status.length > 0) {
                filteredScans = filteredScans.filter((scan) =>
                    filters.status.includes(scan.status)
                );
            }

            // Filter by SSL grade
            if (filters.sslGrade.length > 0) {
                filteredScans = filteredScans.filter((scan) =>
                    filters.sslGrade.includes(scan.sslGrade)
                );
            }

            // Filter by issuer
            if (filters.issuer.length > 0) {
                filteredScans = filteredScans.filter((scan) =>
                    filters.issuer.some((issuer) =>
                        scan.issuer.toLowerCase().includes(issuer.toLowerCase())
                    )
                );
            }

            return {
                ...prev,
                filters,
                recentScans: filteredScans,
            };
        });

        // Reset to first page on filter
        setPagination((prev) => ({ ...prev, currentPage: 1 }));
    }, []);

    // Handle card clicks - simulates fetching related data
    const handleCardClick = useCallback((cardType: string, data?: unknown) => {
        console.log(`Card clicked: ${cardType}`, data);

        // Simulate loading state
        setState((prev) => ({ ...prev, isLoading: true }));

        // Simulate API call delay
        setTimeout(() => {
            let newScans: ScanEntry[] = [];

            switch (cardType) {
                case 'globalHealth':
                    newScans = generateRandomScans(25);
                    break;
                case 'activeCertificates':
                    newScans = generateRandomScans(30).map((s) => ({ ...s, status: 'VALID' as const }));
                    break;
                case 'expiringSoon':
                    newScans = generateRandomScans(15).map((s) => ({ ...s, status: 'EXPIRING_SOON' as const }));
                    break;
                case 'vulnerabilities':
                    newScans = generateRandomScans(20).map((s) => ({
                        ...s,
                        vulnerabilities: ['1 Critical', '2 High', '3 Medium'][Math.floor(Math.random() * 3)],
                    }));
                    break;
                case 'encryptionBar':
                    const encData = data as EncryptionStrength;
                    console.log(`Filtering by encryption: ${encData?.name}`);
                    newScans = generateRandomScans(18);
                    break;
                case 'caLeaderboard':
                    const caData = data as CALeaderboardEntry;
                    newScans = generateRandomScans(22).map((s) => ({
                        ...s,
                        issuer: caData?.name || s.issuer,
                    }));
                    break;
                case 'geographic':
                    const geoData = data as GeographicEntry;
                    console.log(`Filtering by country: ${geoData?.country}`);
                    newScans = generateRandomScans(16);
                    break;
                case 'validityTrend':
                    newScans = generateRandomScans(28);
                    break;
                case 'futureRisk':
                    newScans = generateRandomScans(12).map((s) => ({
                        ...s,
                        status: ['WEAK', 'EXPIRING_SOON'][Math.floor(Math.random() * 2)] as 'WEAK' | 'EXPIRING_SOON',
                    }));
                    break;
                default:
                    newScans = mockRecentScans;
            }

            setState((prev) => ({
                ...prev,
                recentScans: newScans,
                isLoading: false,
            }));

            // Reset pagination
            setPagination((prev) => ({
                ...prev,
                currentPage: 1,
                totalItems: newScans.length,
            }));
        }, 300);
    }, []);

    // Set page for pagination
    const setPage = useCallback((page: number) => {
        setPagination((prev) => ({
            ...prev,
            currentPage: Math.max(1, Math.min(page, Math.ceil(prev.totalItems / prev.itemsPerPage))),
        }));
    }, []);

    // Reset filters
    const resetFilters = useCallback(() => {
        setState((prev) => ({
            ...prev,
            filters: initialFilters,
            search: { query: '', isActive: false, results: [] },
            recentScans: mockRecentScans,
        }));
        setPagination(initialPagination);
    }, []);

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
