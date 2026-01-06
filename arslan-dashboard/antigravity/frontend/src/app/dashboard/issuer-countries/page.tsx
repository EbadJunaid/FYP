'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import { GlobeIcon, CertificateIcon } from '@/components/icons/Icons';
import { fetchPageData, generateGeographicData, generatePageMetrics } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';

export default function IssuerCountriesPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [geoData, setGeoData] = useState<ReturnType<typeof generateGeographicData>>([]);
    const [metrics, setMetrics] = useState<ReturnType<typeof generatePageMetrics> | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            const data = await fetchPageData('issuer-countries');
            setMetrics(data.metrics);
            setGeoData(generateGeographicData(10));
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

    const colors = [
        'bg-primary-blue',
        'bg-primary-purple',
        'bg-accent-green',
        'bg-accent-yellow',
        'bg-primary-cyan',
        'bg-accent-pink',
        'bg-accent-orange',
        'bg-text-muted',
    ];

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Issuer Countries</h1>
                <p className="text-text-muted mt-1">Geographic distribution of certificate issuers</p>
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
                    value={geoData.length}
                    label="Countries"
                />
                <MetricCard
                    icon={<GlobeIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={geoData[0]?.country || 'N/A'}
                    label="Top Country"
                />
            </div>

            {/* Country Distribution */}
            <Card title="Certificates by Country">
                <div className="space-y-3">
                    {geoData.map((country, index) => (
                        <div key={country.id} className="flex items-center gap-4">
                            <span className="w-8 text-sm font-medium text-text-muted text-right">
                                {index + 1}.
                            </span>
                            <div className="flex-1">
                                <div
                                    className={`h-8 rounded-lg flex items-center px-3 ${colors[index % colors.length]}`}
                                    style={{ width: `${Math.max(country.percentage, 20)}%` }}
                                >
                                    <span className="text-xs font-medium text-white truncate">
                                        {country.country} ({country.percentage}%)
                                    </span>
                                </div>
                            </div>
                            <span className="text-sm text-text-muted w-20 text-right">
                                {country.count} certs
                            </span>
                        </div>
                    ))}
                </div>
            </Card>

            {/* Table */}
            <Card title="Certificates by Location">
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
