'use client';

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { CertificateIcon, GlobeIcon, ShieldIcon, AlertIcon, DownloadIcon } from '@/components/icons/Icons';
import { useSearch } from '@/context/SearchContext';
import apiClient, { CAStats, IssuerValidationEntry, CALeaderboardEntry } from '@/services/apiClient';
import { fetchCertificates } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';

const STORAGE_KEY = 'ca-analytics-state';

// Card info tooltips
const cardInfoTooltips = {
    totalCAs: 'Number of unique Certificate Authorities issuing certificates in your ecosystem.',
    topCA: 'The most prevalent CA by certificate count. Click to filter table.',
    selfSigned: 'Certificates signed by themselves rather than a trusted CA - may indicate development or internal certs.',
    countries: 'Geographic distribution of Certificate Authorities.',
    heatmap: 'Shows which Certificate Authorities issue which validation level certificates (DV/OV/EV). Click a cell to filter.',
};

// Heatmap columns for validation levels
const HEATMAP_COLUMNS = ['DV', 'OV', 'EV', 'Unknown'];

// SWR fetchers
const caStatsFetcher = () => apiClient.getCAStats();
const caDistributionFetcher = () => apiClient.getCAAnalytics(10);
const issuerValidationFetcher = () => apiClient.getIssuerValidationMatrix(10);

type FilterType = 'issuer' | 'self_signed' | 'heatmap';

const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filterType = parts[1] as FilterType;
    const filterValue = parts[2] || '';
    const page = parseInt(parts[3]) || 1;
    const search = parts[4] || undefined;

    let issuer: string | undefined;
    let selfSigned: string | undefined;
    let validationLevel: string | undefined;

    if (filterType === 'issuer' && filterValue) {
        issuer = filterValue;
    } else if (filterType === 'self_signed') {
        selfSigned = 'true';
    } else if (filterType === 'heatmap' && filterValue) {
        // Format: "issuer::validationLevel"
        const [iss, val] = filterValue.split('::');
        issuer = iss;
        validationLevel = val;
    }

    return fetchCertificates({
        page,
        pageSize: 10,
        issuer,
        self_signed: selfSigned,
        search,
        validationLevels: validationLevel ? [validationLevel] : undefined,
    });
};

// Colors for charts
const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16'];

export default function CAAnalyticsPage() {
    const router = useRouter();
    const tableRef = useRef<HTMLDivElement>(null);
    const { searchQuery } = useSearch();

    // State - default to top CA filter (set after data loads)
    const [filterType, setFilterType] = useState<FilterType>('issuer');
    const [filterValue, setFilterValue] = useState<string>('');
    const [currentPage, setCurrentPage] = useState(1);
    const [isRestoring, setIsRestoring] = useState(true);
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);
    const [defaultFilterSet, setDefaultFilterSet] = useState(false);

    // SWR data fetching
    const { data: caStats, isLoading: isStatsLoading } = useSWR<CAStats>(
        'ca-stats',
        caStatsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: caDistribution, isLoading: isDistLoading } = useSWR<CALeaderboardEntry[]>(
        'ca-distribution',
        caDistributionFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    const { data: issuerValidationMatrix, isLoading: isMatrixLoading } = useSWR<IssuerValidationEntry[]>(
        'issuer-validation-matrix',
        issuerValidationFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    // Restore state on mount
    useEffect(() => {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved) {
                const { filterType: ft, filterValue: fv, page, scrollY } = JSON.parse(saved);
                if (ft) setFilterType(ft);
                if (fv) setFilterValue(fv);
                if (page) setCurrentPage(page);
                if (scrollY) setTimeout(() => window.scrollTo(0, scrollY), 150);
                sessionStorage.removeItem(STORAGE_KEY);
                setDefaultFilterSet(true);
            }
        } catch (e) {
            console.error('Error restoring state:', e);
        }
        setIsRestoring(false);
    }, []);

    // Set default filter to top CA when data loads (if not restoring from session)
    useEffect(() => {
        if (!defaultFilterSet && caStats?.top_ca?.name && !isRestoring) {
            setFilterType('issuer');
            setFilterValue(caStats.top_ca.name);
            setDefaultFilterSet(true);
        }
    }, [caStats, defaultFilterSet, isRestoring]);

    // Process heatmap data
    const heatmapData = useMemo(() => {
        if (!issuerValidationMatrix || issuerValidationMatrix.length === 0) {
            return { issuers: [], matrix: {} as Record<string, Record<string, number>>, maxCount: 0 };
        }

        // Get unique issuers
        const issuerSet = new Set<string>();
        const matrix: Record<string, Record<string, number>> = {};
        let maxCount = 0;

        for (const entry of issuerValidationMatrix) {
            issuerSet.add(entry.issuer);
            if (!matrix[entry.issuer]) {
                matrix[entry.issuer] = {};
            }
            matrix[entry.issuer][entry.validationLevel] = entry.count;
            maxCount = Math.max(maxCount, entry.count);
        }

        return {
            issuers: Array.from(issuerSet),
            matrix,
            maxCount
        };
    }, [issuerValidationMatrix]);

    // Certificates table - build SWR key that works for all filter types
    const getSWRKey = () => {
        // For self_signed, we don't need filterValue
        if (filterType === 'self_signed') {
            return `ca-certs|self_signed|true|${currentPage}|${searchQuery || ''}`;
        }
        // For issuer and heatmap, we need filterValue
        if (filterValue) {
            return `ca-certs|${filterType}|${filterValue}|${currentPage}|${searchQuery || ''}`;
        }
        return null;
    };

    const swrKey = getSWRKey();
    const { data: certsData, isLoading: isCertsLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = certsData?.certificates || [];
    const totalPages = certsData?.pagination?.totalPages || 1;

    // Scroll to table on search
    useEffect(() => {
        if (searchQuery) {
            setCurrentPage(1);
            requestAnimationFrame(() => {
                setTimeout(() => {
                    tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            });
        }
    }, [searchQuery]);

    // Handler functions
    const handleCardClick = useCallback((type: FilterType, value: string = '') => {
        setFilterType(type);
        setFilterValue(value);
        setCurrentPage(1);
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    const handleBarClick = useCallback((data: { name?: string }) => {
        if (data.name) {
            // For "Others", API expects "Others" as issuer value
            handleCardClick('issuer', data.name);
        }
    }, [handleCardClick]);

    const handleHeatmapClick = useCallback((issuer: string, validationLevel: string) => {
        handleCardClick('heatmap', `${issuer}::${validationLevel}`);
    }, [handleCardClick]);

    const handleRowClick = useCallback((entry: ScanEntry) => {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
            filterType,
            filterValue,
            page: currentPage,
            scrollY: window.scrollY
        }));
        router.push(`/certificate/${entry.id}`);
    }, [filterType, filterValue, currentPage, router]);

    const handlePageChange = useCallback((page: number) => {
        setCurrentPage(page);
    }, []);

    const handleClearFilter = useCallback(() => {
        // Reset to top CA
        if (caStats?.top_ca?.name) {
            setFilterType('issuer');
            setFilterValue(caStats.top_ca.name);
        }
        setCurrentPage(1);
    }, [caStats]);

    // Build download modal filter
    const getActiveFilter = () => {
        if (filterType === 'issuer' && filterValue) {
            return { type: 'issuer' as const, value: filterValue };
        }
        if (filterType === 'self_signed') {
            return { type: 'selfSigned' as const, value: 'true' };
        }
        if (filterType === 'heatmap' && filterValue) {
            return { type: 'heatmap' as const, value: filterValue };
        }
        return { type: 'all' as const };
    };

    // Table title
    const getTableTitle = () => {
        if (filterType === 'issuer' && filterValue) {
            return `Certificates by ${filterValue}`;
        }
        if (filterType === 'self_signed') {
            return 'Self-Signed Certificates';
        }
        if (filterType === 'heatmap' && filterValue) {
            const [issuer, validation] = filterValue.split('::');
            return `${issuer} - ${validation} Certificates`;
        }
        return 'Certificates';
    };

    // Loading state
    if (isStatsLoading && !caStats) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading CA Analytics...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header */}
            <div>
                <h1 className="text-2xl font-bold text-text-primary">CA Analytics</h1>
                <p className="text-text-muted mt-1">Certificate Authority distribution and analysis</p>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={caStats?.total_cas?.toLocaleString() || '0'}
                    label="Total CAs"
                    infoTooltip={cardInfoTooltips.totalCAs}
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={caStats?.top_ca?.name || 'N/A'}
                    label={`Top CA (${caStats?.top_ca?.percentage || 0}%)`}
                    infoTooltip={cardInfoTooltips.topCA}
                    onClick={() => caStats?.top_ca?.name && handleCardClick('issuer', caStats.top_ca.name)}
                />
                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={caStats?.self_signed_count?.toLocaleString() || '0'}
                    label="Self-Signed"
                    badge={{ text: 'Review', variant: 'warning' }}
                    infoTooltip={cardInfoTooltips.selfSigned}
                    onClick={() => handleCardClick('self_signed')}
                />
                <MetricCard
                    icon={<GlobeIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={caStats?.unique_countries?.toLocaleString() || '0'}
                    label="CA Countries"
                    infoTooltip={cardInfoTooltips.countries}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* CA Market Share - Horizontal Bar Chart with fixed name wrapping */}
                <Card title="CA Market Share" infoTooltip="Top Certificate Authorities by certificate count. Click a bar to filter the table.">
                    <div className="h-80">
                        {isDistLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={320} minWidth={0}>
                                <BarChart
                                    layout="vertical"
                                    data={caDistribution}
                                    margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                                    <YAxis
                                        type="category"
                                        dataKey="name"
                                        stroke="#9ca3af"
                                        fontSize={11}
                                        width={120}
                                        tick={{ fill: '#9ca3af' }}
                                        tickFormatter={(value) => {
                                            // Truncate long names for display
                                            return value.length > 16 ? value.slice(0, 14) + '...' : value;
                                        }}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        formatter={(value, name) => [
                                            `${Number(value).toLocaleString()} (${caDistribution?.find(d => d.count === value)?.percentage || 0}%)`,
                                            name === 'count' ? 'Certificates' : String(name)
                                        ]}
                                        labelFormatter={(label) => label}
                                    />
                                    <Bar
                                        dataKey="count"
                                        radius={[0, 4, 4, 0]}
                                        cursor="pointer"
                                        onClick={(data) => handleBarClick(data)}
                                    >
                                        {caDistribution?.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color || COLORS[index % COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                {/* Validation Level by Issuer Heatmap */}
                <Card title="Validation Level by Issuer" infoTooltip={cardInfoTooltips.heatmap}>
                    <div className="overflow-x-auto">
                        {isMatrixLoading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <table className="w-full text-sm">
                                <thead>
                                    <tr>
                                        <th className="text-left py-2 px-3 text-text-muted font-medium">Issuer</th>
                                        {HEATMAP_COLUMNS.map(col => (
                                            <th key={col} className="text-center py-2 px-2 text-text-muted font-medium text-xs">
                                                {col}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {heatmapData.issuers.length === 0 ? (
                                        <tr>
                                            <td colSpan={5} className="py-8 text-center text-text-muted">
                                                No issuer data available
                                            </td>
                                        </tr>
                                    ) : (
                                        heatmapData.issuers.map((issuer) => (
                                            <tr key={issuer} className="border-t border-card-border">
                                                <td className="py-2 px-3 text-text-primary text-xs truncate max-w-[150px]" title={issuer}>
                                                    {issuer.length > 20 ? issuer.slice(0, 18) + '...' : issuer}
                                                </td>
                                                {HEATMAP_COLUMNS.map(col => {
                                                    const count = heatmapData.matrix[issuer]?.[col] || 0;
                                                    const intensity = heatmapData.maxCount > 0 ? count / heatmapData.maxCount : 0;
                                                    const bgOpacity = Math.max(0.1, intensity);

                                                    return (
                                                        <td
                                                            key={col}
                                                            className="py-2 px-2 text-center cursor-pointer transition-all hover:ring-2 hover:ring-primary-blue"
                                                            onClick={() => count > 0 && handleHeatmapClick(issuer, col)}
                                                            title={`${issuer}: ${count.toLocaleString()} ${col} certificates`}
                                                        >
                                                            {count > 0 && (
                                                                <span
                                                                    className="inline-block px-2 py-1 rounded text-xs font-medium min-w-[40px]"
                                                                    style={{
                                                                        backgroundColor: `rgba(99, 102, 241, ${bgOpacity})`,
                                                                        color: intensity > 0.5 ? '#fff' : '#c7d2fe'
                                                                    }}
                                                                >
                                                                    {count.toLocaleString()}
                                                                </span>
                                                            )}
                                                        </td>
                                                    );
                                                })}
                                            </tr>
                                        ))
                                    )}
                                </tbody>
                            </table>
                        )}
                    </div>
                </Card>
            </div>

            {/* Certificates Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    subtitle="Certificates filtered by CA analysis criteria"
                    infoTooltip="View certificates filtered by selected CA, validation level, or self-signed status."
                    headerAction={
                        <button
                            onClick={() => setIsDownloadModalOpen(true)}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Download
                        </button>
                    }
                >
                    <div className={`transition-opacity duration-200 ${isCertsLoading ? 'opacity-50' : 'opacity-100'}`}>
                        {!swrKey ? (
                            <div className="py-8 text-center text-text-muted">
                                Loading certificates...
                            </div>
                        ) : (
                            <DataTable
                                data={tableData}
                                currentPage={currentPage}
                                totalPages={totalPages}
                                onPageChange={handlePageChange}
                                onRowClick={handleRowClick}
                            />
                        )}
                    </div>
                </Card>
            </div>

            {/* Download Modal */}
            <DownloadModal
                isOpen={isDownloadModalOpen}
                onClose={() => setIsDownloadModalOpen(false)}
                activeFilter={getActiveFilter()}
                currentPageData={tableData}
            />
        </div>
    );
}
