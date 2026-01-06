'use client';

import React, { useState } from 'react';
import { CloseIcon } from '@/components/icons/Icons';
import { FilterOptions, SSLGrade, CertificateStatus, VulnerabilitySeverity } from '@/types/dashboard';

interface FilterModalProps {
    isOpen: boolean;
    onClose: () => void;
    filters: FilterOptions;
    onApplyFilters: (filters: FilterOptions) => void;
}

const sslGrades: SSLGrade[] = ['A+', 'A', 'A-', 'B+', 'B', 'C', 'D', 'F'];
const statuses: CertificateStatus[] = ['VALID', 'EXPIRED', 'WEAK', 'EXPIRING_SOON'];
const severities: VulnerabilitySeverity[] = ['Critical', 'High', 'Medium', 'Low', 'None'];

// Mock countries data
const countries = [
    { code: 'US', name: 'United States' },
    { code: 'UK', name: 'United Kingdom' },
    { code: 'DE', name: 'Germany' },
    { code: 'JP', name: 'Japan' },
    { code: 'FR', name: 'France' },
    { code: 'CA', name: 'Canada' },
    { code: 'AU', name: 'Australia' },
    { code: 'NL', name: 'Netherlands' },
];

// Mock issuers data
const issuers = [
    'DigiCert Inc.',
    'Let\'s Encrypt',
    'GlobalSign',
    'Sectigo',
    'GoDaddy',
    'Entrust Datacard',
    'Comodo',
    'Internal CA',
];

// Extended filter options
interface ExtendedFilterOptions extends FilterOptions {
    country: string[];
}

export default function FilterModal({
    isOpen,
    onClose,
    filters,
    onApplyFilters,
}: FilterModalProps) {
    const [localFilters, setLocalFilters] = useState<ExtendedFilterOptions>({
        ...filters,
        country: [],
    });

    if (!isOpen) return null;

    const handleStatusToggle = (status: CertificateStatus) => {
        setLocalFilters((prev) => ({
            ...prev,
            status: prev.status.includes(status)
                ? prev.status.filter((s) => s !== status)
                : [...prev.status, status],
        }));
    };

    const handleGradeToggle = (grade: SSLGrade) => {
        setLocalFilters((prev) => ({
            ...prev,
            sslGrade: prev.sslGrade.includes(grade)
                ? prev.sslGrade.filter((g) => g !== grade)
                : [...prev.sslGrade, grade],
        }));
    };

    const handleSeverityToggle = (severity: VulnerabilitySeverity) => {
        setLocalFilters((prev) => ({
            ...prev,
            vulnerabilityType: prev.vulnerabilityType.includes(severity)
                ? prev.vulnerabilityType.filter((s) => s !== severity)
                : [...prev.vulnerabilityType, severity],
        }));
    };

    const handleCountryToggle = (code: string) => {
        setLocalFilters((prev) => ({
            ...prev,
            country: prev.country.includes(code)
                ? prev.country.filter((c) => c !== code)
                : [...prev.country, code],
        }));
    };

    const handleIssuerToggle = (issuer: string) => {
        setLocalFilters((prev) => ({
            ...prev,
            issuer: prev.issuer.includes(issuer)
                ? prev.issuer.filter((i) => i !== issuer)
                : [...prev.issuer, issuer],
        }));
    };

    const handleApply = () => {
        onApplyFilters(localFilters);
        onClose();
    };

    const handleReset = () => {
        const resetFilters: ExtendedFilterOptions = {
            dateRange: { start: null, end: null },
            status: [],
            vulnerabilityType: [],
            issuer: [],
            sslGrade: [],
            country: [],
        };
        setLocalFilters(resetFilters);
    };

    const getActiveFiltersCount = () => {
        let count = 0;
        if (localFilters.status.length) count += localFilters.status.length;
        if (localFilters.sslGrade.length) count += localFilters.sslGrade.length;
        if (localFilters.vulnerabilityType.length) count += localFilters.vulnerabilityType.length;
        if (localFilters.issuer.length) count += localFilters.issuer.length;
        if (localFilters.country.length) count += localFilters.country.length;
        if (localFilters.dateRange.start || localFilters.dateRange.end) count += 1;
        return count;
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Overlay */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative w-full max-w-2xl bg-card-bg border border-card-border rounded-2xl shadow-2xl animate-fade-in">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-card-border">
                    <div className="flex items-center gap-3">
                        <h2 className="text-lg font-semibold text-text-primary">Filter Results</h2>
                        {getActiveFiltersCount() > 0 && (
                            <span className="px-2 py-0.5 text-xs font-medium bg-primary-blue text-white rounded-full">
                                {getActiveFiltersCount()} active
                            </span>
                        )}
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-background transition-colors"
                    >
                        <CloseIcon size={20} />
                    </button>
                </div>

                {/* Content */}
                <div className="p-6 space-y-6 max-h-[60vh] overflow-y-auto">
                    {/* Date Range */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            Date Range
                        </label>
                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label className="block text-xs text-text-muted mb-1">From</label>
                                <input
                                    type="date"
                                    className="w-full px-3 py-2 bg-background border border-card-border rounded-lg
                    text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-blue/50"
                                    onChange={(e) =>
                                        setLocalFilters((prev) => ({
                                            ...prev,
                                            dateRange: { ...prev.dateRange, start: new Date(e.target.value) },
                                        }))
                                    }
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-text-muted mb-1">To</label>
                                <input
                                    type="date"
                                    className="w-full px-3 py-2 bg-background border border-card-border rounded-lg
                    text-sm text-text-primary focus:outline-none focus:ring-2 focus:ring-primary-blue/50"
                                    onChange={(e) =>
                                        setLocalFilters((prev) => ({
                                            ...prev,
                                            dateRange: { ...prev.dateRange, end: new Date(e.target.value) },
                                        }))
                                    }
                                />
                            </div>
                        </div>
                    </div>

                    {/* Country */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            Country
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {countries.map((country) => (
                                <button
                                    key={country.code}
                                    onClick={() => handleCountryToggle(country.code)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${localFilters.country.includes(country.code)
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-background text-text-secondary hover:bg-card-border'
                                        }`}
                                >
                                    {country.name}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Issuer */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            Certificate Issuer
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {issuers.map((issuer) => (
                                <button
                                    key={issuer}
                                    onClick={() => handleIssuerToggle(issuer)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${localFilters.issuer.includes(issuer)
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-background text-text-secondary hover:bg-card-border'
                                        }`}
                                >
                                    {issuer}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* SSL Grade */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            SSL Grade
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {sslGrades.map((grade) => (
                                <button
                                    key={grade}
                                    onClick={() => handleGradeToggle(grade)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${localFilters.sslGrade.includes(grade)
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-background text-text-secondary hover:bg-card-border'
                                        }`}
                                >
                                    {grade}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Status */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            Certificate Status
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {statuses.map((status) => (
                                <button
                                    key={status}
                                    onClick={() => handleStatusToggle(status)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${localFilters.status.includes(status)
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-background text-text-secondary hover:bg-card-border'
                                        }`}
                                >
                                    {status.replace('_', ' ')}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Vulnerability Severity */}
                    <div>
                        <label className="block text-sm font-medium text-text-primary mb-3">
                            Vulnerability Severity
                        </label>
                        <div className="flex flex-wrap gap-2">
                            {severities.map((severity) => (
                                <button
                                    key={severity}
                                    onClick={() => handleSeverityToggle(severity)}
                                    className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                    ${localFilters.vulnerabilityType.includes(severity)
                                            ? 'bg-primary-blue text-white'
                                            : 'bg-background text-text-secondary hover:bg-card-border'
                                        }`}
                                >
                                    {severity}
                                </button>
                            ))}
                        </div>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between px-6 py-4 border-t border-card-border">
                    <button
                        onClick={handleReset}
                        className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors"
                    >
                        Reset All
                    </button>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={onClose}
                            className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary
                bg-background border border-card-border rounded-lg transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            onClick={handleApply}
                            className="px-4 py-2 text-sm font-medium text-white bg-primary-blue hover:bg-primary-blue/90
                rounded-lg transition-colors"
                        >
                            Apply Filters
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
