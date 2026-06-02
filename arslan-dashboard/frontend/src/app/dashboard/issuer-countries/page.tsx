'use client';

import React, { useEffect, useState } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import ProgressBar from '@/components/charts/ProgressBar';
import { GlobeIcon, CertificateIcon, CloseIcon } from '@/components/icons/Icons';
import { fetchGeographicDistribution, fetchCertificates, fetchDashboardMetrics } from '@/controllers/pageController';
import { ScanEntry, GeographicEntry } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';

const STORAGE_KEY = 'issuer-countries-page-state';

export default function IssuerCountriesPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [geoData, setGeoData] = useState<GeographicEntry[]>([]);
    const [selectedCountry, setSelectedCountry] = useState<GeographicEntry | null>(null);
    const [searchQuery, setSearchQuery] = useState('');
    const [metrics, setMetrics] = useState<{ total: number; countries: number; topCountry: string } | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalCerts, setTotalCerts] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [hasRestoredState, setHasRestoredState] = useState(false);
    const itemsPerPage = 10;
    const tableRef = React.useRef<HTMLDivElement>(null); // Ref for scrolling to table
    const pageSearchRef = React.useRef<HTMLInputElement>(null);
    const { searchQuery: globalSearchQuery } = useSearch();
    const savedStateRef = React.useRef<{ selectedCountryName?: string; currentPage?: number; searchQuery?: string; scrollY?: number } | null>(null);
    const normalizeSearch = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '');
    const normalizedSearch = normalizeSearch(searchQuery);
    const displayedGeoData = normalizedSearch
        ? geoData.filter((geo) => normalizeSearch(geo.country).includes(normalizedSearch))
        : geoData;

    useEffect(() => {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved) {
                savedStateRef.current = JSON.parse(saved);
                sessionStorage.removeItem(STORAGE_KEY);
            }
        } catch (error) {
            console.error('Error restoring issuer countries page state:', error);
        }
    }, []);

    // Load initial geographic distribution
    useEffect(() => {
        const loadGeoData = async () => {
            setIsLoading(true);
            try {
                const [dashboardMetrics, geoDistribution] = await Promise.all([
                    fetchDashboardMetrics(),
                    fetchGeographicDistribution(200), // Get ALL countries (not just 10)
                ]);

                setMetrics({
                    total: dashboardMetrics.activeCertificates.count,
                    countries: geoDistribution.length,
                    topCountry: geoDistribution[0]?.country || 'N/A',
                });
                setGeoData(geoDistribution);
                const savedState = savedStateRef.current;
                if (savedState && geoDistribution.length > 0) {
                    const restoredCountry = geoDistribution.find((geo) => geo.country === savedState.selectedCountryName) || geoDistribution[0];
                    setSelectedCountry(restoredCountry);
                    setCurrentPage(savedState.currentPage || 1);
                    setSearchQuery(savedState.searchQuery || '');
                    if (savedState.scrollY !== undefined && savedState.scrollY !== null) {
                        setTimeout(() => {
                            window.scrollTo(0, savedState.scrollY as number);
                        }, 100);
                    }
                    setHasRestoredState(true);
                } else if (geoDistribution.length > 0) {
                    setSelectedCountry(geoDistribution[0]);
                }
            } catch (error) {
                console.error('Error loading geographic data:', error);
            }
            setIsLoading(false);
        };
        loadGeoData();
    }, []); // Empty dependency - run only once on mount

    // Load certificates when country selection or page changes
    useEffect(() => {
        const loadCertificates = async () => {
            setIsLoading(true);
            try {
                const result = await fetchCertificates({
                    page: currentPage,
                    pageSize: itemsPerPage,
                    country: selectedCountry?.country,  // ⚡ Uses pre-computed IDs!
                    search: globalSearchQuery || undefined,
                });

                setTableData(result.certificates);
                setTotalPages(result.pagination?.totalPages || 1);
                setTotalCerts(result.pagination?.total || 0);
            } catch (error) {
                console.error('Error loading certificates:', error);
            }
            setIsLoading(false);
        };
        loadCertificates();
    }, [selectedCountry, currentPage, globalSearchQuery]);

    // When global header search changes, reset to first page
    useEffect(() => {
        if (globalSearchQuery) {
            setCurrentPage(1);
        }
    }, [globalSearchQuery]);

    // Shortcut: Ctrl+Shift+K focuses the page's country search input
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                pageSearchRef.current?.focus();
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, []);

    // Handle country selection from heat map
    const handleCountryClick = (country: GeographicEntry) => {
        setSelectedCountry(country);
        setCurrentPage(1); // Reset to first page
        
        // Scroll to table smoothly
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    };

    const handleTableRowClick = (entry: ScanEntry) => {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
                selectedCountryName: selectedCountry?.country,
                currentPage,
                searchQuery,
                scrollY: window.scrollY,
            }));
        } catch (error) {
            console.error('Error saving issuer countries page state:', error);
        }
    };

    // Clear country filter - go back to top country
    const handleClearFilter = () => {
        if (geoData.length > 0) {
            setSelectedCountry(geoData[0]); // Reset to top country
        }
        setCurrentPage(1);
    };

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
                <p className="text-text-muted mt-1">
                    Geographic distribution of SSL certificates
                    {selectedCountry && (
                        <span className="ml-2 text-primary-blue">
                            • Filtered by: {selectedCountry.country}
                        </span>
                    )}
                </p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={selectedCountry ? totalCerts.toLocaleString() : metrics?.total?.toLocaleString() || '0'}
                    label={selectedCountry ? `Certificates in ${selectedCountry.country}` : "Total Certificates"}
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
                    value={selectedCountry ? `${selectedCountry.percentage}%` : metrics?.topCountry || 'N/A'}
                    label={selectedCountry ? "Percentage" : "Top Country"}
                />
            </div>

            {/* Geographic Distribution */}
            <Card
                title="Issuer Countries Heat Map"
                subtitle={`Click on a country to filter certificates · Showing ${displayedGeoData.length} of ${geoData.length} countries${normalizedSearch ? ` matching "${searchQuery}"` : ''}`}
                headerAction={
                    <input
                        ref={pageSearchRef}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search country"
                        className="rounded-full border border-border bg-background px-3 py-2 text-sm text-text-primary outline-none transition focus:border-primary-blue focus:ring-2 focus:ring-primary-blue/20"
                    />
                }
            >
                <div className="space-y-4">
                    {displayedGeoData.length > 0 ? (
                        displayedGeoData.map((geo, index) => {
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
                            const isSelected = selectedCountry?.country === geo.country;
                            
                            return (
                                <div 
                                    key={geo.id}
                                    onClick={() => handleCountryClick(geo)}
                                    className="cursor-pointer transition-all duration-200 hover:bg-background/30 rounded-lg p-1 -m-1"
                                >
                                    <ProgressBar
                                        value={geo.percentage}
                                        maxValue={100}
                                        label={`${geo.country} (${geo.count.toLocaleString()} certs)`}
                                        valueLabel={`${geo.percentage}%`}
                                        color={colors[index % colors.length]}
                                        height="md"
                                    />
                                </div>
                            );
                        })
                    ) : (
                        <div className="py-10 text-center text-text-muted">No country found.</div>
                    )}
                </div>
            </Card>

            {/* Table */}
            <div ref={tableRef}>
                <Card 
                    title={selectedCountry ? `Certificates from ${selectedCountry.country}` : "Certificates"}
                    subtitle={
                        selectedCountry && selectedCountry.country !== geoData[0]?.country ? (
                            <button
                                onClick={handleClearFilter}
                                className="flex items-center gap-1 text-sm text-accent-blue hover:text-accent-blue/80 transition-colors"
                            >
                                <CloseIcon className="w-4 h-4" size={16} />
                                Reset to Top Country
                            </button>
                        ) : undefined
                    }
                >
                <DataTable
                    data={tableData}
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={setCurrentPage}
                    onRowClick={handleTableRowClick}
                />
                </Card>
            </div>
        </div>
    );
}
