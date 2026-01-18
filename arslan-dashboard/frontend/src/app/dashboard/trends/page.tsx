'use client';

import React, { useState, useEffect, useRef, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import {
    BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
    XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts';
import { useSearch } from '@/context/SearchContext';
import Card from '@/components/Card';
import MetricCard from '@/components/dashboard/MetricCard';
import DataTable from '@/components/DataTable';
import Pagination from '@/components/Pagination';
import DownloadModal from '@/components/DownloadModal';
import {
    ChartPieIcon, ShieldIcon, ClockIcon, CertificateIcon, AlertIcon, KeyIcon
} from '@/components/icons/Icons';
import apiClient, {
    TrendsStats, ExpirationForecastEntry,
    AlgorithmAdoptionEntry, ValidationLevelTrendsEntry, KeySizeTimelineEntry
} from '@/services/apiClient';
import { fetchCertificates } from '@/controllers/pageController';

const STORAGE_KEY = 'trends-analytics-state';

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    issued30d: 'Number of certificates issued in the last 30 days. Click to view in table.',
    expiring: 'Number of certificates expiring in the next 30 days. Click to view.',
    modernAlgo: 'Percentage of certificates using modern algorithms (SHA256+, ECDSA).',
    strongKeys: 'Percentage of certificates with strong keys (RSA ≥ 2048 or ECDSA ≥ 256 bits).',
};

// Filter types for table
type FilterType = 'all' | 'expiring30d' | 'issued30d' | 'issued_month' | 'expiring_month' | 'algo' | 'validation';

// SWR fetchers
const trendsStatsFetcher = () => apiClient.getTrendsStats();
const expirationForecastFetcher = () => apiClient.getExpirationForecast(12);
const algorithmAdoptionFetcher = () => apiClient.getAlgorithmAdoption(12);
const validationTrendsFetcher = () => apiClient.getValidationLevelTrends(12);
const keySizeTimelineFetcher = () => apiClient.getKeySizeTimeline(12);

// Certificates fetcher with trends filters
const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const filterType = parts[1] as FilterType;
    const filterValue = parts[2] || '';
    const page = parseInt(parts[3]) || 1;
    const search = parts[4] || undefined;

    // Build params based on filter type
    let expiring_days: number | undefined;
    let issued_month: number | undefined;
    let issued_year: number | undefined;
    let expiring_month: number | undefined;
    let expiring_year: number | undefined;
    let issuedWithinDays: number | undefined;

    if (filterType === 'expiring30d') {
        expiring_days = 30;
    } else if (filterType === 'issued30d') {
        issuedWithinDays = 30;
    } else if (filterType === 'issued_month' && filterValue) {
        // filterValue like "2025-11"
        const [year, month] = filterValue.split('-').map(Number);
        if (!isNaN(year) && !isNaN(month)) {
            issued_year = year;
            issued_month = month;
        }
    } else if (filterType === 'expiring_month' && filterValue) {
        // filterValue like "2026-03" for expiration forecast
        const [year, month] = filterValue.split('-').map(Number);
        if (!isNaN(year) && !isNaN(month)) {
            expiring_year = year;
            expiring_month = month;
        }
    }

    return fetchCertificates({
        page,
        pageSize: 10,
        search,
        expiringDays: expiring_days,
        issuedMonth: issued_month,
        issuedYear: issued_year,
        expiringMonth: expiring_month,
        expiringYear: expiring_year,
        issuedWithinDays,
    });
};

// Chart colors
const ALGO_COLORS = {
    sha256_rsa: '#10b981',
    sha384_rsa: '#3b82f6',
    ecdsa: '#8b5cf6',
    sha1_rsa: '#ef4444',
    other: '#6b7280',
};

const VALIDATION_COLORS = {
    dv: '#10b981',
    ov: '#3b82f6',
    ev: '#8b5cf6',
};

export default function TrendsAnalyticsPage() {
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
                const state = JSON.parse(saved);
                if (state.filterType) setFilterType(state.filterType);
                if (state.filterValue) setFilterValue(state.filterValue);
                if (state.currentPage) setCurrentPage(state.currentPage);
            }
        } catch (e) {
            console.error('Failed to restore state:', e);
        }
        setIsRestoring(false);
    }, []);

    // Save state on change
    useEffect(() => {
        if (!isRestoring) {
            try {
                sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                    filterType,
                    filterValue,
                    currentPage,
                }));
            } catch (e) {
                console.error('Failed to save state:', e);
            }
        }
    }, [filterType, filterValue, currentPage, isRestoring]);

    // SWR data fetching
    const { data: trendsStats, isLoading: isStatsLoading } = useSWR('trends-stats', trendsStatsFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 60000,
    });

    const { data: expirationForecast, isLoading: isForecastLoading } = useSWR('expiration-forecast', expirationForecastFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 60000,
    });

    const { data: algorithmAdoption, isLoading: isAlgoLoading } = useSWR('algorithm-adoption', algorithmAdoptionFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 60000,
    });

    const { data: validationTrends, isLoading: isValidationLoading } = useSWR('validation-trends', validationTrendsFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 60000,
    });

    // Key size timeline for animated chart
    const { data: keySizeTimeline, isLoading: isKeySizeLoading } = useSWR('key-size-timeline', keySizeTimelineFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 60000,
    });

    // Animation state for key size distribution chart
    const [animationIndex, setAnimationIndex] = useState(0);
    const [isAnimating, setIsAnimating] = useState(false);
    const animationRef = useRef<NodeJS.Timeout | null>(null);

    // Animation control
    useEffect(() => {
        if (isAnimating && keySizeTimeline && keySizeTimeline.length > 0) {
            animationRef.current = setInterval(() => {
                setAnimationIndex(prev => {
                    if (prev >= keySizeTimeline.length - 1) {
                        setIsAnimating(false);
                        return prev;
                    }
                    return prev + 1;
                });
            }, 800);
        } else {
            if (animationRef.current) {
                clearInterval(animationRef.current);
                animationRef.current = null;
            }
        }
        return () => {
            if (animationRef.current) clearInterval(animationRef.current);
        };
    }, [isAnimating, keySizeTimeline]);

    const toggleAnimation = () => {
        if (!keySizeTimeline || keySizeTimeline.length === 0) return;
        if (isAnimating) {
            setIsAnimating(false);
        } else {
            if (animationIndex >= keySizeTimeline.length - 1) {
                setAnimationIndex(0);
            }
            setIsAnimating(true);
        }
    };

    // Certificates with filters
    const certsKey = isRestoring ? null : `certs|${filterType}|${filterValue}|${currentPage}|${searchQuery}`;
    const { data: certsData, isLoading: isCertsLoading } = useSWR(certsKey, certificatesFetcher, {
        revalidateOnFocus: false,
        dedupingInterval: 30000,
    });

    // Handle card click
    const handleCardClick = (type: FilterType, value: string = '') => {
        startTransition(() => {
            setFilterType(type);
            setFilterValue(value);
            setCurrentPage(1);
            setTimeout(() => {
                tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
        });
    };

    // Page change
    const handlePageChange = (page: number) => {
        setCurrentPage(page);
        tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };

    // Get table title
    const getTableTitle = () => {
        if (filterType === 'expiring30d') return 'Certificates Expiring in 30 Days';
        if (filterType === 'issued30d') return 'Certificates Issued in Last 30 Days';
        if (filterType === 'issued_month' && filterValue) return `Certificates Issued in ${filterValue}`;
        if (filterType === 'expiring_month' && filterValue) return `Certificates Expiring in ${filterValue}`;
        return 'All Certificates';
    };

    // Get active filter for download
    const getActiveFilter = () => {
        if (filterType === 'expiring30d') return { type: 'expiringDays' as const, value: '30' };
        if (filterType === 'issued30d') return { type: 'issuedWithinDays' as const, value: '30' };
        if (filterType === 'issued_month') {
            const [year, month] = filterValue.split('-');
            return { type: 'issuedMonth' as const, value: filterValue, month, year };
        }
        if (filterType === 'expiring_month') {
            const [year, month] = filterValue.split('-');
            return { type: 'expiringMonth' as const, value: filterValue, month, year };
        }
        return { type: 'all' as const, value: '' };
    };

    // Loading state
    if (isStatsLoading && !trendsStats) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading trends data...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6 animate-fadeIn">
            {/* Page Header */}
            <div>
                <h1 className="text-2xl font-semibold text-text-primary">Trends Analytics</h1>
                <p className="text-text-secondary mt-1">Track certificate ecosystem changes over time</p>
            </div>

            {/* Metric Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={trendsStats?.velocity_30d?.toLocaleString() || '0'}
                    label="Issued Certificates (30d)"
                    badge={trendsStats?.velocity_change !== undefined ? {
                        text: `${trendsStats.velocity_change >= 0 ? '+' : ''}${trendsStats.velocity_change}%`,
                        variant: trendsStats.velocity_change >= 0 ? 'success' : 'error'
                    } : undefined}
                    infoTooltip={cardInfoTooltips.issued30d}
                    onClick={() => handleCardClick('issued30d')}
                />
                <MetricCard
                    icon={<ClockIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={trendsStats?.expiring_30d?.toLocaleString() || '0'}
                    label="Expiring Soon (30d)"
                    infoTooltip={cardInfoTooltips.expiring}
                    onClick={() => handleCardClick('expiring30d')}
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={`${trendsStats?.modern_algo_percent || 0}%`}
                    label="Modern Algorithms"
                    infoTooltip={cardInfoTooltips.modernAlgo}
                />
                <MetricCard
                    icon={<KeyIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={`${trendsStats?.strong_key_percent || 0}%`}
                    label="Strong Keys"
                    infoTooltip={cardInfoTooltips.strongKeys}
                />
            </div>

            {/* Charts Row 1 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Expiration Forecast */}
                <Card title="Expiration Forecast" infoTooltip="Certificates expiring in the next 12 months. Click a bar to filter.">
                    <div className="h-72">
                        {isForecastLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={280}>
                                <BarChart data={expirationForecast || []} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} angle={-45} textAnchor="end" height={60} />
                                    <YAxis stroke="#9ca3af" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px' }}
                                        labelStyle={{ color: '#fff' }}
                                    />
                                    <Bar
                                        dataKey="count"
                                        fill="#f59e0b"
                                        radius={[4, 4, 0, 0]}
                                        cursor="pointer"
                                        onClick={(data: unknown) => {
                                            const d = data as { year?: number; monthNum?: number };
                                            if (d?.year && d?.monthNum) {
                                                const value = `${d.year}-${String(d.monthNum).padStart(2, '0')}`;
                                                handleCardClick('expiring_month', value);
                                            }
                                        }}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                {/* Algorithm Adoption */}
                <Card title="Algorithm Adoption Over Time" infoTooltip="Signature algorithm distribution by certificate issuance month.">
                    <div className="h-72">
                        {isAlgoLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={280}>
                                <AreaChart data={algorithmAdoption || []} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} angle={-45} textAnchor="end" height={60} />
                                    <YAxis stroke="#9ca3af" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px' }}
                                        labelStyle={{ color: '#fff' }}
                                    />
                                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                                    <Area type="monotone" dataKey="sha256_rsa" stackId="1" stroke={ALGO_COLORS.sha256_rsa} fill={ALGO_COLORS.sha256_rsa} name="SHA256-RSA" />
                                    <Area type="monotone" dataKey="sha384_rsa" stackId="1" stroke={ALGO_COLORS.sha384_rsa} fill={ALGO_COLORS.sha384_rsa} name="SHA384-RSA" />
                                    <Area type="monotone" dataKey="ecdsa" stackId="1" stroke={ALGO_COLORS.ecdsa} fill={ALGO_COLORS.ecdsa} name="ECDSA" />
                                    <Area type="monotone" dataKey="sha1_rsa" stackId="1" stroke={ALGO_COLORS.sha1_rsa} fill={ALGO_COLORS.sha1_rsa} name="SHA1 (Legacy)" />
                                    <Area type="monotone" dataKey="other" stackId="1" stroke={ALGO_COLORS.other} fill={ALGO_COLORS.other} name="Other" />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>
            </div>

            {/* Charts Row 2 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Validation Level Trends */}
                <Card title="Validation Level Trends" infoTooltip="Distribution of DV, OV, and EV certificates over time.">
                    <div className="h-72">
                        {isValidationLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : (
                            <ResponsiveContainer width="100%" height="100%" minHeight={280}>
                                <AreaChart data={validationTrends || []} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                                    <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} angle={-45} textAnchor="end" height={60} />
                                    <YAxis stroke="#9ca3af" fontSize={12} />
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1a1a2e', border: '1px solid #2a2a3e', borderRadius: '8px' }}
                                        labelStyle={{ color: '#fff' }}
                                    />
                                    <Legend wrapperStyle={{ paddingTop: '10px' }} />
                                    <Area type="monotone" dataKey="dv" stackId="1" stroke={VALIDATION_COLORS.dv} fill={VALIDATION_COLORS.dv} name="DV" />
                                    <Area type="monotone" dataKey="ov" stackId="1" stroke={VALIDATION_COLORS.ov} fill={VALIDATION_COLORS.ov} name="OV" />
                                    <Area type="monotone" dataKey="ev" stackId="1" stroke={VALIDATION_COLORS.ev} fill={VALIDATION_COLORS.ev} name="EV" />
                                </AreaChart>
                            </ResponsiveContainer>
                        )}
                    </div>
                </Card>

                {/* Animated Key Size Distribution */}
                <Card
                    title="Key Size Distribution"
                    infoTooltip="Key size distribution over time. Click play to animate through months."
                    headerAction={
                        <div className="flex items-center gap-3">
                            <span className="text-sm text-text-secondary">
                                {keySizeTimeline?.[animationIndex]?.month || 'Loading...'}
                            </span>
                            <button
                                onClick={toggleAnimation}
                                className="p-2 rounded-full bg-primary-blue/20 hover:bg-primary-blue/30 transition-colors"
                                disabled={!keySizeTimeline || keySizeTimeline.length === 0}
                            >
                                {isAnimating ? (
                                    <svg className="w-4 h-4 text-primary-blue" fill="currentColor" viewBox="0 0 20 20">
                                        <rect x="6" y="4" width="3" height="12" rx="1" />
                                        <rect x="11" y="4" width="3" height="12" rx="1" />
                                    </svg>
                                ) : (
                                    <svg className="w-4 h-4 text-primary-blue" fill="currentColor" viewBox="0 0 20 20">
                                        <path d="M6.3 2.841A1.5 1.5 0 004 4.11v11.78a1.5 1.5 0 002.3 1.269l9.344-5.89a1.5 1.5 0 000-2.538L6.3 2.84z" />
                                    </svg>
                                )}
                            </button>
                        </div>
                    }
                >
                    <div className="h-72">
                        {isKeySizeLoading ? (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">Loading...</div>
                            </div>
                        ) : keySizeTimeline && keySizeTimeline.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <BarChart
                                    data={[
                                        { name: 'RSA-2048', value: keySizeTimeline[animationIndex]?.rsa_2048 || 0, fill: '#3b82f6' },
                                        { name: 'RSA-4096', value: keySizeTimeline[animationIndex]?.rsa_4096 || 0, fill: '#8b5cf6' },
                                        { name: 'ECDSA-256', value: keySizeTimeline[animationIndex]?.ecdsa_256 || 0, fill: '#10b981' },
                                        { name: 'ECDSA-384', value: keySizeTimeline[animationIndex]?.ecdsa_384 || 0, fill: '#f59e0b' },
                                        { name: 'Other', value: keySizeTimeline[animationIndex]?.rsa_other || 0, fill: '#6b7280' },
                                    ]}
                                    layout="vertical"
                                    margin={{ top: 10, right: 30, left: 70, bottom: 10 }}
                                >
                                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" horizontal={false} />
                                    <XAxis type="number" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
                                    <YAxis type="category" dataKey="name" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} width={65} />
                                    <Tooltip
                                        contentStyle={{
                                            backgroundColor: 'var(--bg-secondary)',
                                            border: '1px solid var(--border)',
                                            borderRadius: '8px',
                                        }}
                                        itemStyle={{ color: 'var(--text-primary)' }}
                                        labelStyle={{ color: 'var(--text-secondary)' }}
                                    />
                                    <Bar
                                        dataKey="value"
                                        radius={[0, 4, 4, 0]}
                                        animationDuration={600}
                                        animationEasing="ease-in-out"
                                        isAnimationActive={true}
                                    />
                                </BarChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="flex items-center justify-center h-full">
                                <div className="text-text-muted">No data available</div>
                            </div>
                        )}
                        {/* Timeline slider */}
                        {keySizeTimeline && keySizeTimeline.length > 0 && (
                            <div className="mt-2 px-4">
                                <input
                                    type="range"
                                    min={0}
                                    max={keySizeTimeline.length - 1}
                                    value={animationIndex}
                                    onChange={(e) => {
                                        setIsAnimating(false);
                                        setAnimationIndex(parseInt(e.target.value));
                                    }}
                                    className="w-full accent-primary-blue"
                                />
                            </div>
                        )}
                    </div>
                </Card>
            </div>

            {/* Certificate Table */}
            <div ref={tableRef}>
                <Card
                    title={getTableTitle()}
                    subtitle="Certificates filtered by trends analysis criteria"
                    infoTooltip="View certificates filtered by time-based criteria."
                    headerAction={
                        <div className="flex items-center gap-2">
                            <button
                                onClick={() => handleCardClick('all', '')}
                                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${filterType === 'all'
                                    ? 'bg-primary-blue/20 text-primary-blue'
                                    : 'text-text-secondary hover:text-primary-blue hover:bg-primary-blue/10'
                                    }`}
                            >
                                All
                            </button>
                            <button
                                onClick={() => handleCardClick('expiring30d')}
                                className={`px-3 py-1.5 text-sm font-medium rounded-md transition-colors ${filterType === 'expiring30d'
                                    ? 'bg-accent-yellow/20 text-accent-yellow'
                                    : 'text-text-secondary hover:text-accent-yellow hover:bg-accent-yellow/10'
                                    }`}
                            >
                                Expiring 30d
                            </button>
                            <div className="w-px h-5 bg-border-default mx-1" />
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
                    <div className={`transition-opacity duration-200 ${isCertsLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
                        <DataTable
                            data={certsData?.certificates || []}
                            onRowClick={(row) => router.push(`/dashboard/certificate/${row.id}`)}
                            currentPage={currentPage}
                            totalPages={certsData?.pagination?.totalPages || 1}
                            onPageChange={handlePageChange}
                            showPagination={false}
                        />
                    </div>

                    {certsData?.pagination && certsData.pagination.totalPages > 1 && (
                        <div className="mt-4 flex justify-center">
                            <Pagination
                                currentPage={currentPage}
                                totalPages={certsData.pagination.totalPages}
                                onPageChange={handlePageChange}
                            />
                        </div>
                    )}
                </Card>
            </div>

            <DownloadModal
                isOpen={isDownloadModalOpen}
                onClose={() => setIsDownloadModalOpen(false)}
                currentPageData={certsData?.certificates || []}
                activeFilter={getActiveFilter()}
                totalCount={certsData?.pagination?.total}
            />
        </div>
    );
}
