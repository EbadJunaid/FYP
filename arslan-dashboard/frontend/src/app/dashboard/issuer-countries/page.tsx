'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import ProgressBar from '@/components/charts/ProgressBar';
import { GlobeIcon, CertificateIcon } from '@/components/icons/Icons';
import { fetchGeographicDistribution, fetchCertificates, fetchDashboardMetrics } from '@/controllers/pageController';
import { ScanEntry, GeographicEntry } from '@/types/dashboard';

export default function IssuerCountriesPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [geoData, setGeoData] = useState<GeographicEntry[]>([]);
    const [metrics, setMetrics] = useState<{ total: number; countries: number; topCountry: string } | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const itemsPerPage = 10;

    useEffect(() => {
        const loadData = async () => {
            setIsLoading(true);
            try {
                const [dashboardMetrics, geoDistribution, certificates] = await Promise.all([
                    fetchDashboardMetrics(),
                    fetchGeographicDistribution(10),
                    fetchCertificates({ page: 1, pageSize: 25 }),
                ]);

                setMetrics({
                    total: dashboardMetrics.activeCertificates.count,
                    countries: geoDistribution.length,
                    topCountry: geoDistribution[0]?.country || 'N/A',
                });
                setGeoData(geoDistribution);
                setTableData(certificates.certificates);
            } catch (error) {
                console.error('Error loading geographic data:', error);
            }
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
                <h1 className="text-2xl font-bold text-text-primary">Issuer Countries</h1>
                <p className="text-text-muted mt-1">Geographic distribution of SSL certificates</p>
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
                    value={metrics?.countries || geoData.length}
                    label="Countries"
                />
                <MetricCard
                    icon={<GlobeIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={metrics?.topCountry || 'N/A'}
                    label="Top Country"
                />
            </div>

            {/* Geographic Distribution */}
            <Card title="Issuer Countries Heat Map">
                <div className="space-y-4">
                    {geoData.map((geo, index) => {
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
                                key={geo.id}
                                value={geo.percentage}
                                maxValue={100}
                                label={geo.country}
                                valueLabel={`${geo.percentage}%`}
                                color={colors[index % colors.length]}
                                height="md"
                            />
                        );
                    })}
                </div>
            </Card>

            {/* Table */}
            <Card title="Certificates by Country">
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
