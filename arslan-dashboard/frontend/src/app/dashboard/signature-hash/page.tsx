'use client';

import React, { useState, useCallback, useRef, useMemo, useTransition, useEffect } from 'react';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { apiClient, SignatureStats, HashTrendEntry, IssuerAlgorithmEntry } from '@/services/apiClient';
import { fetchCertificates } from '@/controllers/pageController';
import { useSearch } from '@/context/SearchContext';
import {
    PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend,
    LineChart, Line, XAxis, YAxis, CartesianGrid
} from 'recharts';

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    maxEncryption: 'The encryption type (RSA or ECDSA) with the most certificates in the database.',
    hashCompliance: 'Percentage of certificates using secure hash algorithms (SHA-256, SHA-384, or SHA-512).',
    weakHash: 'Certificates using deprecated hash algorithms (MD5, SHA-1) that are vulnerable to collision attacks.',
    strengthScore: 'Composite security score (0-100) based on: Key Size (40%), Hash Algorithm (40%), Signature Type (20%).',
    keySize: 'Distribution of public key sizes across all certificates.',
    selfSigned: 'Certificates where issuer equals subject, often indicating test/development environments.',
    algoDistribution: 'Distribution of signature algorithms (SHA256-RSA, ECDSA-SHA256, etc.) across all certificates.',
    heatmap: 'Shows which Certificate Authorities use which algorithm/key size combinations.',
    hashTrends: 'Adoption trends of hash algorithms over time.',
    keySizeDist: 'Distribution of different key sizes and encryption types.',
    table: 'List of certificates. Click any card or chart to filter.'
};

// Filter types for signature page
type FilterType = 'all' | 'encryption' | 'algorithm' | 'hash' | 'keysize' | 'weak' | 'selfsigned' | 'heatmap';

// Pie chart colors - distinct colors for each algorithm
const ALGO_COLORS: Record<string, string> = {
    'SHA256-RSA': '#6366f1',      // Indigo
    'SHA384-RSA': '#8b5cf6',      // Purple
    'SHA512-RSA': '#a855f7',      // Violet
    'SHA1-RSA': '#f59e0b',        // Amber (warning)
    'MD5-RSA': '#ef4444',         // Red (critical)
    'ECDSA-SHA256': '#10b981',    // Emerald
    'ECDSA-SHA384': '#14b8a6',    // Teal
    'ECDSA-SHA512': '#06b6d4',    // Cyan
    'rsaEncryption': '#3b82f6',   // Blue
};

// Heatmap column definitions
const HEATMAP_COLUMNS = ['RSA-2048', 'RSA-4096', 'ECDSA-256', 'ECDSA-384'];

// SWR fetchers
const signatureStatsFetcher = () => apiClient.getSignatureStats();
const hashTrendsFetcher = () => apiClient.getHashTrends(36, 'quarterly');
const issuerMatrixFetcher = () => apiClient.getIssuerAlgorithmMatrix(10);

// Build API params from filter state
const buildApiParams = (filter: FilterType, filterValue: string, page: number): Record<string, unknown> => {
    const params: Record<string, unknown> = { page, pageSize: 10 };

    switch (filter) {
        case 'encryption':
            params.encryption_type = filterValue;
            break;
        case 'algorithm':
            params.signature_algorithm = filterValue;
            break;
        case 'hash':
            params.hash_type = filterValue;
            break;
        case 'keysize':
            params.encryption_type = filterValue;
            break;
        case 'weak':
            params.weak_hash = 'true';
            break;
        case 'selfsigned':
            params.self_signed = 'true';
            break;
        case 'heatmap':
            // Format: "issuer::RSA-2048" (using :: to avoid conflict with SWR key delimiter |)
            const heatmapParts = filterValue.split('::');
            if (heatmapParts[0]) params.issuer = heatmapParts[0];
            if (heatmapParts[1]) {
                // Convert "RSA-2048" to "RSA 2048" for backend
                params.encryption_type = heatmapParts[1].replace('-', ' ');
            }
            break;
    }

    return params;
};

// Certificates fetcher with filter and search
const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filter = parts[1] as FilterType;
    const filterValue = parts[2] || '';
    const page = parseInt(parts[3] || '1');
    const search = parts[4] || '';

    const params = buildApiParams(filter, filterValue, page);
    if (search) {
        params.search = search;
    }
    return fetchCertificates(params);
};

export default function SignatureHashPage() {
    const [activeFilter, setActiveFilter] = useState<FilterType>('all');
    const [filterValue, setFilterValue] = useState<string>('');
    const [currentPage, setCurrentPage] = useState(1);
    const [hiddenSegments, setHiddenSegments] = useState<Set<string>>(new Set());
    const [hiddenHashLines, setHiddenHashLines] = useState<Set<string>>(new Set());
    const [downloadModalOpen, setDownloadModalOpen] = useState(false);
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();
    const [isRestoring, setIsRestoring] = useState(true);

    const STORAGE_KEY = 'signature-hash-state';

    // Search context integration
    const { searchQuery } = useSearch();

    // Restore state from sessionStorage on mount
    useEffect(() => {
        try {
            const savedState = sessionStorage.getItem(STORAGE_KEY);
            if (savedState) {
                const { filter: savedFilter, filterValue: savedFilterValue, page: savedPage, scrollY: savedScrollY } = JSON.parse(savedState);
                if (savedFilter) setActiveFilter(savedFilter);
                if (savedFilterValue) setFilterValue(savedFilterValue);
                if (savedPage) setCurrentPage(savedPage);
                if (savedScrollY) {
                    setTimeout(() => window.scrollTo(0, savedScrollY), 100);
                }
                sessionStorage.removeItem(STORAGE_KEY);
            }
        } catch (e) {
            console.error('Error restoring page state:', e);
        }
        setIsRestoring(false);
    }, []);

    // Save state before navigation
    useEffect(() => {
        const handleBeforeUnload = () => {
            const stateToSave = { filter: activeFilter, filterValue, page: currentPage, scrollY: window.scrollY };
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
        };

        const handleLinkClick = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            const link = target.closest('a');
            if (link && link.href && !link.href.includes('signature-hash')) {
                handleBeforeUnload();
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        document.addEventListener('click', handleLinkClick);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            document.removeEventListener('click', handleLinkClick);
        };
    }, [activeFilter, filterValue, currentPage]);

    // Scroll to table and reset page when search query changes
    useEffect(() => {
        if (searchQuery) {
            setCurrentPage(1);
            // Scroll to table after a short delay to allow render
            setTimeout(() => {
                tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }, [searchQuery]);

    // SWR hooks for data fetching
    const { data: signatureStats, isLoading: statsLoading } = useSWR<SignatureStats>(
        'signature-stats',
        signatureStatsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: hashTrends, isLoading: trendsLoading } = useSWR<HashTrendEntry[]>(
        'hash-trends',
        hashTrendsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    const { data: issuerMatrix } = useSWR<IssuerAlgorithmEntry[]>(
        'issuer-matrix',
        issuerMatrixFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    // Certificates data with filter and search
    const swrKey = `sig-certs|${activeFilter}|${filterValue}|${currentPage}|${searchQuery || ''}`;
    const { data: certificatesData, isLoading: certsLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = certificatesData?.certificates || [];
    const totalPages = certificatesData?.pagination?.totalPages || 1;
    const totalItems = certificatesData?.pagination?.total || 0;

    // Handle filter change with auto-scroll
    const handleFilterChange = useCallback((filter: FilterType, value: string = '') => {
        startTransition(() => {
            setActiveFilter(filter);
            setFilterValue(value);
            setCurrentPage(1);
        });
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    // Handle page change WITHOUT scrolling
    const handlePageChange = useCallback((page: number) => {
        startTransition(() => {
            setCurrentPage(page);
        });
    }, []);

    // Toggle pie chart segment visibility
    const toggleSegment = useCallback((name: string) => {
        setHiddenSegments(prev => {
            const newSet = new Set(prev);
            if (newSet.has(name)) {
                newSet.delete(name);
            } else {
                newSet.add(name);
            }
            return newSet;
        });
    }, []);

    // Toggle hash trends line visibility
    const toggleHashLine = useCallback((name: string) => {
        setHiddenHashLines(prev => {
            const newSet = new Set(prev);
            if (newSet.has(name)) {
                newSet.delete(name);
            } else {
                newSet.add(name);
            }
            return newSet;
        });
    }, []);

    // Get active filter for download modal
    const getActiveFilterForModal = useCallback(() => {
        switch (activeFilter) {
            case 'weak':
                return { type: 'weakHash' as const, value: undefined };
            case 'selfsigned':
                return { type: 'selfSigned' as const, value: undefined };
            case 'algorithm':
                return { type: 'signatureAlgorithm' as const, value: filterValue };
            case 'hash':
                return { type: 'hashType' as const, value: filterValue };
            case 'keysize':
                return { type: 'keySize' as const, value: filterValue };
            case 'encryption':
                return { type: 'encryption' as const, value: filterValue };
            case 'heatmap':
                return { type: 'heatmap' as const, value: filterValue };
            default:
                return { type: 'all' as const, value: undefined };
        }
    }, [activeFilter, filterValue]);

    // Get table title based on filter
    const getTableTitle = useCallback(() => {
        switch (activeFilter) {
            case 'encryption':
                return `${filterValue} Certificates`;
            case 'algorithm':
                return `Certificates using ${filterValue}`;
            case 'hash':
                return `Certificates with ${filterValue} Hash`;
            case 'keysize':
                return `Certificates with ${filterValue}`;
            case 'weak':
                return 'Weak Hash Certificates (MD5/SHA-1)';
            case 'selfsigned':
                return 'Self-Signed Certificates';
            case 'heatmap':
                const [issuer, algo] = filterValue.split('::');
                return `${issuer} - ${algo} Certificates`;
            default:
                return 'All Certificates';
        }
    }, [activeFilter, filterValue]);

    // Prepare chart data with visibility filter and custom colors
    const algorithmChartData = useMemo(() => {
        return (signatureStats?.algorithmDistribution || [])
            .filter(item => !hiddenSegments.has(item.name))
            .map((item) => ({
                ...item,
                color: ALGO_COLORS[item.name] || '#6b7280'
            }));
    }, [signatureStats?.algorithmDistribution, hiddenSegments]);

    // All algorithm entries for legend (including hidden)
    const allAlgorithms = useMemo(() => {
        return (signatureStats?.algorithmDistribution || []).map((item) => ({
            ...item,
            color: ALGO_COLORS[item.name] || '#6b7280'
        }));
    }, [signatureStats?.algorithmDistribution]);

    // Transform issuer matrix into heatmap format
    const heatmapData = useMemo(() => {
        if (!issuerMatrix) return { issuers: [], matrix: {}, maxCount: 0 };

        const issuerCounts: Record<string, Record<string, number>> = {};
        let maxCount = 0;

        issuerMatrix.forEach(item => {
            if (!issuerCounts[item.issuer]) {
                issuerCounts[item.issuer] = {};
            }
            issuerCounts[item.issuer][item.algorithm] = item.count;
            if (item.count > maxCount) maxCount = item.count;
        });

        // Get top 10 issuers by total count
        const issuerTotals = Object.entries(issuerCounts).map(([issuer, algos]) => ({
            issuer,
            total: Object.values(algos).reduce((a, b) => a + b, 0)
        }));
        issuerTotals.sort((a, b) => b.total - a.total);
        const topIssuers = issuerTotals.slice(0, 10).map(i => i.issuer);

        return { issuers: topIssuers, matrix: issuerCounts, maxCount };
    }, [issuerMatrix]);

    const keySizeChartData = signatureStats?.keySizeDistribution || [];
    const maxEncType = signatureStats?.maxEncryptionType;

    // Loading state
    if (statsLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-blue"></div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Signature & Hash Analysis</h1>
                <p className="text-text-muted mt-1">Cryptographic signature algorithms and hash function analysis</p>
            </div>

            {/* Metrics Row - 6 Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
                {/* Card 1: Max Encryption Type */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-primary-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" /></svg>}
                    iconBgColor="bg-primary-blue/15"
                    value={maxEncType?.name || 'N/A'}
                    label="Max Encryption"
                    badge={maxEncType ? { text: `${maxEncType.percentage}%`, variant: 'info' } : undefined}
                    infoTooltip={cardInfoTooltips.maxEncryption}
                    onClick={() => maxEncType && handleFilterChange('encryption', maxEncType.name)}
                />

                {/* Card 2: Hash Compliance Rate - NOT CLICKABLE */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-accent-green" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" /></svg>}
                    iconBgColor={signatureStats?.hashComplianceRate && signatureStats.hashComplianceRate >= 95 ? "bg-accent-green/15" : "bg-accent-orange/15"}
                    value={`${signatureStats?.hashComplianceRate || 0}%`}
                    label="Hash Compliance"
                    badge={signatureStats?.hashComplianceRate && signatureStats.hashComplianceRate >= 99 ? { text: 'SECURE', variant: 'success' } : undefined}
                    infoTooltip={cardInfoTooltips.hashCompliance}
                />

                {/* Card 3: Weak Hash Alert - CLICKABLE when count > 0 */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-accent-red" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>}
                    iconBgColor={signatureStats?.weakHashCount ? "bg-accent-red/15" : "bg-accent-green/15"}
                    value={signatureStats?.weakHashCount?.toLocaleString() || '0'}
                    label="Weak Hash Certs"
                    badge={signatureStats?.weakHashCount && signatureStats.weakHashCount > 0 ? { text: 'WARNING', variant: 'warning' } : { text: 'NONE', variant: 'success' }}
                    infoTooltip={cardInfoTooltips.weakHash}
                    onClick={() => signatureStats?.weakHashCount && signatureStats.weakHashCount > 0 && handleFilterChange('weak')}
                />

                {/* Card 4: Signature Strength Score - NOT CLICKABLE */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-primary-purple" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" /></svg>}
                    iconBgColor="bg-primary-purple/15"
                    value={`${signatureStats?.strengthScore || 0}/100`}
                    label="Strength Score"
                    badge={signatureStats?.strengthScore && signatureStats.strengthScore >= 80 ? { text: 'STRONG', variant: 'success' } : signatureStats?.strengthScore && signatureStats.strengthScore >= 60 ? { text: 'FAIR', variant: 'warning' } : { text: 'WEAK', variant: 'error' }}
                    infoTooltip={cardInfoTooltips.strengthScore}
                />

                {/* Card 5: Top Key Size - CLICKABLE */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-primary-blue" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" /></svg>}
                    iconBgColor="bg-primary-blue/15"
                    value={keySizeChartData[0]?.name || 'N/A'}
                    label="Top Key Size"
                    badge={keySizeChartData[0] ? { text: `${keySizeChartData[0].percentage}%`, variant: 'info' } : undefined}
                    infoTooltip={cardInfoTooltips.keySize}
                    onClick={() => keySizeChartData[0] && handleFilterChange('keysize', keySizeChartData[0].name)}
                />

                {/* Card 6: Self-Signed Certificates - CLICKABLE when count > 0 */}
                <MetricCard
                    icon={<svg className="w-6 h-6 text-accent-orange" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>}
                    iconBgColor="bg-accent-orange/15"
                    value={signatureStats?.selfSignedCount?.toLocaleString() || '0'}
                    label="Self-Signed"
                    badge={signatureStats?.selfSignedCount && signatureStats.selfSignedCount > (signatureStats.totalCertificates * 0.05) ? { text: 'HIGH', variant: 'warning' } : undefined}
                    infoTooltip={cardInfoTooltips.selfSigned}
                    onClick={() => signatureStats?.selfSignedCount && signatureStats.selfSignedCount > 0 && handleFilterChange('selfsigned')}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Signature Algorithm Distribution Pie Chart with Legend Toggle */}
                <Card title="Signature Algorithm Distribution" infoTooltip={cardInfoTooltips.algoDistribution}>
                    <div className="h-72">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie
                                    data={algorithmChartData}
                                    dataKey="count"
                                    nameKey="name"
                                    cx="50%"
                                    cy="50%"
                                    outerRadius={80}
                                    innerRadius={0}
                                    labelLine={false}
                                    onClick={(data) => handleFilterChange('algorithm', data.name)}
                                    style={{ cursor: 'pointer' }}
                                >
                                    {algorithmChartData.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={entry.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    formatter={(value) => [typeof value === 'number' ? value.toLocaleString() : String(value ?? 0), 'Count']}
                                    contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                                    labelStyle={{ color: '#fff' }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    {/* Custom Legend with Toggle */}
                    <div className="flex flex-wrap justify-center gap-3 mt-2 px-2">
                        {allAlgorithms.map((item) => (
                            <button
                                key={item.name}
                                onClick={() => toggleSegment(item.name)}
                                className={`flex items-center gap-2 px-2 py-1 rounded text-xs transition-all ${hiddenSegments.has(item.name) ? 'opacity-40 line-through' : 'opacity-100'
                                    } hover:bg-surface-light`}
                            >
                                <span
                                    className="w-3 h-3 rounded-full flex-shrink-0"
                                    style={{ backgroundColor: item.color }}
                                ></span>
                                <span className="text-text-secondary">{item.name}</span>
                                <span className="text-text-muted">({item.percentage}%)</span>
                            </button>
                        ))}
                    </div>
                </Card>

                {/* Signature Strength Heatmap by Issuer */}
                <Card title="Signature Strength by Issuer" infoTooltip={cardInfoTooltips.heatmap}>
                    <div className="overflow-x-auto">
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
                                                {issuer}
                                            </td>
                                            {HEATMAP_COLUMNS.map(col => {
                                                const count = heatmapData.matrix[issuer]?.[col] || 0;
                                                const intensity = heatmapData.maxCount > 0 ? count / heatmapData.maxCount : 0;
                                                const bgOpacity = Math.max(0.1, intensity);

                                                return (
                                                    <td
                                                        key={col}
                                                        className="py-2 px-2 text-center cursor-pointer transition-all hover:ring-2 hover:ring-primary-blue"
                                                        onClick={() => count > 0 && handleFilterChange('heatmap', `${issuer}::${col}`)}
                                                        title={`${issuer}: ${count.toLocaleString()} ${col} certificates`}
                                                    >
                                                        {count > 0 && (
                                                            <div
                                                                className="w-full h-6 rounded flex items-center justify-center text-xs font-medium"
                                                                style={{
                                                                    backgroundColor: `rgba(99, 102, 241, ${bgOpacity})`,
                                                                    color: intensity > 0.5 ? '#fff' : '#a5b4fc'
                                                                }}
                                                            >
                                                                {count >= 1000 ? `${(count / 1000).toFixed(1)}k` : count}
                                                            </div>
                                                        )}
                                                    </td>
                                                );
                                            })}
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                    <div className="flex items-center justify-center gap-4 mt-4 text-xs text-text-muted">
                        <span>Intensity:</span>
                        <div className="flex items-center gap-1">
                            <div className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(99, 102, 241, 0.2)' }}></div>
                            <span>Low</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <div className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(99, 102, 241, 0.6)' }}></div>
                            <span>Medium</span>
                        </div>
                        <div className="flex items-center gap-1">
                            <div className="w-4 h-4 rounded" style={{ backgroundColor: 'rgba(99, 102, 241, 1)' }}></div>
                            <span>High</span>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Hash Adoption Trends Line Chart */}
            <Card title="Hash Algorithm Adoption Over Time" infoTooltip={cardInfoTooltips.hashTrends}>
                {trendsLoading ? (
                    <div className="h-64 flex items-center justify-center">
                        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-blue"></div>
                    </div>
                ) : (
                    <>
                        <div className="h-64">
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={hashTrends || []} margin={{ left: 0, right: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                                    <XAxis dataKey="period" stroke="#9ca3af" fontSize={12} />
                                    <YAxis stroke="#9ca3af" unit="%" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: 'none', borderRadius: '8px' }}
                                        labelStyle={{ color: '#fff' }}
                                        formatter={(value) => [`${value ?? 0}%`, '']}
                                    />
                                    {!hiddenHashLines.has('SHA-256') && (
                                        <Line type="monotone" dataKey="SHA-256" stroke="#10b981" strokeWidth={2} dot={false} />
                                    )}
                                    {!hiddenHashLines.has('SHA-384') && (
                                        <Line type="monotone" dataKey="SHA-384" stroke="#3b82f6" strokeWidth={2} dot={false} />
                                    )}
                                    {!hiddenHashLines.has('SHA-512') && (
                                        <Line type="monotone" dataKey="SHA-512" stroke="#1d4ed8" strokeWidth={2} dot={false} />
                                    )}
                                    {!hiddenHashLines.has('SHA-1') && (
                                        <Line type="monotone" dataKey="SHA-1" stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                                    )}
                                    {!hiddenHashLines.has('MD5') && (
                                        <Line type="monotone" dataKey="MD5" stroke="#ef4444" strokeWidth={2} strokeDasharray="5 5" dot={false} />
                                    )}
                                </LineChart>
                            </ResponsiveContainer>
                        </div>
                        {/* Custom Legend */}
                        <div className="flex flex-wrap justify-center gap-x-4 gap-y-2 mt-4 px-2">
                            {[
                                { name: 'SHA-256', color: '#10b981', secure: true },
                                { name: 'SHA-384', color: '#3b82f6', secure: true },
                                { name: 'SHA-512', color: '#1d4ed8', secure: true },
                                { name: 'SHA-1', color: '#f59e0b', secure: false },
                                { name: 'MD5', color: '#ef4444', secure: false },
                            ].map((item) => (
                                <button
                                    key={item.name}
                                    onClick={() => toggleHashLine(item.name)}
                                    className={`flex items-center gap-2 px-2 py-1 rounded text-xs transition-all ${hiddenHashLines.has(item.name) ? 'opacity-40 line-through' : 'opacity-100'
                                        } hover:bg-surface-light`}
                                >
                                    <span
                                        className={`w-4 h-0.5 ${!item.secure ? 'border-t-2 border-dashed' : ''}`}
                                        style={{ backgroundColor: item.color, borderColor: item.color }}
                                    ></span>
                                    <span className="text-text-secondary">{item.name}</span>
                                </button>
                            ))}
                        </div>
                    </>
                )}
            </Card>

            {/* Key Size Distribution */}
            <Card title="Key Size Distribution" infoTooltip={cardInfoTooltips.keySizeDist}>
                <div className="space-y-3">
                    {keySizeChartData.map((item) => (
                        <div
                            key={item.name}
                            className="flex items-center gap-4 cursor-pointer hover:bg-surface-light p-2 rounded-lg transition-colors"
                            onClick={() => handleFilterChange('keysize', item.name)}
                        >
                            <div className="w-24 font-medium text-text-primary">{item.name}</div>
                            <div className="flex-1">
                                <div className="h-6 bg-surface-dark rounded-full overflow-hidden">
                                    <div
                                        className="h-full rounded-full transition-all duration-500"
                                        style={{
                                            width: `${item.percentage}%`,
                                            backgroundColor: item.color
                                        }}
                                    ></div>
                                </div>
                            </div>
                            <div className="w-20 text-right text-text-muted">
                                {item.count.toLocaleString()}
                            </div>
                            <div className="w-16 text-right font-medium text-text-primary">
                                {item.percentage}%
                            </div>
                        </div>
                    ))}
                </div>
            </Card>

            {/* Certificates Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    infoTooltip={cardInfoTooltips.table}
                    headerAction={
                        <div className="flex items-center gap-3">
                            <div className="flex gap-2">
                                {(['all', 'weak', 'selfsigned'] as const).map((f) => (
                                    <button
                                        key={f}
                                        onClick={() => handleFilterChange(f)}
                                        className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${activeFilter === f
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                            }`}
                                    >
                                        {f === 'all' ? 'All' : f === 'weak' ? 'Weak Hash' : 'Self-Signed'}
                                    </button>
                                ))}
                            </div>
                            <button
                                onClick={() => setDownloadModalOpen(true)}
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
                    <div className={`transition-opacity duration-200 ${certsLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
                        {tableData.length === 0 && certsLoading ? (
                            <div className="flex items-center justify-center h-64">
                                <div className="text-text-muted">Loading certificates...</div>
                            </div>
                        ) : (
                            <DataTable
                                data={tableData}
                                currentPage={currentPage}
                                totalPages={totalPages}
                                onPageChange={handlePageChange}
                                onRowClick={(entry) => console.log('Row clicked:', entry)}
                            />
                        )}
                    </div>
                </Card>
            </div>

            {/* Download Modal */}
            <DownloadModal
                isOpen={downloadModalOpen}
                onClose={() => setDownloadModalOpen(false)}
                currentPageData={tableData}
                activeFilter={getActiveFilterForModal()}
                totalCount={totalItems}
            />
        </div>
    );
}
