'use client';

import React, { useState } from 'react';
import { ScanEntry } from '@/types/dashboard';
import { DownloadIcon } from '@/components/icons/Icons';

// API base URL for downloads
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

interface ActiveFilter {
    type: 'all' | 'active' | 'expired' | 'expiringSoon' | 'vulnerabilities' | 'ca' | 'geographic' | 'encryption' | 'validityTrend';
    value?: string;
}

interface DownloadModalProps {
    isOpen: boolean;
    onClose: () => void;
    currentPageData: ScanEntry[];
    activeFilter: ActiveFilter;
    totalCount?: number;
}

export default function DownloadModal({
    isOpen,
    onClose,
    currentPageData,
    activeFilter,
    totalCount,
}: DownloadModalProps) {
    const [isDownloading, setIsDownloading] = useState(false);

    if (!isOpen) return null;

    const generateCSV = (data: ScanEntry[]): string => {
        const headers = ['Domain', 'Start Date', 'End Date', 'SSL Grade', 'Encryption', 'Vulnerabilities', 'Issuer', 'Country', 'Status'];
        const rows = data.map(scan => [
            scan.domain,
            scan.scanDate,
            scan.endDate || 'N/A',
            scan.sslGrade,
            scan.encryptionType || 'Unknown',
            scan.vulnerabilities,
            scan.issuer,
            scan.country || 'Unknown',
            scan.status
        ]);

        return [headers, ...rows]
            .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            .join('\n');
    };

    const downloadCSV = (csvContent: string, filename: string) => {
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    };

    const handleDownloadThisPage = () => {
        const csvContent = generateCSV(currentPageData);
        downloadCSV(csvContent, `ssl-certificates-page-${new Date().toISOString().split('T')[0]}.csv`);
        onClose();
    };

    const buildDownloadUrl = (): string => {
        const params = new URLSearchParams();

        // Map activeFilter to backend query params
        switch (activeFilter.type) {
            case 'active':
                params.append('status', 'VALID');
                break;
            case 'expired':
                params.append('status', 'EXPIRED');
                break;
            case 'expiringSoon':
                params.append('status', 'EXPIRING_SOON');
                break;
            case 'vulnerabilities':
                params.append('has_vulnerabilities', 'true');
                break;
            case 'ca':
                if (activeFilter.value) {
                    params.append('issuer', activeFilter.value);
                }
                break;
            case 'geographic':
                if (activeFilter.value) {
                    params.append('country', activeFilter.value);
                }
                break;
            case 'encryption':
                if (activeFilter.value) {
                    params.append('encryption_type', activeFilter.value);
                }
                break;
            case 'validityTrend':
                if (activeFilter.value) {
                    // Parse month/year from value like "Jan 2026"
                    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
                    const parts = activeFilter.value.split(' ');
                    const monthName = parts[0];
                    const year = parseInt(parts[1] || '2026');
                    const monthIndex = monthNames.indexOf(monthName) + 1;
                    if (monthIndex > 0) {
                        params.append('expiring_month', monthIndex.toString());
                        params.append('expiring_year', year.toString());
                    }
                }
                break;
            case 'all':
            default:
                // No filter params = all certificates
                break;
        }

        const queryString = params.toString();
        return `${API_BASE_URL}/certificates/download/${queryString ? `?${queryString}` : ''}`;
    };

    const handleDownloadAll = async () => {
        setIsDownloading(true);
        try {
            // Trigger browser download by navigating to the streaming endpoint
            const downloadUrl = buildDownloadUrl();
            window.location.href = downloadUrl;

            // Small delay to allow download to start
            await new Promise(resolve => setTimeout(resolve, 1000));
        } finally {
            setIsDownloading(false);
            onClose();
        }
    };

    const getFilterDescription = (): string => {
        switch (activeFilter.type) {
            case 'active':
                return 'All active certificates';
            case 'expiringSoon':
                return 'Certificates expiring soon';
            case 'vulnerabilities':
                return 'Certificates with vulnerabilities';
            case 'ca':
                return activeFilter.value === 'Others'
                    ? 'Other CAs certificates'
                    : `${activeFilter.value || 'CA'} certificates`;
            case 'geographic':
                return `${activeFilter.value || 'Country'} certificates`;
            case 'encryption':
                return `${activeFilter.value || 'Encryption'} certificates`;
            case 'validityTrend':
                return `Certificates expiring ${activeFilter.value || 'in selected month'}`;
            case 'all':
            default:
                return 'All certificates in database';
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-card-bg border border-card-border rounded-2xl p-6 w-full max-w-md shadow-2xl">
                {/* Header */}
                <div className="flex items-center gap-3 mb-6">
                    <div className="w-10 h-10 rounded-xl bg-primary-blue/15 flex items-center justify-center">
                        <DownloadIcon className="w-5 h-5 text-primary-blue" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-text-primary">Download Certificates</h3>
                        <p className="text-sm text-text-muted">Choose download option</p>
                    </div>
                </div>

                {/* Options */}
                <div className="space-y-3 mb-6">
                    <button
                        onClick={handleDownloadThisPage}
                        className="w-full p-4 rounded-xl border border-card-border bg-background hover:bg-card-bg transition-colors text-left group"
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium text-text-primary group-hover:text-primary-blue transition-colors">This Page Only</p>
                                <p className="text-sm text-text-muted">{currentPageData.length} certificates</p>
                            </div>
                            <svg className="w-5 h-5 text-text-muted group-hover:text-primary-blue transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                            </svg>
                        </div>
                    </button>

                    <button
                        onClick={handleDownloadAll}
                        disabled={isDownloading}
                        className="w-full p-4 rounded-xl border border-primary-blue/30 bg-primary-blue/5 hover:bg-primary-blue/10 transition-colors text-left group disabled:opacity-50"
                    >
                        <div className="flex items-center justify-between">
                            <div>
                                <p className="font-medium text-primary-blue">Complete Data</p>
                                <p className="text-sm text-text-muted">
                                    {isDownloading ? 'Starting download...' : getFilterDescription()}
                                </p>
                                {totalCount && !isDownloading && (
                                    <p className="text-xs text-text-muted mt-1">~{totalCount.toLocaleString()} certificates</p>
                                )}
                            </div>
                            {isDownloading ? (
                                <svg className="w-5 h-5 text-primary-blue animate-spin" fill="none" viewBox="0 0 24 24">
                                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                </svg>
                            ) : (
                                <svg className="w-5 h-5 text-primary-blue" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                                </svg>
                            )}
                        </div>
                    </button>
                </div>

                {/* Close button */}
                <button
                    onClick={onClose}
                    className="w-full py-2 text-center text-sm text-text-muted hover:text-text-primary transition-colors"
                >
                    Cancel
                </button>
            </div>
        </div>
    );
}

