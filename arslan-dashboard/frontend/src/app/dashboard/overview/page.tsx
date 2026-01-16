'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import { CertificateIcon, ClockIcon, AlertIcon, TrendUpIcon } from '@/components/icons/Icons';
import { fetchPageData, generatePageMetrics, generateChartData } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function OverviewPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('overview');
            setMetrics(data.metrics);
            setTableData(data.tableData);
            setIsLoading(false);
        };
        loadData();
    }, []);

    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return tableData.slice(start, start + itemsPerPage);
    }, [tableData, currentPage]);

    const totalPages = Math.ceil(tableData.length / itemsPerPage);

    if (isLoading) {
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
                    value={metrics?.total?.toLocaleString() || '0'}
                    label="Total Certificates"
                    trend={parseFloat(metrics?.trend || '0')}
                />
                <MetricCard
                    icon={<TrendUpIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={metrics?.active?.toLocaleString() || '0'}
                    label="Active Certificates"
                />
                <MetricCard
                    icon={<ClockIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={metrics?.expiringSoon || 0}
                    label="Expiring Soon"
                    badge={{ text: 'Action Needed', variant: 'warning' }}
                />
                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={metrics?.expired || 0}
                    label="Expired"
                />
            </div>

            {/* Recent Scans Table */}
            <Card title="Certificate Overview">
                <DataTable
                    data={paginatedData}
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={setCurrentPage}
                    onRowClick={(entry) => console.log('Row clicked:', entry)}
                />
            </Card>
        </div>
    );
}
