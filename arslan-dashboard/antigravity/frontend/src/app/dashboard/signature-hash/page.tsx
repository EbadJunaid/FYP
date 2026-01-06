'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import ProgressBar from '@/components/charts/ProgressBar';
import { CertificateIcon, KeyIcon, SignatureIcon } from '@/components/icons/Icons';
import { fetchPageData, generateChartData, generatePageMetrics } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function SignatureHashPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [hashData, setHashData] = useState<ReturnType<typeof generateChartData>>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('signature-hash');
            setMetrics(data.metrics);
            setHashData(generateChartData('signature-hash'));
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
                <h1 className="text-2xl font-bold text-text-primary">Signature & Hash</h1>
                <p className="text-text-muted mt-1">Certificate signature algorithm and hash analysis</p>
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
                    icon={<SignatureIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value="SHA-256"
                    label="Most Common Hash"
                />
                <MetricCard
                    icon={<KeyIcon className="w-6 h-6 text-accent-red" />}
                    iconBgColor="bg-accent-red/15"
                    value={`${Math.floor(Math.random() * 5) + 1}%`}
                    label="Deprecated (SHA-1)"
                    badge={{ text: 'Warning', variant: 'warning' }}
                />
            </div>

            {/* Hash Distribution */}
            <Card title="Hash Algorithm Distribution">
                <div className="space-y-4">
                    {(hashData as Array<{ name: string; percentage: number; color: string }>).map((hash) => (
                        <ProgressBar
                            key={hash.name}
                            value={hash.percentage}
                            maxValue={100}
                            label={hash.name}
                            valueLabel={`${hash.percentage}%`}
                            color={hash.name.includes('SHA-1') ? 'bg-accent-red' :
                                hash.name.includes('256') ? 'bg-accent-green' :
                                    hash.name.includes('384') ? 'bg-primary-blue' : 'bg-primary-purple'}
                            height="md"
                        />
                    ))}
                </div>
            </Card>

            {/* Table */}
            <Card title="Certificates by Hash Algorithm">
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
