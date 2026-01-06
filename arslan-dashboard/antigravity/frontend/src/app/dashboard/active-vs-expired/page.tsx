'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import { CertificateIcon, AlertIcon, CheckCircleIcon, ErrorCircleIcon } from '@/components/icons/Icons';
import { fetchPageData, generatePageMetrics } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function ActiveVsExpiredPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [filter, setFilter] = useState<'all' | 'active' | 'expired'>('all');
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('active-vs-expired');
            setMetrics(data.metrics);
            setTableData(data.tableData);
            setIsLoading(false);
        };
        loadData();
    }, []);

    const filteredData = useMemo(() => {
        if (filter === 'all') return tableData;
        if (filter === 'active') return tableData.filter(d => d.status === 'VALID');
        return tableData.filter(d => d.status === 'EXPIRED');
    }, [tableData, filter]);

    const paginatedData = useMemo(() => {
        const start = (currentPage - 1) * itemsPerPage;
        return filteredData.slice(start, start + itemsPerPage);
    }, [filteredData, currentPage]);

    const totalPages = Math.ceil(filteredData.length / itemsPerPage);

    const activeCount = tableData.filter(d => d.status === 'VALID').length;
    const expiredCount = tableData.filter(d => d.status === 'EXPIRED').length;

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
                <h1 className="text-2xl font-bold text-text-primary">Active vs Expired</h1>
                <p className="text-text-muted mt-1">Compare active and expired certificates</p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={tableData.length}
                    label="Total Certificates"
                />
                <MetricCard
                    icon={<CheckCircleIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={activeCount}
                    label="Active"
                    onClick={() => { setFilter('active'); setCurrentPage(1); }}
                />
                <MetricCard
                    icon={<ErrorCircleIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={expiredCount}
                    label="Expired"
                    onClick={() => { setFilter('expired'); setCurrentPage(1); }}
                />
                <MetricCard
                    icon={<AlertIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={`${((activeCount / tableData.length) * 100).toFixed(1)}%`}
                    label="Active Rate"
                />
            </div>

            {/* Filter Tabs */}
            <div className="flex gap-2">
                {(['all', 'active', 'expired'] as const).map((f) => (
                    <button
                        key={f}
                        onClick={() => { setFilter(f); setCurrentPage(1); }}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === f
                                ? 'bg-primary-blue text-white'
                                : 'bg-card-bg text-text-secondary hover:bg-card-border'
                            }`}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            {/* Table */}
            <Card title={`${filter.charAt(0).toUpperCase() + filter.slice(1)} Certificates`}>
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
