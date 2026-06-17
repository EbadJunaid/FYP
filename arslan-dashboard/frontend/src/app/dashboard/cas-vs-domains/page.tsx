'use client';

import React, { useEffect, useRef, useState } from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import ProgressBar from '@/components/charts/ProgressBar';
import SmallSearchInput from '@/components/SmallSearchInput';
import { ShieldIcon, CertificateIcon, CloseIcon } from '@/components/icons/Icons';
import { fetchCertificates } from '@/controllers/pageController';
import apiClient, { CALeaderboardEntry } from '@/services/apiClient';
import { ScanEntry } from '@/types/dashboard';
import { useSearch } from '@/context/SearchContext';

export default function CAsPage() {
    const [tableData, setTableData] = useState<ScanEntry[]>([]);
    const [caData, setCAData] = useState<CALeaderboardEntry[]>([]);
    const [selectedCA, setSelectedCA] = useState<CALeaderboardEntry | null>(null);
    const [metrics, setMetrics] = useState<{ total: number; cas: number; topCA: string } | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [totalCerts, setTotalCerts] = useState(0);
    const [windowStart, setWindowStart] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [hasRestoredState, setHasRestoredState] = useState(false);
    const savedStateRef = useRef<{
        selectedCAName?: string;
        currentPage?: number;
        windowStart?: number;
        searchQuery?: string;
        scrollY?: number;
    } | null>(null);
    const itemsPerPage = 10;
    const WINDOW_SIZE = 20;
    const isOnlyOnePage = caData.length <= WINDOW_SIZE;
    const maxWindowStart = Math.max(0, caData.length - WINDOW_SIZE);
    const isFirstPage = windowStart === 0;
    const isLastPage = windowStart >= maxWindowStart;
    const normalizeSearch = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '');
    const normalizedSearch = normalizeSearch(searchQuery);
    const searchedCAData = normalizedSearch
        ? caData.filter((ca) => normalizeSearch(ca.name).includes(normalizedSearch))
        : [];
    const hasSearch = normalizedSearch.length > 0;
    const pagedCAData = hasSearch
        ? searchedCAData
        : caData.slice(windowStart, Math.min(windowStart + WINDOW_SIZE, caData.length));
    const displayedCAData = pagedCAData;
    const totalVisibleCAs = displayedCAData.length;
    const tableRef = React.useRef<HTMLDivElement>(null);
    const caSearchRef = React.useRef<HTMLInputElement>(null);
    const { searchQuery: globalSearchQuery } = useSearch();

    // Load initial CA distribution
    useEffect(() => {
        try {
            const saved = sessionStorage.getItem('cas-page-state');
            if (saved) {
                savedStateRef.current = JSON.parse(saved);
                sessionStorage.removeItem('cas-page-state');
            }
        } catch (error) {
            console.error('Error loading saved CA page state:', error);
        }
    }, []);

    useEffect(() => {
        const loadCAData = async () => {
            setIsLoading(true);
            try {
                // Fetch all CAs (no limit) from the API
                const caDistribution = await apiClient.getCAAnalytics(99999); // Large number to get all CAs
                const caStats = await apiClient.getCAStats();

                setMetrics({
                    total: caStats.total_certs,
                    cas: caStats.total_cas,
                    topCA: caStats.top_ca?.name || 'N/A',
                });

                setCAData(caDistribution);

                const savedState = savedStateRef.current;
                if (savedState && caDistribution.length > 0) {
                    const restoredCA = caDistribution.find((ca) => ca.name === savedState.selectedCAName) || caDistribution[0];
                    setSelectedCA(restoredCA);
                    setCurrentPage(savedState.currentPage || 1);
                    setWindowStart(savedState.windowStart ?? 0);
                    setSearchQuery(savedState.searchQuery ?? '');
                    if (savedState.scrollY !== undefined && savedState.scrollY !== null) {
                        setTimeout(() => {
                            window.scrollTo(0, savedState.scrollY as number);
                        }, 100);
                    }
                    setHasRestoredState(true);
                } else if (caDistribution.length > 0 && !selectedCA) {
                    setSelectedCA(caDistribution[0]);
                }
            } catch (error) {
                console.error('Error loading CA data:', error);
            }
            setIsLoading(false);
        };
        loadCAData();
    }, []);

    useEffect(() => {
        setWindowStart(0);
    }, [caData.length]);

    // Load certificates when CA selection or page changes
    useEffect(() => {
        const loadCertificates = async () => {
            setIsLoading(true);
            try {
                const result = await fetchCertificates({
                    page: currentPage,
                    pageSize: itemsPerPage,
                    issuer: selectedCA?.name,
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
        if (selectedCA) {
            loadCertificates();
        }
    }, [selectedCA, currentPage, globalSearchQuery]);

    // When global header search changes, reset to first page
    useEffect(() => {
        if (globalSearchQuery) {
            setCurrentPage(1);
        }
    }, [globalSearchQuery]);

    // Shortcut: Ctrl+Shift+K focuses the CA search input on this page
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'k') {
                e.preventDefault();
                caSearchRef.current?.focus();
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, []);

    // Handle CA selection
    const handleCAClick = (ca: CALeaderboardEntry) => {
        setSelectedCA(ca);
        setCurrentPage(1);
        
        setTimeout(() => {
            tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    };

    const handleTableRowClick = (entry: ScanEntry) => {
        try {
            const stateToSave = {
                selectedCAName: selectedCA?.name,
                currentPage,
                windowStart,
                searchQuery,
                scrollY: window.scrollY,
            };
            sessionStorage.setItem('cas-page-state', JSON.stringify(stateToSave));
        } catch (error) {
            console.error('Error saving CA page state:', error);
        }
    };

    const handleHideAllCAs = () => {
        setWindowStart(0);
    };

    const handleHide100CAs = () => {
        setWindowStart((prev) => Math.max(prev - WINDOW_SIZE, 0));
    };

    const handleShow100CAs = () => {
        const maxStart = Math.max(0, caData.length - WINDOW_SIZE);
        setWindowStart((prev) => Math.min(prev + WINDOW_SIZE, maxStart));
    };

    const handleTablePageChange = (page: number) => {
        setCurrentPage(page);
    };

    // Clear CA filter - go back to top CA
    const handleClearFilter = () => {
        if (caData.length > 0) {
            setSelectedCA(caData[0]);
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
                <h1 className="text-2xl font-bold text-text-primary">Certificate Authorities</h1>
                <p className="text-text-muted mt-1">
                    Distribution and analysis of Certificate Authorities
                    {selectedCA && (
                        <span className="ml-2 text-primary-blue">
                            • Filtered by: {selectedCA.name}
                        </span>
                    )}
                </p>
            </div>

            {/* Metrics Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={selectedCA ? totalCerts.toLocaleString() : metrics?.total?.toLocaleString() || '0'}
                    label={selectedCA ? `Certificates from ${selectedCA.name}` : "Total Certificates"}
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={metrics?.cas || caData.length}
                    label="Certificate Authorities"
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={selectedCA ? `${selectedCA.percentage}%` : metrics?.topCA || 'N/A'}
                    label={selectedCA ? "Percentage" : "Top CA"}
                />
            </div>

            {/* CA Distribution */}
            <Card
                title="CA Market Share"
                subtitle={`Click on a CA to filter certificates · Showing ${totalVisibleCAs} of ${caData.length} CAs${hasSearch ? ` matching "${searchQuery}"` : ''}`}
                headerAction={
                    <SmallSearchInput
                        ref={caSearchRef}
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        placeholder="Search CA"
                    />
                }
            >
                {displayedCAData.length > 0 ? (
                    <div className="space-y-4">
                        {displayedCAData.map((ca, index) => {
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
                                <div 
                                    key={ca.id}
                                    onClick={() => handleCAClick(ca)}
                                    className="cursor-pointer transition-all duration-200 hover:bg-background/30 rounded-lg p-1 -m-1"
                                >
                                    <ProgressBar
                                        value={ca.percentage}
                                        maxValue={100}
                                        label={`${ca.name} (${ca.count.toLocaleString()} certs)`}
                                        valueLabel={`${ca.percentage}%`}
                                        color={colors[index % colors.length]}
                                        height="md"
                                    />
                                </div>
                            );
                        })}
                    </div>
                ) : (
                    <div className="py-10 text-center text-text-muted">No CA found.</div>
                )}

                <div className="mt-4 border-t border-border pt-4">
                    <div className="flex flex-wrap justify-center gap-4 w-full">
                        <button
                            onClick={handleHideAllCAs}
                            disabled={hasSearch || isFirstPage || isOnlyOnePage}
                            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${hasSearch || isFirstPage || isOnlyOnePage ? 'border-border bg-surface text-text-muted cursor-not-allowed' : 'border-border bg-background text-text-primary hover:bg-background/80'}`}
                        >
                            Move to Start
                        </button>
                        <button
                            onClick={handleHide100CAs}
                            disabled={hasSearch || isFirstPage || isOnlyOnePage}
                            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${hasSearch || isFirstPage || isOnlyOnePage ? 'border-border bg-surface text-text-muted cursor-not-allowed' : 'border-border bg-background text-text-primary hover:bg-background/80'}`}
                        >
                            Previous 20
                        </button>
                        <button
                            onClick={handleShow100CAs}
                            disabled={hasSearch || isOnlyOnePage || isLastPage}
                            className={`inline-flex items-center gap-2 rounded-full border px-4 py-2 text-sm font-medium transition ${hasSearch || isOnlyOnePage || isLastPage ? 'border-border bg-surface text-text-muted cursor-not-allowed' : 'border-border bg-background text-text-primary hover:bg-background/80'}`}
                        >
                            Next 20
                        </button>
                    </div>
                </div>
            </Card>

            {/* Table */}
            <div ref={tableRef}>
                <Card 
                    title={selectedCA ? `Certificates from ${selectedCA.name}` : "Certificates"}
                    subtitle={
                        selectedCA && selectedCA.name !== caData[0]?.name ? (
                            <button
                                onClick={handleClearFilter}
                                className="flex items-center gap-1 text-sm text-accent-blue hover:text-accent-blue/80 transition-colors"
                            >
                                <CloseIcon className="w-4 h-4" size={16} />
                                Reset to Top CA
                            </button>
                        ) : undefined
                    }
                >
                <DataTable
                    data={tableData}
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={handleTablePageChange}
                    onRowClick={handleTableRowClick}
                />
                </Card>
            </div>
        </div>
    );
}
