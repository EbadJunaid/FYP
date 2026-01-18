'use client';

import React, { useState, useCallback, useRef, useTransition, useEffect } from 'react';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { CertificateIcon, CheckCircleIcon, AlertIcon } from '@/components/icons/Icons';
import { fetchDashboardMetrics, fetchCertificates } from '@/controllers/pageController';
import { ScanEntry, DashboardMetrics } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';
import { apiClient, ValidityStats, ValidityDistributionEntry, IssuanceTimelineEntry, ValidityTrend } from '@/services/apiClient';
import {
    AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
    Legend, PieChart, Pie, Cell
} from 'recharts';


// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    avgDuration: 'Average number of days between certificate issuance (validFrom) and expiration (validTo) across all certificates.',
    expiring30: 'Number of certificates expiring within the next 30 days. These require immediate attention.',
    expiring90: 'Number of certificates expiring within the next 90 days. Plan for upcoming quarterly renewals.',
    complianceRate: 'Percentage of certificates with validity period ≤ 398 days, compliant with industry standards (as of 2020).',
};

// Status breakdown colors
const STATUS_COLORS = {
    valid: '#10b981',
    expiring: '#f59e0b',
    expired: '#ef4444',
};

// SWR fetchers
const validityStatsFetcher = () => apiClient.getValidityStats();
const validityDistributionFetcher = () => apiClient.getValidityDistribution();
const issuanceTimelineFetcher = () => apiClient.getIssuanceTimeline();
const metricsFetcher = () => fetchDashboardMetrics();

// Extended filter type for all card clicks, chart interactions, and table filters
// Includes: expiring-month-YYYY-MM for trends chart, issued-month-YYYY-MM and expired-month-YYYY-MM for timeline chart
type FilterType = 'all' | 'expiring30' | 'expiring90' | 'longest' | 'shortest' | 'avgDuration' | 'compliant' | 'valid' | 'expiring' | 'expired' | 'bucket-0-90' | 'bucket-90-365' | 'bucket-365-730' | 'bucket-730+' | string;

const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filter = parts[1] as FilterType;
    const page = parseInt(parts[2]);
    const search = parts[3] || undefined;

    // Determine filter params based on filter type
    let expiringDays: number | undefined;
    let validityBucket: string | undefined;
    let status: string | undefined;
    let expiringMonth: number | undefined;
    let expiringYear: number | undefined;
    let issuedMonth: number | undefined;
    let issuedYear: number | undefined;

    // Expiring card clicks - use distinct expiringDays parameter
    if (filter === 'expiring30') {
        expiringDays = 30;
    } else if (filter === 'expiring90') {
        expiringDays = 90;
    }
    // Status breakdown chart clicks
    else if (filter === 'valid') {
        status = 'VALID';
    } else if (filter === 'expiring') {
        status = 'EXPIRING_SOON';
    } else if (filter === 'expired') {
        status = 'EXPIRED';
    }
    // Validity distribution bucket clicks
    else if (filter.startsWith('bucket-')) {
        validityBucket = filter.replace('bucket-', '');
    }
    // Validity Trends chart point clicks - expiring in specific month
    else if (filter.startsWith('expiring-month-')) {
        const dateStr = filter.replace('expiring-month-', '');
        const [year, month] = dateStr.split('-').map(Number);
        expiringMonth = month;
        expiringYear = year;
    }
    // Validity Trends chart point clicks - expiring in specific week (range)
    else if (filter.startsWith('expiring-range::')) {
        const parts = filter.split('::');
        // Format: expiring-range::START_DATE::END_DATE
        // We handle this by passing these as special params to fetchCertificates
        // NOTE: expiringStart/expiringEnd variables need to be added to fetchCertificates signature first
        const rangeStart = parts[1];
        const rangeEnd = parts[2];
        return fetchCertificates({
            page,
            pageSize: 10,
            search: search || undefined,
            expiringStart: rangeStart,
            expiringEnd: rangeEnd
        });
    }
    // Issuance Timeline chart clicks - issued in specific month
    else if (filter.startsWith('issued-month-')) {
        const dateStr = filter.replace('issued-month-', '');
        const [year, month] = dateStr.split('-').map(Number);
        issuedMonth = month;
        issuedYear = year;
    }
    // Issuance Timeline chart clicks - expired in specific month
    else if (filter.startsWith('expired-month-')) {
        const dateStr = filter.replace('expired-month-', '');
        const [year, month] = dateStr.split('-').map(Number);
        expiringMonth = month;
        expiringYear = year;
    }
    // compliant and avgDuration - show all certs sorted by duration (handled in table)

    return fetchCertificates({
        page,
        pageSize: 10,
        status,
        expiringDays,
        validityBucket,
        expiringMonth,
        expiringYear,
        issuedMonth,
        issuedYear,
        search: search || undefined,
    });
};

export default function ValidityAnalyticsPage() {
    const [filter, setFilter] = useState<FilterType>('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [downloadModalOpen, setDownloadModalOpen] = useState(false);
    const [granularity, setGranularity] = useState<'monthly' | 'weekly'>('monthly');
    const [hiddenStatuses, setHiddenStatuses] = useState<Set<string>>(new Set());
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();
    const [isRestoring, setIsRestoring] = useState(true);

    const { searchQuery } = useSearch();

    const STORAGE_KEY = 'validity-analytics-state';

    // Restore state from sessionStorage on mount (for back navigation)
    useEffect(() => {
        try {
            const savedState = sessionStorage.getItem(STORAGE_KEY);
            if (savedState) {
                const { filter: savedFilter, page: savedPage, scrollY: savedScrollY } = JSON.parse(savedState);
                if (savedFilter) setFilter(savedFilter);
                if (savedPage) setCurrentPage(savedPage);
                // Restore scroll position after a short delay to allow content to render
                if (savedScrollY) {
                    setTimeout(() => window.scrollTo(0, savedScrollY), 100);
                }
                // Clear saved state after restoring (only restore once)
                sessionStorage.removeItem(STORAGE_KEY);
            }
        } catch (e) {
            console.error('Error restoring page state:', e);
        }
        setIsRestoring(false);
    }, []);

    // Save state to sessionStorage before navigating away
    useEffect(() => {
        const handleBeforeUnload = () => {
            // Save current state
            const stateToSave = {
                filter,
                page: currentPage,
                scrollY: window.scrollY
            };
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
        };

        // Listen for link clicks that would navigate away
        const handleLinkClick = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            const link = target.closest('a');
            if (link && link.href && !link.href.includes('validity-analytics')) {
                handleBeforeUnload();
            }
        };

        window.addEventListener('beforeunload', handleBeforeUnload);
        document.addEventListener('click', handleLinkClick);

        return () => {
            window.removeEventListener('beforeunload', handleBeforeUnload);
            document.removeEventListener('click', handleLinkClick);
        };
    }, [filter, currentPage]);

    // Scroll to table on search
    useEffect(() => {
        if (searchQuery) {
            setCurrentPage(1);
            setTimeout(() => {
                tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        }
    }, [searchQuery]);

    // SWR hooks
    const { data: validityStats, isLoading: isStatsLoading } = useSWR<ValidityStats>(
        'validity-stats',
        validityStatsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: distribution, isLoading: isDistLoading } = useSWR<ValidityDistributionEntry[]>(
        'validity-distribution',
        validityDistributionFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: timeline, isLoading: isTimelineLoading } = useSWR<IssuanceTimelineEntry[]>(
        'issuance-timeline',
        issuanceTimelineFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const { data: validityTrends, isLoading: isTrendsLoading } = useSWR<ValidityTrend[]>(
        ['validity-trends', granularity],
        () => apiClient.getValidityTrends(12, granularity),
        { revalidateOnFocus: false, dedupingInterval: 300000, keepPreviousData: true }
    );

    const { data: metrics } = useSWR<DashboardMetrics>(
        'dashboard-metrics',
        metricsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const swrKey = `validity-certs|${filter}|${currentPage}|${searchQuery || ''}`;
    const { data: tableResult, isLoading: isTableLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = tableResult?.certificates || [];
    const totalPages = tableResult?.pagination?.totalPages || 1;
    const totalItems = tableResult?.pagination?.total || 0;

    const handleFilterChange = useCallback((newFilter: FilterType) => {
        startTransition(() => {
            setFilter(newFilter);
            setCurrentPage(1);
        });
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    const handlePageChange = useCallback((page: number) => {
        startTransition(() => {
            setCurrentPage(page);
        });
    }, []);

    const handleCardClick = useCallback((filterType: FilterType) => {
        handleFilterChange(filterType);
    }, [handleFilterChange]);

    // Toggle status segment visibility in pie chart
    const handleStatusToggle = useCallback((statusName: string) => {
        setHiddenStatuses(prev => {
            const newSet = new Set(prev);
            if (newSet.has(statusName)) {
                newSet.delete(statusName);
            } else {
                newSet.add(statusName);
            }
            return newSet;
        });
    }, []);

    // Map status name to filter type for chart clicks
    const handleStatusClick = useCallback((statusName: string) => {
        const statusMap: Record<string, FilterType> = {
            'Valid': 'valid',
            'Expiring': 'expiring',
            'Expired': 'expired'
        };
        const filterType = statusMap[statusName];
        if (filterType) {
            handleCardClick(filterType);
        }
    }, [handleCardClick]);

    // Handle click on Validity Trends chart point (expiring in specific month)
    const handleTrendPointClick = useCallback((data: { year?: number; monthNum?: number; weekStart?: string; weekEnd?: string; granularity?: string }) => {
        if (data.granularity === 'weekly' && data.weekStart && data.weekEnd) {
            // "expiring-range::START::END" - use :: to avoid conflict with SWR key | separator
            const filterStr = `expiring-range::${data.weekStart}::${data.weekEnd}`;
            handleCardClick(filterStr);
        } else if (data.year && data.monthNum) {
            const filterStr = `expiring-month-${data.year}-${data.monthNum.toString().padStart(2, '0')}`;
            handleCardClick(filterStr);
        }
    }, [handleCardClick]);

    // Handle click on Issuance Timeline chart point (issued or expired in specific month)
    const handleTimelinePointClick = useCallback((data: { year?: number; monthNum?: number }, type: 'issued' | 'expired') => {
        if (data.year && data.monthNum) {
            const filterStr = `${type}-month-${data.year}-${data.monthNum.toString().padStart(2, '0')}`;
            handleCardClick(filterStr);
        }
    }, [handleCardClick]);

    const getTableTitle = () => {
        // Handle dynamic filter patterns
        if (filter.startsWith('expiring-range::')) {
            const parts = filter.split('::');
            const startStr = parts[1];
            const endStr = parts[2];
            try {
                const startDate = new Date(startStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
                const endDate = new Date(endStr).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
                return `Certificates Expiring: ${startDate} - ${endDate}`;
            } catch {
                return 'Certificates Expiring in Selected Week';
            }
        }
        if (filter.startsWith('expiring-month-')) {
            const dateStr = filter.replace('expiring-month-', '');
            const [year, month] = dateStr.split('-').map(Number);
            const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            return `Certificates Expiring in ${monthNames[month]} ${year}`;
        }
        if (filter.startsWith('issued-month-')) {
            const dateStr = filter.replace('issued-month-', '');
            const [year, month] = dateStr.split('-').map(Number);
            const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            return `Certificates Issued in ${monthNames[month]} ${year}`;
        }
        if (filter.startsWith('expired-month-')) {
            const dateStr = filter.replace('expired-month-', '');
            const [year, month] = dateStr.split('-').map(Number);
            const monthNames = ['', 'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
            return `Certificates Expired in ${monthNames[month]} ${year}`;
        }
        switch (filter) {
            case 'expiring30': return 'Certificates Expiring in 30 Days';
            case 'expiring90': return 'Certificates Expiring in 90 Days';
            case 'longest': return 'Longest Validity Certificates';
            case 'shortest': return 'Shortest Validity Certificates';
            case 'avgDuration': return 'Certificates by Duration';
            case 'compliant': return 'Compliant Certificates (≤398 days)';
            case 'valid': return 'Valid Certificates';
            case 'expiring': return 'Expiring Certificates';
            case 'expired': return 'Expired Certificates';
            case 'bucket-0-90': return 'Certificates with <90 Days Validity';
            case 'bucket-90-365': return 'Certificates with 90 days - 1 Year Validity';
            case 'bucket-365-730': return 'Certificates with 1-2 Years Validity';
            case 'bucket-730+': return 'Certificates with >2 Years Validity';
            default: return 'All Certificates';
        }
    };

    const statusBreakdown = [
        { name: 'Valid', value: (metrics?.activeCertificates.count || 0) - (metrics?.expiringSoon.count || 0), color: STATUS_COLORS.valid },
        { name: 'Expiring', value: metrics?.expiringSoon.count || 0, color: STATUS_COLORS.expiring },
        { name: 'Expired', value: metrics?.expiredCertificates?.count || 0, color: STATUS_COLORS.expired },
    ];

    // Filter out hidden statuses for pie chart display
    const visibleStatusBreakdown = statusBreakdown.filter(item => !hiddenStatuses.has(item.name));

    const totalCerts = metrics?.activeCertificates.total || validityStats?.totalCertificates || 0;

    // Use raw trends data (forecast feature removed as it was hardcoded)
    const trendsData = validityTrends || [];

    if (isStatsLoading && !validityStats) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading validity analysis...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Validity Analysis</h1>
                <p className="text-text-muted mt-1">Certificate validity periods and expiration insights</p>
            </div>

            {/* Top 4 Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={`${validityStats?.averageValidityDays || 0} days`}
                    label="Avg Validity Duration"
                    infoTooltip={cardInfoTooltips.avgDuration}
                />

                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={(validityStats?.expiring30Days || 0).toLocaleString()}
                    label="Expiring <30 Days"
                    badge={{ text: 'Action Needed', variant: 'error' }}
                    onClick={() => handleCardClick('expiring30')}
                    infoTooltip={cardInfoTooltips.expiring30}
                />

                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-orange" />}
                    iconBgColor="bg-accent-orange/15"
                    value={(validityStats?.expiring90Days || 0).toLocaleString()}
                    label="Expiring <90 Days"
                    onClick={() => handleCardClick('expiring90')}
                    infoTooltip={cardInfoTooltips.expiring90}
                />

                <MetricCard
                    icon={<CheckCircleIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={`${validityStats?.complianceRate || 0}%`}
                    label="Compliance Rate"
                    infoTooltip={cardInfoTooltips.complianceRate}
                />
            </div>

            {/* Validity Trends Card */}
            <Card title="Validity Trends Over Time" subtitle="Certificate expirations by months" infoTooltip="Shows certificate expiration trends over time. Click on data points to filter the table. Toggle between monthly and weekly views.">
                <div className="mb-4 flex items-center justify-between flex-wrap gap-4">
                    <div className="flex items-center gap-4">
                        <span className="text-sm text-text-muted">Total Expirations: {validityTrends?.reduce((sum, t) => sum + t.expirations, 0) || 0}</span>
                    </div>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setGranularity('monthly')}
                            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${granularity === 'monthly'
                                ? 'bg-primary-blue text-white'
                                : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                }`}
                        >
                            Monthly
                        </button>
                        <button
                            onClick={() => setGranularity('weekly')}
                            className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${granularity === 'weekly'
                                ? 'bg-primary-blue text-white'
                                : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                }`}
                        >
                            Weekly
                        </button>
                    </div>
                </div>
                <div className="h-72">
                    {isTrendsLoading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-text-muted">Loading trends...</div>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={trendsData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                    labelStyle={{ color: '#f3f4f6' }}
                                />
                                <defs>
                                    <linearGradient id="expirationGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#ef4444" stopOpacity={0.2} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="expirations"
                                    stroke="#f59e0b"
                                    fill="url(#expirationGradient)"
                                    strokeWidth={2}
                                    activeDot={{ r: 8, style: { cursor: 'pointer' }, onClick: (_: unknown, e: { payload?: { year?: number; monthNum?: number; } }) => e.payload && handleTrendPointClick(e.payload) }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </Card>

            {/* Middle Row */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card title="Validity Period Distribution" infoTooltip="Distribution of certificates by their validity period length. Click on a bar to filter the table to that validity range.">
                    <div className="space-y-4">
                        {isDistLoading ? (
                            <div className="h-48 flex items-center justify-center">
                                <div className="text-text-muted">Loading distribution...</div>
                            </div>
                        ) : (
                            distribution?.map((item, index) => {
                                // Map distribution range to bucket filter
                                const bucketMap: Record<string, FilterType> = {
                                    '< 90 Days': 'bucket-0-90',
                                    '90 Days - 1 Year': 'bucket-90-365',
                                    '1 - 2 Years': 'bucket-365-730',
                                    '> 2 Years': 'bucket-730+'
                                };
                                const bucketFilter = bucketMap[item.range] || 'all';

                                return (
                                    <div
                                        key={index}
                                        className="space-y-2 cursor-pointer hover:bg-card-border/30 p-2 -mx-2 rounded-lg transition-colors"
                                        onClick={() => handleCardClick(bucketFilter)}
                                    >
                                        <div className="flex justify-between text-sm">
                                            <span className="text-text-secondary">{item.range}</span>
                                            <span className="text-text-primary font-medium">{item.count.toLocaleString()} ({item.percentage}%)</span>
                                        </div>
                                        <div className="h-3 bg-card-border rounded-full overflow-hidden">
                                            <div
                                                className="h-full rounded-full transition-all duration-500"
                                                style={{
                                                    width: `${item.percentage}%`,
                                                    backgroundColor: item.color
                                                }}
                                            />
                                        </div>
                                    </div>
                                );
                            })
                        )}
                    </div>
                </Card>

                <Card title="Certificate Status Breakdown" infoTooltip="Distribution of certificates by status. Click legend items to toggle visibility. Double-click to filter the table by that status.">
                    <div className="flex items-center justify-center h-64">
                        <div className="flex items-center gap-8">
                            <div className="relative">
                                <ResponsiveContainer width={180} height={180}>
                                    <PieChart>
                                        <Pie
                                            data={visibleStatusBreakdown}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={50}
                                            outerRadius={80}
                                            paddingAngle={2}
                                            dataKey="value"
                                            onClick={(data) => handleStatusClick(data.name)}
                                            style={{ cursor: 'pointer' }}
                                        >
                                            {visibleStatusBreakdown.map((entry, index) => (
                                                <Cell key={`cell-${index}`} fill={entry.color} />
                                            ))}
                                        </Pie>
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                                <div className="absolute inset-0 flex flex-col items-center justify-center">
                                    <span className="text-2xl font-bold text-text-primary">{totalCerts.toLocaleString()}</span>
                                    <span className="text-xs text-text-muted">TOTAL CERTS</span>
                                </div>
                            </div>
                            <div className="space-y-3">
                                {statusBreakdown.map((item, index) => {
                                    const isHidden = hiddenStatuses.has(item.name);
                                    return (
                                        <div
                                            key={index}
                                            className={`flex items-center gap-3 cursor-pointer p-1 -mx-1 rounded transition-colors hover:bg-card-border/30 ${isHidden ? 'opacity-40' : ''}`}
                                            onClick={(e) => {
                                                e.stopPropagation();
                                                handleStatusToggle(item.name);
                                            }}
                                            onDoubleClick={() => handleStatusClick(item.name)}
                                            title={`Click to ${isHidden ? 'show' : 'hide'} in chart, double-click to filter table`}
                                        >
                                            <div
                                                className={`w-3 h-3 rounded-full transition-opacity ${isHidden ? 'opacity-40' : ''}`}
                                                style={{ backgroundColor: item.color }}
                                            />
                                            <span className={`text-text-secondary text-sm ${isHidden ? 'line-through' : ''}`}>{item.name}</span>
                                            <span className="text-text-primary font-semibold ml-auto">{item.value.toLocaleString()}</span>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Issuance Timeline */}
            <Card
                title="Certificate Issuance Timeline"
                subtitle="Volume of certificates issued vs expiring over the last 12 months"
                infoTooltip="Historical view of certificate issuance and expiration trends. Click on data points to filter the table by that month."
            >
                <div className="h-72">
                    {isTimelineLoading ? (
                        <div className="flex items-center justify-center h-full">
                            <div className="text-text-muted">Loading timeline...</div>
                        </div>
                    ) : (
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={timeline} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                                <YAxis stroke="#9ca3af" fontSize={12} />
                                <Tooltip
                                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                    labelStyle={{ color: '#f3f4f6' }}
                                />
                                <Legend />
                                <defs>
                                    <linearGradient id="issuedGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0.1} />
                                    </linearGradient>
                                    <linearGradient id="expiringGradient" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                                        <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1} />
                                    </linearGradient>
                                </defs>
                                <Area
                                    type="monotone"
                                    dataKey="issued"
                                    name="Issued"
                                    stroke="#3b82f6"
                                    fill="url(#issuedGradient)"
                                    strokeWidth={2}
                                    activeDot={{ r: 8, style: { cursor: 'pointer' }, onClick: (_: unknown, e: { payload?: { year?: number; monthNum?: number; } }) => e.payload && handleTimelinePointClick(e.payload, 'issued') }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="expiring"
                                    name="Expiring"
                                    stroke="#f59e0b"
                                    fill="url(#expiringGradient)"
                                    strokeWidth={2}
                                    activeDot={{ r: 8, style: { cursor: 'pointer' }, onClick: (_: unknown, e: { payload?: { year?: number; monthNum?: number; } }) => e.payload && handleTimelinePointClick(e.payload, 'expired') }}
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    )}
                </div>
            </Card>

            {/* Certificates Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    subtitle="Detailed list of all certificates sortable by validity duration"
                    infoTooltip="View and filter certificates by validity status. Use quick filters or click chart elements to refine results."
                    headerAction={
                        <div className="flex items-center gap-3">
                            <div className="flex gap-2">
                                {(['all', 'expiring30', 'expiring90'] as const).map((f) => (
                                    <button
                                        key={f}
                                        onClick={() => handleFilterChange(f)}
                                        className={`px-3 py-1.5 text-xs rounded-lg transition-colors ${filter === f
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-card-bg text-text-secondary border border-card-border hover:bg-card-border'
                                            }`}
                                    >
                                        {f === 'all' ? 'All' : f === 'expiring30' ? '30 Days' : '90 Days'}
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
                                onRowClick={(entry) => console.log('Row clicked:', entry)}
                            />
                        )}
                    </div>
                </Card>
            </div>

            {/* Download Modal - Pass correct active filter based on current filter state */}
            <DownloadModal
                isOpen={downloadModalOpen}
                onClose={() => setDownloadModalOpen(false)}
                currentPageData={tableData}
                activeFilter={(() => {
                    // Helper to map current filter string to ActiveFilter object
                    if (filter === 'all') return { type: 'all' };
                    if (filter === 'valid') return { type: 'active' }; // Map valid to active
                    if (filter === 'expiring') return { type: 'expiringSoon' }; // Map expiring to expiringSoon
                    if (filter === 'expired') return { type: 'expired' };
                    if (filter === 'expiring30') return { type: 'expiringDays', value: '30' };
                    if (filter === 'expiring90') return { type: 'expiringDays', value: '90' };

                    if (filter.startsWith('bucket-')) {
                        return { type: 'bucket', value: filter.replace('bucket-', '') };
                    }
                    if (filter.startsWith('expiring-month-')) {
                        return { type: 'expiringMonth', value: filter.replace('expiring-month-', '') };
                    }
                    if (filter.startsWith('expiring-range::')) {
                        return { type: 'expiringRange', value: filter.replace('expiring-range::', '') };
                    }
                    if (filter.startsWith('issued-month-')) {
                        return { type: 'issuedMonth', value: filter.replace('issued-month-', '') };
                    }
                    if (filter.startsWith('expired-month-')) {
                        return { type: 'expiredMonth', value: filter.replace('expired-month-', '') };
                    }

                    // Fallback
                    return { type: 'all', value: filter };
                })()}
                totalCount={totalItems}
            />
        </div>
    );
}
