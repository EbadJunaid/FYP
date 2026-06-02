'use client';

import React, { useState, useCallback, useRef, useTransition, useEffect, useMemo } from 'react';
import useSWR from 'swr';
import { useRouter } from 'next/navigation';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { CertificateIcon, AlertIcon, GlobeIcon } from '@/components/icons/Icons';
import { fetchCertificates } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';
import { useDatabaseKey } from '@/hooks/useDatabaseKey';
import { apiClient, SANStats, SANDistributionEntry, SANTLDEntry, SANWildcardBreakdown, SANFilteredCertsResponse } from '@/services/apiClient';
import {
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    PieChart, Pie, Cell
} from 'recharts';

const STORAGE_KEY = 'san-analytics-state';

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    totalSans: 'Total count of all SAN (Subject Alternative Name) entries across all certificates. Click to view all certificates.',
    avgSans: 'Average number of domain names protected per certificate.',
    wildcard: 'Click to filter certificates with wildcard SANs (*.domain.com).',
    multiDomain: 'Click to filter certificates protecting 5 or more domains (multi-domain/UCC certificates).',
};

// Filter types - added sanType for wildcard/standard pie click, tld for TLD bar click
type FilterType = 'standard' | 'wildcard' | 'multidomain' | 'bucket' | 'tld' | 'sanType';

// SWR fetchers
const sanStatsFetcher = () => apiClient.getSANStats();
const sanDistributionFetcher = () => apiClient.getSANDistribution();
const sanTldFetcher = () => apiClient.getSANTLDBreakdown(10);
const sanWildcardFetcher = () => apiClient.getSANWildcardBreakdown();

// Certificates fetcher with SAN filters - ⚡ NOW USING FAST PRE-COMPUTED API!
const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filterType = parts[1] as FilterType;
    const filterValue = parts[2] || '';
    const page = parseInt(parts[3]) || 1;
    const search = parts[4] || undefined;

    // If searching, use slow API (fetchCertificates)
    if (search) {
        // Build filter params for legacy API
        let san_tld: string | undefined;
        let san_type: string | undefined;
        let san_count_min: number | undefined;
        let san_count_max: number | undefined;

        if (filterType === 'wildcard') {
            san_type = 'wildcard';
        } else if (filterType === 'sanType') {
            san_type = filterValue;
        } else if (filterType === 'tld') {
            san_tld = filterValue;
        } else if (filterType === 'bucket' && filterValue) {
            const [min, max] = filterValue.split('-').map(Number);
            if (!isNaN(min)) san_count_min = min;
            if (!isNaN(max)) san_count_max = max;
        } else if (filterType === 'multidomain') {
            san_count_min = 5;
            san_count_max = 1000;
        }

        return fetchCertificates({
            page,
            pageSize: 10,
            search,
            san_tld,
            san_type,
            san_count_min,
            san_count_max,
        });
    }

    // ⚡ Use fast pre-computed API for filtered results!
    let apiFilterType: 'wildcard' | 'standard' | 'multi-domain' | 'san-count' | 'tld';
    let apiFilterValue: string | undefined;

    if (filterType === 'standard') {
        apiFilterType = 'standard';
    } else if (filterType === 'wildcard' || filterType === 'sanType' && filterValue === 'wildcard') {
        apiFilterType = 'wildcard';
    } else if (filterType === 'multidomain') {
        apiFilterType = 'multi-domain';
    } else if (filterType === 'bucket') {
        apiFilterType = 'san-count';
        // Convert bucket range to API format (e.g., "2-3" stays "2-3", "50-1000" becomes "50+")
        if (filterValue === '50-1000') {
            apiFilterValue = '50+';
        } else if (filterValue === '0-0') {
            apiFilterValue = '0';
        } else if (filterValue === '1-1') {
            apiFilterValue = '1';
        } else {
            apiFilterValue = filterValue;
        }
    } else if (filterType === 'tld') {
        apiFilterType = 'tld';
        apiFilterValue = filterValue;
    } else {
        // Fallback to legacy API
        return fetchCertificates({ page, pageSize: 10 });
    }

    // Call fast API
    const response = await apiClient.getSANFilteredCerts({
        filter_type: apiFilterType,
        filter_value: apiFilterValue,
        page,
        page_size: 10,
    });

    // Transform fast API response to match fetchCertificates format
    return {
        certificates: response.certificates.map((cert, index) => ({
            id: `${cert.cert_id}-${cert.domain}-${index}`,  // ⚡ Use unique combination to avoid duplicate keys
            cert_id: cert.cert_id,  // Keep original cert_id for navigation
            domain: cert.domain,
            san_count: cert.san_count,  // ⚡ Keep this for table display
            sample_sans: cert.sample_sans,
            issuer: Array.isArray(cert.issuer) ? cert.issuer[0] : cert.issuer,
            expiry: cert.expiry,
            grade: 'N/A' as const,
            status: 'VALID' as const,
            // ⚡ NOW enriched from main collection!
            vulnerabilities: cert.vulnerabilities || undefined,
            issuer_org: Array.isArray(cert.issuer) ? cert.issuer[0] : cert.issuer,
            common_name: cert.domain,
            scanDate: cert.expiry ? new Date(cert.expiry).toISOString().split('T')[0] : 'N/A',
            endDate: cert.expiry,
            sslGrade: 'N/A' as any,
            encryptionType: cert.encryption || 'Unknown',
            country: cert.country || 'Unknown',
        } as any)),
        pagination: {
            page: response.page,
            pageSize: response.page_size,
            totalPages: Math.ceil(response.total / response.page_size),
            total: response.total,
        },
    };
};

// Chart colors
const COLORS = ['#10b981', '#3b82f6', '#8b5cf6', '#f59e0b', '#ef4444', '#06b6d4', '#14b8a6', '#6366f1', '#ec4899', '#84cc16'];
const PIE_COLORS = { wildcard: '#f59e0b', standard: '#10b981' };
const formatSanBucketLabel = (bucket: string) => {
    return bucket;
};
const SAN_BUCKET_TICKS = ['0', '1', '2-3', '4-5', '6-10', '11-30', '31-50', '50+'];

export default function SANAnalyticsPage() {
    const router = useRouter();
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();
    const dbKey = useDatabaseKey('san');

    // State for filters
    const [filterType, setFilterType] = useState<FilterType>('standard');
    const [filterValue, setFilterValue] = useState<string>('');
    const [currentPage, setCurrentPage] = useState(1);
    const [isRestoring, setIsRestoring] = useState(true);
    const [isDownloadModalOpen, setIsDownloadModalOpen] = useState(false);

    const { searchQuery, setSearchQuery } = useSearch();

    // Clear search query on unmount
    useEffect(() => {
        return () => {
            setSearchQuery('');
        };
    }, [setSearchQuery]);

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

    // SWR data fetching
    const { data: sanStats, isLoading: isStatsLoading } = useSWR<SANStats>(
        `san-stats|${dbKey}`,
        sanStatsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: sanDistribution, isLoading: isDistLoading } = useSWR<SANDistributionEntry[]>(
        `san-distribution|${dbKey}`,
        sanDistributionFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    const { data: sanTlds, isLoading: isTldLoading } = useSWR<SANTLDEntry[]>(
        `san-tld|${dbKey}`,
        sanTldFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    const { data: wildcardBreakdown, isLoading: isWildcardLoading } = useSWR<SANWildcardBreakdown>(
        `san-wildcard|${dbKey}`,
        sanWildcardFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    // Build SWR key for certificates
    const swrKey = `san-certs|${filterType}|${filterValue}|${currentPage}|${searchQuery || ''}|${dbKey}`;

    const { data: certsData, isLoading: isCertsLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = certsData?.certificates || [];
    const totalPages = certsData?.pagination?.totalPages || 1;
    const distributionData = useMemo(() => {
        if (!sanDistribution || sanDistribution.length === 0) {
            return SAN_BUCKET_TICKS.map((bucket) => ({ bucket, count: 0 }));
        }

        const byBucket = new Map(
            sanDistribution.map((entry) => [String(entry.bucket), entry])
        );

        return SAN_BUCKET_TICKS.map((bucket) => (
            byBucket.get(bucket) || { bucket, count: 0 }
        ));
    }, [sanDistribution]);

    // Scroll to table on search
    useEffect(() => {
        if (searchQuery) {
            setCurrentPage(1);
            setTimeout(() => {
                tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
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

    const handleRowClick = useCallback((entry: ScanEntry) => {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
            filterType,
            filterValue,
            page: currentPage,
            scrollY: window.scrollY
        }));
        
        // Get pure certificate ID (cert_id field is always clean)
        const certId = (entry as any).cert_id || entry.id.split('-')[0];
        console.log('SAN Analytics - Row clicked:', {
            fullId: entry.id,
            certId: certId,
            domain: entry.domain
        });
        
        router.push(`/certificate/${certId}`);
    }, [filterType, filterValue, currentPage, router]);

    const handlePageChange = useCallback((page: number) => {
        startTransition(() => {
            setCurrentPage(page);
        });
    }, []);

    const handleBucketClick = useCallback((bucket: string) => {
        // Convert bucket label to range for backend
        const bucketRanges: Record<string, string> = {
            '0': '0-0',
            '1': '1-1',
            '2-3': '2-3',
            '4-5': '4-5',
            '6-10': '6-10',
            '11-30': '11-30',
            '31-50': '31-50',
            '50+': '50-1000',
        };
        handleCardClick('bucket', bucketRanges[bucket] || bucket);
    }, [handleCardClick]);

    // Get table title
    const getTableTitle = () => {
        switch (filterType) {
            case 'standard': return 'Standard Certificates (with SANs, no wildcards)';
            case 'wildcard': return 'Wildcard Certificates';
            case 'sanType': return filterValue === 'wildcard' ? 'Wildcard SAN Certificates' : 'Standard SAN Certificates';
            case 'multidomain': return 'Multi-Domain Certificates (5+ SANs)';
            case 'bucket': return `Certificates with ${filterValue.replace('-', ' to ')} SANs`;
            case 'tld': return `Certificates with ${filterValue} TLD`;
            default: return 'Standard Certificates (with SANs, no wildcards)';
        }
    };

    // Prepare pie data
    const pieData = wildcardBreakdown ? [
        { name: 'Wildcard', value: wildcardBreakdown.wildcard, color: PIE_COLORS.wildcard },
        { name: 'Standard', value: wildcardBreakdown.standard, color: PIE_COLORS.standard },
    ] : [];

    // Get active filter for download
    const getActiveFilter = () => {
        if (filterType === 'standard') return { type: 'san' as const, value: 'standard' };
        if (filterType === 'wildcard') return { type: 'san' as const, value: 'wildcard' };
        if (filterType === 'sanType') return { type: 'san' as const, value: filterValue }; // 'wildcard' or 'standard'
        if (filterType === 'multidomain') return { type: 'san' as const, value: 'multidomain' };
        if (filterType === 'bucket') return { type: 'san' as const, value: `count:${filterValue}` };
        if (filterType === 'tld') return { type: 'san' as const, value: `tld:${filterValue}` };
        return { type: 'san' as const, value: 'standard' }; // Default to standard
    };

    // Loading state
    if (isStatsLoading && !sanStats) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading SAN Analytics...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">SAN Analytics</h1>
                <p className="text-text-muted mt-1">Subject Alternative Name (SAN) distribution and analysis</p>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={sanStats?.total_sans?.toLocaleString() || '0'}
                    label="Total SANs"
                    infoTooltip={cardInfoTooltips.totalSans}
                />
                <MetricCard
                    icon={<GlobeIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={(() => {
                        const avg = sanStats?.avg_sans_per_cert || 0;
                        if (Number.isInteger(avg)) return avg.toString();
                        return `${Math.floor(avg)}-${Math.ceil(avg)}`;
                    })()}
                    label="Avg SANs per Cert"
                    infoTooltip={cardInfoTooltips.avgSans}
                />
                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={sanStats?.wildcard_certs?.toLocaleString() || '0'}
                    label="Wildcard Certs"
                    infoTooltip={cardInfoTooltips.wildcard}
                    onClick={() => handleCardClick('wildcard')}
                />
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={sanStats?.multi_domain_certs?.toLocaleString() || '0'}
                    label="Multi-Domain Certs"
                    badge={{ text: '5+ SANs', variant: 'info' }}
                    infoTooltip={cardInfoTooltips.multiDomain}
                    onClick={() => handleCardClick('multidomain')}
                />
            </div>

            {/* Charts Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* SAN Distribution Histogram */}
                <Card title="SAN Count Distribution" infoTooltip="Distribution of how many SANs certificates typically have. Click a bar to filter.">
                    <div className="h-72">
                        {isDistLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={280} minWidth={0}>
                                <BarChart data={distributionData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis
                                        dataKey="bucket"
                                        stroke="#9ca3af"
                                        fontSize={12}
                                        tickFormatter={(value) => formatSanBucketLabel(String(value))}
                                        ticks={SAN_BUCKET_TICKS}
                                        interval={0}
                                    />
                                    <YAxis stroke="#9ca3af" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        formatter={(value) => [Number(value).toLocaleString(), 'Certificates']}
                                        labelFormatter={(label) => formatSanBucketLabel(String(label))}
                                    />
                                    <Bar
                                        dataKey="count"
                                        fill="#3b82f6"
                                        radius={[4, 4, 0, 0]}
                                        cursor="pointer"
                                        onClick={(data: unknown) => {
                                            const d = data as { bucket?: string };
                                            if (d.bucket) handleBucketClick(d.bucket);
                                        }}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                {/* Wildcard vs Standard Pie */}
                <Card title="Wildcard vs Standard SANs" infoTooltip="Comparison of wildcard (*.domain) vs explicit subdomain SANs.">
                    <div className="h-72">
                        {isWildcardLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={280} minWidth={0}>
                                <PieChart>
                                    <Pie
                                        data={pieData}
                                        cx="50%"
                                        cy="50%"
                                        labelLine={false}
                                        label={({ name, percent }: { name?: string; percent?: number }) => `${name || ''} ${((percent || 0) * 100).toFixed(0)}%`}
                                        outerRadius={100}
                                        dataKey="value"
                                        cursor="pointer"
                                        onClick={(data: unknown) => {
                                            const d = data as { name?: string };
                                            if (d.name) {
                                                handleCardClick('sanType', d.name.toLowerCase());
                                            }
                                        }}
                                    >
                                        {pieData.map((entry, index) => (
                                            <Cell key={`cell-${index}`} fill={entry.color} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        formatter={(value) => [Number(value).toLocaleString(), 'SANs']}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>
            </div>

            {/* Top TLDs Bar Chart */}
            <Card title="Top TLDs by SAN Count" infoTooltip="Most common domain extensions (TLDs) found in SAN entries.">
                <div className="h-72">
                    {isTldLoading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-text-muted">Loading...</div>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%" minHeight={280} minWidth={0}>
                            <BarChart
                                layout="vertical"
                                data={sanTlds || []}
                                margin={{ top: 5, right: 30, left: 10, bottom: 5 }}
                            >
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                                <YAxis
                                    type="category"
                                    dataKey="tld"
                                    stroke="#9ca3af"
                                    fontSize={12}
                                    width={60}
                                />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                    formatter={(value) => [Number(value).toLocaleString(), 'SANs']}
                                />
                                <Bar
                                    dataKey="count"
                                    radius={[0, 4, 4, 0]}
                                    cursor="pointer"
                                    onClick={(data: unknown) => {
                                        const d = data as { tld?: string };
                                        if (d.tld) handleCardClick('tld', d.tld);
                                    }}
                                >
                                    {sanTlds?.map((entry, index) => (
                                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                    ))}
                                </Bar>
                            </BarChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </Card>

            {/* Certificate Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    subtitle="Certificates filtered by SAN analysis criteria"
                    infoTooltip="View certificates filtered by SAN count, wildcard usage, or TLD."
                    headerAction={
                        <div className="flex items-center gap-2">
                            {/* Quick Filter Buttons */}
                            <button
                                onClick={() => handleCardClick('standard', '')}
                                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${filterType === 'standard'
                                    ? 'bg-primary-blue/20 text-primary-blue'
                                    : 'text-text-secondary hover:text-primary-blue hover:bg-primary-blue/10'
                                    }`}
                            >
                                Standard
                            </button>
                            <button
                                onClick={() => handleCardClick('wildcard', '')}
                                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${filterType === 'wildcard'
                                    ? 'bg-accent-yellow/20 text-accent-yellow'
                                    : 'text-text-secondary hover:text-accent-yellow hover:bg-accent-yellow/10'
                                    }`}
                            >
                                Wildcard
                            </button>

                            {/* SAN Count Dropdown */}
                            <select
                                value={filterType === 'bucket' ? filterValue : ''}
                                onChange={(e) => {
                                    if (e.target.value) {
                                        handleBucketClick(e.target.value);
                                    }
                                }}
                                className="px-3 py-1.5 text-sm font-medium rounded-md bg-card-bg border border-card-border text-text-secondary hover:text-primary-blue focus:outline-none focus:ring-2 focus:ring-primary-blue/50"
                            >
                                <option value="">SAN Count...</option>
                                <option value="0">0</option>
                                <option value="1">1 SAN</option>
                                <option value="2-3">2-3 SANs</option>
                                <option value="4-5">4-5 SANs</option>
                                <option value="6-10">6-10 SANs</option>
                                <option value="11-30">11-30 SANs</option>
                                <option value="31-50">31-50 SANs</option>
                                <option value="50+">50+ SANs</option>
                            </select>

                            <div className="w-px h-5 bg-border-default mx-1" />
                    {/*
                            <button
                                onClick={() => setIsDownloadModalOpen(true)}
                                className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors"
                            >
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                </svg>
                                Download
                            </button>
                    */}
                        </div>
                    }
                >
                    <div className={`transition-opacity duration-200 ${isCertsLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
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
                                showSanColumn={true}
                                enableNavigation={false}  // ⚡ Disable DataTable's navigation - we handle it ourselves!
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
                activeFilter={getActiveFilter()}
                totalCount={certsData?.pagination?.total || 0}
            />
        </div>
    );
}
