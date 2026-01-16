'use client';

import React, { useEffect, useState, useMemo } from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import { TrendUpIcon, ClockIcon, CertificateIcon } from '@/components/icons/Icons';
import { fetchPageData, generateChartData, generatePageMetrics } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function TrendsPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [chartData, setChartData] = useState<ReturnType<typeof generateChartData>>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('trends');
            setMetrics(data.metrics);
            setChartData(generateChartData('trends', 12));
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
                <h1 className="text-2xl font-bold text-text-primary">Trends</h1>
                <p className="text-text-muted mt-1">Certificate trends over time</p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
                    value={`+${Math.floor(Math.random() * 200) + 50}`}
                    label="New This Month"
                />
                <MetricCard
                    icon={<ClockIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={metrics?.expiringSoon || 0}
                    label="Expiring This Month"
                />
            </div>

            {/* Trend Chart */}
            <Card title="Certificate Trend (12 Months)">
                <div className="h-[300px]">
                    <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
                        <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                            <defs>
                                <linearGradient id="colorCerts" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                                </linearGradient>
                                <linearGradient id="colorExpired" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#ef4444" stopOpacity={0.4} />
                                    <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <CartesianGrid strokeDasharray="3 3" stroke="var(--card-border)" />
                            <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                            <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} />
                            <Tooltip
                                contentStyle={{
                                    backgroundColor: 'var(--card-bg)',
                                    border: '1px solid var(--card-border)',
                                    borderRadius: '8px',
                                }}
                            />
                            <Area
                                type="monotone"
                                dataKey="certificates"
                                stroke="#3b82f6"
                                fillOpacity={1}
                                fill="url(#colorCerts)"
                                name="Certificates"
                            />
                            <Area
                                type="monotone"
                                dataKey="expired"
                                stroke="#ef4444"
                                fillOpacity={1}
                                fill="url(#colorExpired)"
                                name="Expired"
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            {/* Table */}
            <Card title="Recent Certificate Activity">
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
