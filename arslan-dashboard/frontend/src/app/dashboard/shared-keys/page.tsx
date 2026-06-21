'use client';

import React, { useState, useCallback, useRef, useTransition, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import Card from '@/components/Card';
import MetricCard from '@/components/dashboard/MetricCard';
import { CertificateIcon, AlertIcon, ShieldIcon, KeyIcon } from '@/components/icons/Icons';
import { useSearchOptional } from '@/context/SearchContext';
import { useDatabaseKey } from '@/hooks/useDatabaseKey';
import {
    apiClient,
    SharedKeyStats,
    SharedKeyDistributionEntry,
    SharedKeyIssuerEntry,
    SharedKeyHeatmapEntry
} from '@/services/apiClient';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell
} from 'recharts';

// TypeScript interfaces for shared keys list
interface SharedKeyIssuerInfo {
    organization: string;
    common_name?: string;
    certificate_count: number;
}

interface SharedKeyListItem {
    public_key_hash: string;
    public_key_hash_short: string;
    certificate_count: number;
    total_domains: number;
    sample_domains: string[];
    total_sans: number;
    sample_sans: string[];
    key_type: string;
    issuers: SharedKeyIssuerInfo[];
    issuer_count: number;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
}

const STORAGE_KEY = 'shared-keys-state';
const SELECTED_SCOPE_KEY = 'selected_certificate_scope';

const getStoredScope = () => {
    if (typeof window === 'undefined') return 'all';
    const params = new URLSearchParams(window.location.search);
    const urlScope = params.get('scope');
    if (urlScope) return urlScope;
    return localStorage.getItem(SELECTED_SCOPE_KEY) || 'all';
};

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    totalKeys: 'Total number of distinct public keys in the system, including both shared and unique keys.',
    uniqueKeys: 'Number of public keys that are used by only ONE certificate (truly unique, not shared with any other certificate).',
    sharedGroups: 'Number of public keys that appear in more than one certificate (security risk).',
    atRisk: 'Total certificates that share a public key with at least one other certificate.',
    mostAffected: 'The domain with the most certificates sharing a single key.',
};

// SWR fetchers
const statsFetcher = () => apiClient.getSharedKeyStats();
const distributionFetcher = () => apiClient.getSharedKeyDistribution();
const issuerFetcher = () => apiClient.getSharedKeysByIssuer(10);
const heatmapFetcher = () => apiClient.getSharedKeyHeatmap(10);

// Shared keys list fetcher
const sharedKeysListFetcher = async (key: string) => {
    const parts = key.split('|');
    const page = parseInt(parts[1]) || 1;
    const pageSize = parseInt(parts[2]) || 10;
    const sortBy = parts[3] || 'certificate_count';
    const sortOrder = parts[4] || 'desc';
    
    const scope = getStoredScope();
    const response = await fetch(`http://localhost:8000/api/shared-keys/list/?page=${page}&page_size=${pageSize}&sort_by=${sortBy}&sort_order=${sortOrder}&scope=${encodeURIComponent(scope)}`);
    const json = await response.json();
    if (json.success && json.data) {
        return json.data;
    }
    return { results: [], pagination: { total: 0, total_pages: 0 } };
};

// Chart colors
const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16'];

export default function SharedKeysPage() {
    const router = useRouter();
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();
    const dbKey = useDatabaseKey('shared-keys');

    // Clear search query on unmount
    const searchContext = useSearchOptional();
    useEffect(() => {
        return () => {
            if (searchContext) {
                searchContext.setSearchQuery('');
            }
        };
    }, [searchContext]);

    // State for table
    const [currentPage, setCurrentPage] = useState(1);
    const [pageSize] = useState(10);
    const [sortBy, setSortBy] = useState('certificate_count');
    const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
    const [isRestoring, setIsRestoring] = useState(true);

    // Restore state on mount
    useEffect(() => {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved) {
                const { page, scrollY } = JSON.parse(saved);
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
                page: currentPage,
                scrollY: window.scrollY
            }));
        } catch (e) {
            console.error('Error saving state:', e);
        }
    }, [currentPage]);

    // API Data fetching with SWR
    const { data: stats, isLoading: isStatsLoading } = useSWR<SharedKeyStats>(
        `shared-key-stats|${dbKey}`,
        statsFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: distribution, isLoading: isDistLoading } = useSWR<SharedKeyDistributionEntry[]>(
        `shared-key-distribution|${dbKey}`,
        distributionFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: issuerData, isLoading: isIssuerLoading } = useSWR<SharedKeyIssuerEntry[]>(
        `shared-key-issuer|${dbKey}`,
        issuerFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    const { data: heatmap, isLoading: isHeatmapLoading } = useSWR<SharedKeyHeatmapEntry[]>(
        `shared-key-heatmap|${dbKey}`,
        heatmapFetcher,
        { dedupingInterval: 300000, revalidateOnFocus: false }
    );

    // Shared keys list data (NEW)
    const { data: sharedKeysResponse, isLoading: isTableLoading } = useSWR(
        isRestoring ? null : `shared-keys-list|${currentPage}|${pageSize}|${sortBy}|${sortOrder}|${dbKey}`,
        sharedKeysListFetcher,
        { dedupingInterval: 60000, revalidateOnFocus: false }
    );

    const sharedKeysList: SharedKeyListItem[] = sharedKeysResponse?.results || [];
    const totalPages = sharedKeysResponse?.pagination?.total_pages || 1;
    const totalItems = sharedKeysResponse?.pagination?.total || 0;

    // Handlers
    const handlePageChange = useCallback((page: number) => {
        setCurrentPage(page);
    }, []);

    const handleRowClick = useCallback((publicKeyHash: string) => {
        saveState();
        router.push(`/dashboard/shared-keys/${publicKeyHash}`);
    }, [saveState, router]);

    const handleSort = useCallback((field: string) => {
        if (sortBy === field) {
            setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc');
        } else {
            setSortBy(field);
            setSortOrder('desc');
        }
        setCurrentPage(1);
    }, [sortBy, sortOrder]);

    const handleCardClick = useCallback((type: string) => {
        // Scroll to the shared keys table
        if (tableRef.current) {
            tableRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    }, []);

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

            {/* Metric Cards - First Row: Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-4">
                <MetricCard
                    label="Total Public Keys"
                    value={stats?.total_public_keys?.toLocaleString() || '0'}
                    icon={<KeyIcon className="w-6 h-6 text-primary-blue" />}
                    infoTooltip={cardInfoTooltips.totalKeys}
                />
                <MetricCard
                    label="Unique Public Keys"
                    value={stats?.unique_public_keys?.toLocaleString() || '0'}
                    icon={<CertificateIcon className="w-6 h-6 text-primary-green" />}
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
                    value={stats?.most_affected_domain?.name || 'N/A'}
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
                                        labelStyle={{ color: '#fff' }}
                                        itemStyle={{ color: '#fff' }}
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
                    <div className="h-80">
                        {isIssuerLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                                <BarChart
                                    layout="vertical"
                                    data={issuerData || []}
                                    margin={{ top: 5, right: 20, left: 20, bottom: 5 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                                    <YAxis
                                        type="category"
                                        dataKey="issuer"
                                        stroke="#9ca3af"
                                        fontSize={11}
                                        width={140}
                                        tickFormatter={(value: string) => value.length > 18 ? value.substring(0, 18) + '...' : value}
                                    />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        labelStyle={{ color: '#fff' }}
                                        itemStyle={{ color: '#fff' }}
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

            {/* Shared Keys Table */}
            <div ref={tableRef}>
                <Card
                    title="Shared Key Groups"
                    subtitle={`${totalItems} groups with certificates sharing the same public key`}
                >
                    <div className={`transition-opacity duration-200 ${isTableLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
                        {isTableLoading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-text-muted">Loading shared key groups...</div>
                            </div>
                        ) : sharedKeysList.length === 0 ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-text-muted">No shared key groups found</div>
                            </div>
                        ) : (
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-card-border">
                                            <th className="text-left py-3 px-4 text-text-secondary font-medium cursor-pointer hover:text-text-primary"
                                                onClick={() => handleSort('public_key_hash')}>
                                                Public Key Hash
                                            </th>
                                            <th className="text-center py-3 px-4 text-text-secondary font-medium cursor-pointer hover:text-text-primary"
                                                onClick={() => handleSort('certificate_count')}>
                                                Cert Count {sortBy === 'certificate_count' && (sortOrder === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th className="text-left py-3 px-4 text-text-secondary font-medium">
                                                Sample Domains
                                            </th>
                                            <th className="text-left py-3 px-4 text-text-secondary font-medium">
                                                Issuers
                                            </th>
                                            <th className="text-center py-3 px-4 text-text-secondary font-medium cursor-pointer hover:text-text-primary"
                                                onClick={() => handleSort('total_sans')}>
                                                Total SANs {sortBy === 'total_sans' && (sortOrder === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th className="text-center py-3 px-4 text-text-secondary font-medium">
                                                Key Type
                                            </th>
                                            <th className="text-center py-3 px-4 text-text-secondary font-medium cursor-pointer hover:text-text-primary"
                                                onClick={() => handleSort('risk_level')}>
                                                Risk {sortBy === 'risk_level' && (sortOrder === 'asc' ? '↑' : '↓')}
                                            </th>
                                            <th className="text-center py-3 px-4 text-text-secondary font-medium">
                                                Actions
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sharedKeysList.map((group) => (
                                            <tr key={group.public_key_hash} 
                                                className="border-b border-card-border/50 hover:bg-card-border/20 cursor-pointer transition-colors"
                                                onClick={() => handleRowClick(group.public_key_hash)}>
                                                <td className="py-3 px-4 font-mono text-xs text-text-primary">
                                                    <div className="flex items-center gap-2">
                                                        <span title={group.public_key_hash}>{group.public_key_hash_short || group.public_key_hash.substring(0, 16)}...</span>
                                                    </div>
                                                </td>
                                                <td className="text-center py-3 px-4">
                                                    <span className="inline-flex items-center justify-center px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-blue/20 text-primary-blue">
                                                        {group.certificate_count}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-text-primary">
                                                    <div className="flex flex-col gap-0.5">
                                                        {group.sample_domains.slice(0, 2).map((domain, idx) => (
                                                            <span key={idx} className="text-xs truncate max-w-[200px]" title={domain}>{domain}</span>
                                                        ))}
                                                        {group.total_domains > 2 && (
                                                            <span className="text-xs text-text-muted">+{group.total_domains - 2} more</span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="py-3 px-4 text-text-primary">
                                                    <div className="flex flex-col gap-0.5">
                                                        {group.issuers.slice(0, 2).map((issuer, idx) => (
                                                            <span key={idx} className="text-xs truncate max-w-[180px]" title={issuer.organization}>
                                                                {issuer.organization} ({issuer.certificate_count})
                                                            </span>
                                                        ))}
                                                        {group.issuer_count > 2 && (
                                                            <span className="text-xs text-text-muted">+{group.issuer_count - 2} more</span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="text-center py-3 px-4">
                                                    <div className="flex flex-col items-center gap-0.5">
                                                        <span className="text-sm font-semibold text-text-primary">{group.total_sans}</span>
                                                        {group.sample_sans.length > 0 && (
                                                            <span className="text-xs text-text-muted" title={group.sample_sans.join(', ')}>
                                                                {group.sample_sans.slice(0, 3).join(', ')}...
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="text-center py-3 px-4">
                                                    <span className="inline-flex items-center px-2 py-1 rounded text-xs font-medium bg-card-border text-text-primary">
                                                        {group.key_type}
                                                    </span>
                                                </td>
                                                <td className="text-center py-3 px-4">
                                                    <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${
                                                        group.risk_level === 'HIGH' ? 'bg-red-500/20 text-red-500' :
                                                        group.risk_level === 'MEDIUM' ? 'bg-orange-500/20 text-orange-500' :
                                                        'bg-green-500/20 text-green-500'
                                                    }`}>
                                                        {group.risk_level}
                                                    </span>
                                                </td>
                                                <td className="text-center py-3 px-4">
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation();
                                                            handleRowClick(group.public_key_hash);
                                                        }}
                                                        className="px-3 py-1 text-xs font-medium text-primary-blue hover:text-primary-blue/80 transition-colors"
                                                    >
                                                        View Details →
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>

                                {/* Pagination */}
                                {totalPages > 1 && (
                                    <div className="flex items-center justify-between mt-4 px-4 py-3 border-t border-card-border">
                                        <div className="text-sm text-text-muted">
                                            Showing page {currentPage} of {totalPages} ({totalItems} total groups)
                                        </div>
                                        <div className="flex gap-2">
                                            <button
                                                onClick={() => handlePageChange(currentPage - 1)}
                                                disabled={currentPage === 1}
                                                className="px-3 py-1.5 text-sm rounded-lg border border-card-border text-text-primary hover:bg-card-border disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                            >
                                                Previous
                                            </button>
                                            <button
                                                onClick={() => handlePageChange(currentPage + 1)}
                                                disabled={currentPage === totalPages}
                                                className="px-3 py-1.5 text-sm rounded-lg border border-card-border text-text-primary hover:bg-card-border disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                            >
                                                Next
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </Card>
            </div>
        </div>
    );
}
