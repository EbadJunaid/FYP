'use client';

import React, { useState, useCallback, useRef, useTransition, useEffect } from 'react';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import DownloadModal from '@/components/DownloadModal';
import { CertificateIcon, CheckCircleIcon, ErrorCircleIcon, ChartPieIcon } from '@/components/icons/Icons';
import { fetchDashboardMetrics, fetchCertificates } from '@/controllers/pageController';
import { ScanEntry, DashboardMetrics } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';

// Define the filter types for this page
type FilterType = 'all' | 'active' | 'expired';

// Map filter to API status parameter
const filterToStatus: Record<FilterType, string | undefined> = {
    all: undefined,
    active: 'VALID',
    expired: 'EXPIRED',
};

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    total: 'Total count of all SSL certificates in the database, including active, expired, and expiring soon.',
    active: 'Certificates that are currently valid and have not yet reached their expiration date.',
    expired: 'Certificates that have passed their expiration date and are no longer valid.',
    activeRate: 'Percentage of active certificates relative to total certificates - indicates overall certificate health.',
};

// Table titles based on filter
const tableTitles: Record<FilterType, string> = {
    all: 'All Certificates',
    active: 'Active Certificates',
    expired: 'Expired Certificates',
};

// SWR fetcher functions
const metricsFetcher = () => fetchDashboardMetrics();
const certificatesFetcher = async (key: string) => {
    // Parse the key to extract filter, page, and search
    const parts = key.split('|');
    const filter = parts[1] as FilterType;
    const page = parseInt(parts[2]);
    const search = parts[3] || undefined;
    const status = filterToStatus[filter];
    return fetchCertificates({
        page,
        pageSize: 10,
        status,
        search: search || undefined,
    });
};

export default function ActiveVsExpiredPage() {
    const [filter, setFilter] = useState<FilterType>('all');
    const [currentPage, setCurrentPage] = useState(1);
    const [downloadModalOpen, setDownloadModalOpen] = useState(false);
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();
    const [isRestoring, setIsRestoring] = useState(true);

    const STORAGE_KEY = 'active-vs-expired-state';

    // Get search query from context
    const { searchQuery } = useSearch();

    // Restore state from sessionStorage on mount
    useEffect(() => {
        try {
            const savedState = sessionStorage.getItem(STORAGE_KEY);
            if (savedState) {
                const { filter: savedFilter, page: savedPage, scrollY: savedScrollY } = JSON.parse(savedState);
                if (savedFilter) setFilter(savedFilter);
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
            const stateToSave = { filter, page: currentPage, scrollY: window.scrollY };
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
        };

        const handleLinkClick = (e: MouseEvent) => {
            const target = e.target as HTMLElement;
            const link = target.closest('a');
            if (link && link.href && !link.href.includes('active-vs-expired')) {
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

    // SWR for metrics with caching (revalidate every 5 min)
    const { data: metrics, isLoading: isMetricsLoading } = useSWR<DashboardMetrics>(
        'active-vs-expired-metrics',
        metricsFetcher,
        {
            revalidateOnFocus: false,
            dedupingInterval: 300000, // 5 minutes
            revalidateIfStale: true,
        }
    );

    // SWR for table data with unique key including filter, page, and search
    const swrKey = `certificates|${filter}|${currentPage}|${searchQuery || ''}`;
    const { data: tableResult, isLoading: isTableLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        {
            revalidateOnFocus: false,
            dedupingInterval: 60000, // 1 minute for table data
            keepPreviousData: true, // Keep previous data while loading new page
        }
    );

    // Extract table data from SWR result
    const tableData = tableResult?.certificates || [];
    const totalPages = tableResult?.pagination?.totalPages || 1;
    const totalItems = tableResult?.pagination?.total || 0;

    // Handle filter change - with transition to prevent UI blocking
    const handleFilterChange = useCallback((newFilter: FilterType) => {
        startTransition(() => {
            setFilter(newFilter);
            setCurrentPage(1);
        });
        // Scroll to table only on filter change, not pagination
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }, []);

    // Handle page change - NO scroll, just update state
    const handlePageChange = useCallback((page: number) => {
        // Use startTransition to prevent UI jank
        startTransition(() => {
            setCurrentPage(page);
        });
        // DO NOT scroll here - this was causing the scroll-to-top issue
    }, []);

    // Handle card clicks
    const handleCardClick = useCallback((filterType: FilterType) => {
        handleFilterChange(filterType);
    }, [handleFilterChange]);

    // Calculate derived metrics
    const totalCount = metrics?.activeCertificates.total || 0;
    const activeCount = metrics?.activeCertificates.count || 0;
    const expiredCount = metrics?.expiredCertificates?.count || 0;
    const activeRate = totalCount > 0 ? ((activeCount / totalCount) * 100).toFixed(1) : '0.0';

    // Handle download
    const handleDownload = useCallback(() => {
        setDownloadModalOpen(true);
    }, []);

    // Show loading only on initial load
    if (isMetricsLoading && !metrics) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Active vs Expired</h1>
                <p className="text-text-muted mt-1">Compare active and expired certificate status</p>
            </div>

            {/* Metrics Row - 4 Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                {/* Total Certificates */}
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={totalCount.toLocaleString()}
                    label="Total Certificates"
                    onClick={() => handleCardClick('all')}
                    infoTooltip={cardInfoTooltips.total}
                />

                {/* Active Certificates */}
                <MetricCard
                    icon={<CheckCircleIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={activeCount.toLocaleString()}
                    label="Active Certificates"
                    onClick={() => handleCardClick('active')}
                    infoTooltip={cardInfoTooltips.active}
                />

                {/* Expired Certificates */}
                <MetricCard
                    icon={<ErrorCircleIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={expiredCount.toLocaleString()}
                    label="Expired Certificates"
                    onClick={() => handleCardClick('expired')}
                    infoTooltip={cardInfoTooltips.expired}
                />

                {/* Active Rate - Not clickable */}
                <MetricCard
                    icon={<ChartPieIcon className="w-6 h-6 text-accent-purple" />}
                    iconBgColor="bg-accent-purple/15"
                    value={`${activeRate}%`}
                    label="Active Rate"
                    infoTooltip={cardInfoTooltips.activeRate}
                />
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2">
                {(['all', 'active', 'expired'] as const).map((f) => (
                    <button
                        key={f}
                        onClick={() => handleFilterChange(f)}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === f
                            ? 'bg-primary-blue text-white'
                            : 'bg-card-bg text-text-secondary hover:bg-card-border border border-card-border'
                            }`}
                    >
                        {f === 'all' ? 'All' : f.charAt(0).toUpperCase() + f.slice(1)}
                        {filter === f && (
                            <span className="">
                                {/* {totalItems} */}
                            </span>
                        )}
                    </button>
                ))}
            </div>

            {/* Table - use key to prevent remount */}
            <div ref={tableRef}>
                <Card
                    title={tableTitles[filter]}
                    headerAction={
                        <button
                            onClick={handleDownload}
                            className="flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                            </svg>
                            Download
                        </button>
                    }
                >
                    {/* Show loading indicator without unmounting table */}
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

            {/* Download Modal - pass filter correctly for expired */}
            <DownloadModal
                isOpen={downloadModalOpen}
                onClose={() => setDownloadModalOpen(false)}
                currentPageData={tableData}
                activeFilter={{
                    type: filter === 'expired' ? 'expired' : filter === 'active' ? 'active' : 'all',
                    value: filter
                }}
                totalCount={totalItems}
            />
        </div>
    );
}
