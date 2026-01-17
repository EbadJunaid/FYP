'use client';

import React, { useEffect, useState, useRef, useCallback, useTransition } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import { CertificateIcon, ClockIcon, AlertIcon, TrendUpIcon } from '@/components/icons/Icons';
import { fetchDashboardMetrics, fetchCertificates } from '@/controllers/pageController';
import { useSearch } from '@/context/SearchContext';
import { DashboardMetrics, ScanEntry } from '@/types/dashboard';

const STORAGE_KEY = 'overview-state';

// Card info tooltips
const cardInfoTooltips: Record<string, string> = {
    total: 'Total count of all SSL certificates in the database.',
    active: 'Certificates that are currently valid and not yet expired.',
    expiringSoon: 'Certificates expiring within the next 30 days - requires attention.',
    expired: 'Certificates that have passed their expiration date.',
};

// SWR fetchers
const metricsFetcher = () => fetchDashboardMetrics();
const certificatesFetcher = async (key: string) => {
    const parts = key.split('|');
    const page = parseInt(parts[1]) || 1;
    const search = parts[2] || undefined;
    return fetchCertificates({ page, pageSize: 10, search });
};

export default function OverviewPage() {
    const router = useRouter();
    const [currentPage, setCurrentPage] = useState(1);
    const [isRestoring, setIsRestoring] = useState(true);
    const tableRef = useRef<HTMLDivElement>(null);
    const [isPending, startTransition] = useTransition();

    const { searchQuery } = useSearch();

    // Restore state from sessionStorage on mount
    useEffect(() => {
        try {
            const savedState = sessionStorage.getItem(STORAGE_KEY);
            if (savedState) {
                const parsed = JSON.parse(savedState);
                if (parsed.page) setCurrentPage(parsed.page);
                if (parsed.scrollY) {
                    setTimeout(() => window.scrollTo(0, parsed.scrollY), 150);
                }
                // Don't remove - we'll clear after data loads
            }
        } catch (e) {
            console.error('Error restoring page state:', e);
        }
        setIsRestoring(false);
    }, []);

    // SWR for metrics
    const { data: metrics, isLoading: isMetricsLoading } = useSWR<DashboardMetrics>(
        'overview-metrics',
        metricsFetcher,
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    // SWR for certificates with search
    const swrKey = `overview-certs|${currentPage}|${searchQuery || ''}`;
    const { data: certsData, isLoading: isCertsLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = certsData?.certificates || [];
    const totalPages = certsData?.pagination?.totalPages || 1;

    // Clear saved state after data loads successfully
    useEffect(() => {
        if (!isCertsLoading && !isRestoring && tableData.length > 0) {
            sessionStorage.removeItem(STORAGE_KEY);
        }
    }, [isCertsLoading, isRestoring, tableData.length]);

    // Scroll to table on search
    useEffect(() => {
        if (searchQuery) {
            startTransition(() => {
                setCurrentPage(1);
            });
            // Use requestAnimationFrame for better scroll timing after render
            requestAnimationFrame(() => {
                setTimeout(() => {
                    tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }, 100);
            });
        }
    }, [searchQuery]);

    // Handle page change
    const handlePageChange = useCallback((page: number) => {
        startTransition(() => {
            setCurrentPage(page);
        });
    }, []);

    // Handle row click - save state before navigation
    const handleRowClick = useCallback((entry: ScanEntry) => {
        // Save current state before navigating
        const stateToSave = { page: currentPage, scrollY: window.scrollY };
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stateToSave));
        // Navigate to certificate detail
        router.push(`/certificate/${entry.id}`);
    }, [currentPage, router]);

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
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Overview</h1>
                <p className="text-text-muted mt-1">Certificate analysis dashboard overview</p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={metrics?.activeCertificates?.total?.toLocaleString() || '0'}
                    label="Total Certificates"
                    infoTooltip={cardInfoTooltips.total}
                />
                <MetricCard
                    icon={<TrendUpIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={metrics?.activeCertificates?.count?.toLocaleString() || '0'}
                    label="Active Certificates"
                    infoTooltip={cardInfoTooltips.active}
                />
                <MetricCard
                    icon={<ClockIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={metrics?.expiringSoon?.count || 0}
                    label="Expiring Soon"
                    badge={{ text: 'Action Needed', variant: 'warning' }}
                    infoTooltip={cardInfoTooltips.expiringSoon}
                />
                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={metrics?.expiredCertificates?.count || 0}
                    label="Expired"
                    infoTooltip={cardInfoTooltips.expired}
                />
            </div>

            {/* Certificates Table */}
            <div ref={tableRef}>
                <Card title="Certificate Overview">
                    <div className={`transition-opacity duration-200 ${isCertsLoading || isPending ? 'opacity-50' : 'opacity-100'}`}>
                        <DataTable
                            data={tableData}
                            currentPage={currentPage}
                            totalPages={totalPages}
                            onPageChange={handlePageChange}
                            onRowClick={handleRowClick}
                        />
                    </div>
                </Card>
            </div>
        </div>
    );
}
