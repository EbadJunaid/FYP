'use client';

import React, { useState, useEffect } from 'react';
import { CloseIcon } from '@/components/icons/Icons';
import { FilterOptions, SSLGrade, CertificateStatus, VulnerabilitySeverity } from '@/types/dashboard';
import { fetchUniqueFilters } from '@/controllers/pageController';

interface FilterModalProps {
    isOpen: boolean;
    onClose: () => void;
    filters: FilterOptions;
    onApplyFilters: (filters: FilterOptions) => void;
}

const sslGrades: SSLGrade[] = ['A+', 'A', 'A-', 'B+', 'B', 'C', 'D', 'F'];
const statuses: CertificateStatus[] = ['VALID', 'EXPIRED', 'WEAK', 'EXPIRING_SOON'];
const severities: VulnerabilitySeverity[] = ['Critical', 'High', 'Medium', 'Low', 'None'];

// Extended filter options
interface ExtendedFilterOptions extends FilterOptions {
    country: string[];
    validationLevel: string[];
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
        validationLevel: [],
    });

    // Dynamic filter options from API
    const [apiCountries, setApiCountries] = useState<string[]>([]);
    const [apiIssuers, setApiIssuers] = useState<string[]>([]);
    const [apiValidationLevels, setApiValidationLevels] = useState<string[]>(['DV', 'OV', 'EV']);
    const [isLoadingFilters, setIsLoadingFilters] = useState(true);

    // Fetch unique filter options from API when modal opens
    useEffect(() => {
        if (isOpen) {
            const loadFilters = async () => {
                setIsLoadingFilters(true);
                try {
                    const filterOptions = await fetchUniqueFilters();
                    setApiCountries(filterOptions.countries || []);
                    setApiIssuers(filterOptions.issuers || []);
                    setApiValidationLevels(filterOptions.validationLevels || ['DV', 'OV', 'EV']);
                } catch (error) {
                    console.error('Error loading filter options:', error);
                    // Fallback to defaults
                    setApiCountries(['Pakistan', 'United States', 'United Kingdom', 'Germany', 'Japan']);
                    setApiIssuers(["Let's Encrypt", 'DigiCert Inc.', 'GlobalSign', 'Sectigo']);
                }
                setIsLoadingFilters(false);
            };
            loadFilters();
        }
    }, [isOpen]);

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

    const handleCountryToggle = (country: string) => {
        setLocalFilters((prev) => ({
            ...prev,
            country: prev.country.includes(country)
                ? prev.country.filter((c) => c !== country)
                : [...prev.country, country],
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

    const handleValidationLevelToggle = (level: string) => {
        setLocalFilters((prev) => ({
            ...prev,
            validationLevel: prev.validationLevel.includes(level)
                ? prev.validationLevel.filter((l) => l !== level)
                : [...prev.validationLevel, level],
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
            validationLevel: [],
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
        if (localFilters.validationLevel.length) count += localFilters.validationLevel.length;
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
                    {isLoadingFilters ? (
                        <div className="flex items-center justify-center py-8">
                            <div className="text-text-muted">Loading filter options...</div>
                        </div>
                    ) : (
                        <>
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

                            {/* Country - from API */}
                            {apiCountries.length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-text-primary mb-3">
                                        Country <span className="text-text-muted text-xs">({apiCountries.length} available)</span>
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {apiCountries.slice(0, 12).map((country) => (
                                            <button
                                                key={country}
                                                onClick={() => handleCountryToggle(country)}
                                                className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                          ${localFilters.country.includes(country)
                                                        ? 'bg-primary-blue text-white'
                                                        : 'bg-background text-text-secondary hover:bg-card-border'
                                                    }`}
                                            >
                                                {country}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Issuer - from API */}
                            {apiIssuers.length > 0 && (
                                <div>
                                    <label className="block text-sm font-medium text-text-primary mb-3">
                                        Certificate Issuer <span className="text-text-muted text-xs">({apiIssuers.length} available)</span>
                                    </label>
                                    <div className="flex flex-wrap gap-2">
                                        {apiIssuers.slice(0, 10).map((issuer) => (
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
                            )}

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

                            {/* Validation Level */}
                            <div>
                                <label className="block text-sm font-medium text-text-primary mb-3">
                                    Validation Level
                                </label>
                                <div className="flex flex-wrap gap-2">
                                    {apiValidationLevels.map((level) => (
                                        <button
                                            key={level}
                                            onClick={() => handleValidationLevelToggle(level)}
                                            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors
                        ${localFilters.validationLevel.includes(level)
                                                    ? 'bg-primary-blue text-white'
                                                    : 'bg-background text-text-secondary hover:bg-card-border'
                                                }`}
                                        >
                                            {level === 'DV' ? 'Domain Validated' : level === 'OV' ? 'Org Validated' : 'Extended Validated'}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </>
                    )}
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
