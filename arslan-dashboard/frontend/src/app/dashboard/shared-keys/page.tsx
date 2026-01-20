'use client';

import React, { useState, useCallback, useRef, useTransition, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { CertificateIcon, AlertIcon, ShieldIcon, KeyIcon } from '@/components/icons/Icons';
import { fetchCertificates } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';
import {
    apiClient,
    SharedKeyStats,
    SharedKeyDistributionEntry,
    SharedKeyIssuerEntry,
    SharedKeyTimelineEntry,
    SharedKeyHeatmapEntry
} from '@/services/apiClient';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    AreaChart, Area, Cell
} from 'recharts';

const STORAGE_KEY = 'shared-keys-state';

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    uniqueKeys: 'Total number of distinct public keys across all certificates.',
    sharedGroups: 'Number of public keys that appear in more than one certificate. Click to view all at-risk certificates.',
    atRisk: 'Total certificates that share a public key with at least one other certificate.',
    mostAffected: 'The domain with the most certificates sharing a single key.',
};

// Filter type
type FilterType = 'all' | 'shared' | 'issuer' | 'bucket';

// SWR fetchers
const statsFetcher = () => apiClient.getSharedKeyStats();
const distributionFetcher = () => apiClient.getSharedKeyDistribution();
const issuerFetcher = () => apiClient.getSharedKeysByIssuer(10);
const timelineFetcher = () => apiClient.getSharedKeyTimeline(12);
const heatmapFetcher = () => apiClient.getSharedKeyHeatmap(10);

// Certificates fetcher with shared key filters
const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filterType = parts[1];
    const filterValue = parts[2];
    const page = parseInt(parts[3]) || 1;
    const search = parts[4] || undefined;

    return fetchCertificates({
        page,
        pageSize: 10,
        search,
        shared_key: filterType === 'shared' ? true : undefined,
    });
};

// Chart colors
const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16'];

export default function SharedKeysPage() {
    const router = useRouter();
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();

    // State for filters
    const [filterType, setFilterType] = useState<FilterType>('all');
    const [filterValue, setFilterValue] = useState<string>('');
    const [currentPage, setCurrentPage] = useState(1);
    const [isRestoring, setIsRestoring] = useState(true);
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);

    const { searchQuery } = useSearch();

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
            }
        } catch (e) {
            console.error('Error restoring state:', e);
        }
        setIsRestoring(false);
    }, []);

    // Save state before navigation
    const saveState = useCallback(() => {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                filterType,
                filterValue,
                page: currentPage,
                scrollY: window.scrollY
            }));
        } catch (e) {
            console.error('Error saving state:', e);
        }
    }, [filterType, filterValue, currentPage]);

    // API Data fetching with SWR
    const { data: stats, isLoading: isStatsLoading } = useSWR<SharedKeyStats>(
        'shared-key-stats',
        statsFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: distribution, isLoading: isDistLoading } = useSWR<SharedKeyDistributionEntry[]>(
        'shared-key-distribution',
        distributionFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: issuerData, isLoading: isIssuerLoading } = useSWR<SharedKeyIssuerEntry[]>(
        'shared-key-issuer',
        issuerFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: timeline, isLoading: isTimelineLoading } = useSWR<SharedKeyTimelineEntry[]>(
        'shared-key-timeline',
        timelineFetcher,
        { dedupingInterval: 600000, revalidateOnFocus: false }
    );

    const { data: heatmap, isLoading: isHeatmapLoading } = useSWR<SharedKeyHeatmapEntry[]>(
        'shared-key-heatmap',
        heatmapFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    // Certificates table data
    const { data: certificatesData, isLoading: isTableLoading } = useSWR(
        isRestoring ? null : `shared-certs|${filterType}|${filterValue}|${currentPage}|${searchQuery}`,
        certificatesFetcher,
        { dedupingInterval: 60000, revalidateOnFocus: false }
    );

    const tableData: ScanEntry[] = certificatesData?.certificates || [];
    const totalPages = certificatesData?.pagination?.totalPages || 1;
    const totalItems = certificatesData?.pagination?.total || 0;

    // Handlers
    const handleCardClick = useCallback((type: FilterType, value?: string) => {
        startTransition(() => {
            setFilterType(type);
            setFilterValue(value || '');
            setCurrentPage(1);
        });
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    const handlePageChange = useCallback((page: number) => {
        setCurrentPage(page);
    }, []);

    const handleRowClick = useCallback((entry: ScanEntry) => {
        saveState();
        router.push(`/certificate/${entry.id}`);
    }, [saveState, router]);

    // Get table title based on filter
    const getTableTitle = () => {
        if (filterType === 'shared') return 'Certificates with Shared Keys';
        if (filterType === 'issuer') return `Certificates by Issuer: ${filterValue}`;
        if (filterType === 'bucket') return `Certificates in Group Size: ${filterValue}`;
        return 'All Certificates';
    };

    // Transform heatmap data for display
    const getHeatmapData = (): { issuerMap: Record<string, Record<string, number>>; keyTypeList: string[] } => {
        if (!heatmap || heatmap.length === 0) return { issuerMap: {}, keyTypeList: [] };

        const issuerMap: Record<string, Record<string, number>> = {};
        const keyTypes = new Set<string>();

        heatmap.forEach(entry => {
            if (!issuerMap[entry.issuer]) issuerMap[entry.issuer] = {};
            issuerMap[entry.issuer][entry.key_type] = entry.count;
            keyTypes.add(entry.key_type);
        });

        const keyTypeList = Array.from(keyTypes).sort();
        return { issuerMap, keyTypeList };
    };

    const heatmapData = getHeatmapData();

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <div>
                    <h1 className="text-2xl font-bold text-text-primary">Shared Public Keys Analysis</h1>
                    <p className="text-text-muted mt-1">
                        Identify certificates sharing the same public key — a significant security risk.
                    </p>
                </div>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                    label="Unique Public Keys"
                    value={stats?.unique_keys?.toLocaleString() || '0'}
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    infoTooltip={cardInfoTooltips.uniqueKeys}
                />
                <MetricCard
                    label="Shared Key Groups"
                    value={stats?.shared_key_groups?.toLocaleString() || '0'}
                    icon={<AlertIcon className="w-6 h-6 text-accent-yellow" />}
                    badge={stats && stats.shared_key_groups > 50 ? { text: 'High Risk', variant: 'error' } : stats && stats.shared_key_groups > 10 ? { text: 'Medium Risk', variant: 'warning' } : { text: 'Low Risk', variant: 'success' }}
                    infoTooltip={cardInfoTooltips.sharedGroups}
                />
                <MetricCard
                    label="Certificates at Risk"
                    value={stats?.certificates_at_risk?.toLocaleString() || '0'}
                    icon={<ShieldIcon className="w-6 h-6 text-accent-red" />}
                    infoTooltip={cardInfoTooltips.atRisk}
                    onClick={() => handleCardClick('shared')}
                />
                <MetricCard
                    label="Most Affected Domain"
                    value={stats?.most_affected_domain?.name?.substring(0, 20) || 'N/A'}
                    icon={<KeyIcon className="w-6 h-6 text-primary-purple" />}
                    infoTooltip={cardInfoTooltips.mostAffected}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Group Size Distribution */}
                <Card title="Shared Key Group Sizes" infoTooltip="Distribution of how many certificates share each key. Click a bar to filter.">
                    <div className="h-72">
                        {isDistLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                                <BarChart data={distribution || []} margin={{ top: 20, right: 20, left: 0, bottom: 5 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="bucket" stroke="#9ca3af" fontSize={12} />
                                    <YAxis stroke="#9ca3af" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                    />
                                    <Bar
                                        dataKey="count"
                                        fill="#3b82f6"
                                        cursor="pointer"
                                    >
                                        {distribution?.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                {/* Key Reuse by Issuer */}
                <Card title="Key Reuse by Issuer" infoTooltip="Top Certificate Authorities with certificates involved in key reuse.">
                    <div className="h-72">
                        {isIssuerLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                                <BarChart
                                    layout="vertical"
                                    data={issuerData || []}
                                    margin={{ top: 5, right: 20, left: 100, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                                    <YAxis
                                        type="category"
                                        dataKey="issuer"
                                        stroke="#9ca3af"
                                        fontSize={11}
                                        width={90}
                                        tickFormatter={(value: string) => value.length > 15 ? value.substring(0, 15) + '...' : value}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                    />
                                    <Bar
                                        dataKey="shared_certs"
                                        fill="#f59e0b"
                                        cursor="pointer"
                                    >
                                        {issuerData?.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Bar>
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>
            </div>

            {/* Timeline */}
            <Card title="Key Reuse Timeline" subtitle="New certificates per month joining shared key groups" infoTooltip="Shows trend of key reuse over time. An upward trend indicates growing security risk.">
                <div className="h-72">
                    {isTimelineLoading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-text-muted">Loading...</div>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                            <AreaChart data={timeline || []} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <defs>
                                    <linearGradient id="sharedGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#ef4444" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0.1} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="count"
                                    stroke="#ef4444"
                                    fill="url(#sharedGradient)"
                                    strokeWidth={2}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </Card>

            {/* Heatmap Table */}
            <Card title="Issuer × Key Type Matrix" infoTooltip="Shows which issuer/key-type combinations have the most shared keys.">
                <div className="overflow-x-auto">
                    {isHeatmapLoading ? (
                        <div className="flex items-center justify-center h-48">
                            <div className="text-text-muted">Loading heatmap...</div>
                        </div>
                    ) : heatmapData.keyTypeList.length === 0 ? (
                        <div className="flex items-center justify-center h-48">
                            <div className="text-text-muted">No shared keys found for heatmap</div>
                        </div>
                    ) : (
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-card-border">
                                    <th className="text-left py-3 px-4 text-text-secondary font-medium">Issuer</th>
                                    {heatmapData.keyTypeList.map((kt: string) => (
                                        <th key={kt} className="text-center py-3 px-4 text-text-secondary font-medium">{kt}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(heatmapData.issuerMap).map(([issuer, keyTypes]) => {
                                    const allCounts = Object.values(heatmapData.issuerMap).flatMap(kt => Object.values(kt as Record<string, number>));
                                    const maxCount = Math.max(...allCounts, 1);
                                    return (
                                        <tr key={issuer} className="border-b border-card-border/50 hover:bg-card-border/20">
                                            <td className="py-3 px-4 text-text-primary font-medium truncate max-w-[200px]" title={issuer}>
                                                {issuer.length > 25 ? issuer.substring(0, 25) + '...' : issuer}
                                            </td>
                                            {heatmapData.keyTypeList.map((kt: string) => {
                                                const count = (keyTypes as Record<string, number>)[kt] || 0;
                                                const intensity = count > 0 ? Math.max(0.2, count / maxCount) : 0;
                                                return (
                                                    <td
                                                        key={kt}
                                                        className="text-center py-3 px-4"
                                                        style={{
                                                            backgroundColor: count > 0 ? `rgba(239, 68, 68, ${intensity})` : 'transparent'
                                                        }}
                                                    >
                                                        <span className={count > 0 ? 'text-white font-semibold' : 'text-text-muted'}>
                                                            {count || '-'}
                                                        </span>
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    );
                                })}
                            </tbody>
                        </table>
                    )}
                </div>
            </Card>

            {/* Certificates Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    subtitle="Certificates potentially affected by shared key vulnerabilities"
                    headerAction={
                        <div className="flex items-center gap-3">
                            <div className="flex gap-2">
                                <button
                                    onClick={() => handleCardClick('all')}
                                    className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${filterType === 'all'
                                        ? 'bg-primary-blue text-white'
                                        : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                        }`}
                                >
                                    All
                                </button>
                                <button
                                    onClick={() => handleCardClick('shared')}
                                    className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${filterType === 'shared'
                                        ? 'bg-primary-blue text-white'
                                        : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                        }`}
                                >
                                    At Risk
                                </button>
                            </div>
                            <button
                                onClick={() => setIsDownloadModalOpen(true)}
                                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download
                            </button>
                        </div>
                    }
                >
                    <div className={`transition-opacity duration-200 ${isTableLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
                        {tableData.length === 0 && isTableLoading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-text-muted">Loading certificates...</div>
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
                currentPageData={tableData}
                activeFilter={{ type: 'all' }}
                totalCount={totalItems}
            />
        </div>
    );
}
