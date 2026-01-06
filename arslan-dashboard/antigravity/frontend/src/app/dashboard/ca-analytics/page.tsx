'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import ProgressBar from '@/components/charts/ProgressBar';
import { CertificateIcon, GlobeIcon } from '@/components/icons/Icons';
import { fetchPageData, generateCAData, generatePageMetrics } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function CAAnalyticsPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [caData, setCAData] = useState<ReturnType<typeof generateCAData>>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('ca-analytics');
            setMetrics(data.metrics);
            setCAData(generateCAData(8));
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
    const maxCount = Math.max(...caData.map(c => c.count));

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
                <h1 className="text-2xl font-bold text-text-primary">CA Analytics</h1>
                <p className="text-text-muted mt-1">Certificate Authority distribution analysis</p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={metrics?.total?.toLocaleString() || '0'}
                    label="Total Certificates"
                />
                <MetricCard
                    icon={<GlobeIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={(metrics as { uniqueCAs?: number })?.uniqueCAs || caData.length}
                    label="Unique CAs"
                />
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={(metrics as { topCA?: string })?.topCA || caData[0]?.name || 'N/A'}
                    label="Top CA"
                />
            </div>

            {/* CA Distribution */}
            <Card title="Certificate Authority Leaderboard">
                <div className="space-y-4">
                    {caData.map((ca, index) => {
                        const colors = [
                            'bg-primary-blue',
                            'bg-accent-green',
                            'bg-primary-purple',
                            'bg-primary-cyan',
                            'bg-accent-yellow',
                            'bg-accent-pink',
                            'bg-accent-orange',
                            'bg-text-muted',
                        ];
                        return (
                            <ProgressBar
                                key={ca.id}
                                value={ca.count}
                                maxValue={maxCount}
                                label={ca.name}
                                valueLabel={`${ca.certificates} certs`}
                                color={colors[index % colors.length]}
                                height="md"
                            />
                        );
                    })}
                </div>
            </Card>

            {/* Table */}
            <Card title="Certificates by CA">
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
