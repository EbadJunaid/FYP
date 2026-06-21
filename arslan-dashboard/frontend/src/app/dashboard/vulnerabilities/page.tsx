'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Card from '@/components/Card';
import Pagination from '@/components/Pagination';
import { AlertIcon, ShieldIcon, ChevronRightIcon, KeyIcon, InfoIcon } from '@/components/icons/Icons';
import { fetchVulnerabilities } from '@/controllers/pageController';
import { apiClient, Certificate } from '@/services/apiClient';

interface RiskSignal {
    label: string;
    points: number;
}

interface VulnerabilityCertificate extends Certificate {
    vulnerabilityCount: { errors: number; warnings: number };
    riskScore?: number;
    riskLevel?: 'Critical' | 'High' | 'Medium' | 'Low';
    riskFactors?: RiskSignal[];
    positiveSignals?: RiskSignal[];
    validityDays?: number;
    sharedPublicKey?: boolean;
}

type FilterMode =
    | { source: 'risk'; label: string; riskLevel?: string }
    | { source: 'certificates'; label: string; riskFilter: string };

const getSeverityColor = (severity: string) => {
    switch (severity) {
        case 'Critical':
            return 'text-accent-red bg-accent-red/15';
        case 'High':
            return 'text-accent-orange bg-accent-orange/15';
        case 'Medium':
            return 'text-accent-yellow bg-accent-yellow/15';
        case 'Low':
            return 'text-accent-green bg-accent-green/15';
        default:
            return 'text-text-muted bg-card-border';
    }
};

const getStatusColor = (status: string) => {
    switch (status) {
        case 'VALID':
            return 'text-accent-green';
        case 'EXPIRED':
            return 'text-accent-red';
        case 'EXPIRING_SOON':
            return 'text-accent-yellow';
        case 'WEAK':
            return 'text-accent-orange';
        default:
            return 'text-text-muted';
    }
};

export default function VulnerabilitiesPage() {
    const router = useRouter();
    const pageSize = 10;
    const [certificates, setCertificates] = useState<VulnerabilityCertificate[]>([]);
    const [summary, setSummary] = useState({ critical: 0, high: 0, medium: 0, low: 0, warning: 0, total: 0 });
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [activeFilter, setActiveFilter] = useState<FilterMode>({ source: 'risk', label: 'Ranked Risk' });
    const [expandedId, setExpandedId] = useState<string | null>(null);
    const [showFormula, setShowFormula] = useState(false);
    const [riskRequestPageSize, setRiskRequestPageSize] = useState(pageSize);

    useEffect(() => {
        const loadVulnerabilities = async () => {
            setIsLoading(true);
            setError(null);

            try {
                if (activeFilter.source === 'certificates') {
                    const data = await apiClient.getCertificates({
                        page: currentPage,
                        pageSize,
                        risk_filter: activeFilter.riskFilter,
                    });
                    setCertificates((data.certificates || []) as VulnerabilityCertificate[]);
                    setTotalPages(data.pagination?.totalPages || 1);
                } else {
                    const data = await fetchVulnerabilities(currentPage, riskRequestPageSize, activeFilter.riskLevel);
                    setCertificates(data.certificates || []);
                    setSummary({
                        critical: data.summary?.critical || 0,
                        high: data.summary?.high || 0,
                        medium: data.summary?.medium || 0,
                        low: data.summary?.low || 0,
                        warning: data.summary?.warning || 0,
                        total: data.summary?.total || 0,
                    });
                    setTotalPages(data.pagination?.totalPages || 1);
                }
            } catch (err) {
                setError('Unable to load vulnerabilities.');
                console.error('Error loading vulnerabilities page:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadVulnerabilities();
    }, [currentPage, activeFilter, riskRequestPageSize]);

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
    };

    const applyFilter = (filter: FilterMode) => {
        let nextRiskPageSize = pageSize;
        if (filter.source === 'risk' && filter.riskLevel) {
            const levelKey = filter.riskLevel.toLowerCase() as keyof typeof summary;
            const levelCount = Number(summary[levelKey] || 0);
            nextRiskPageSize = Math.max(pageSize, levelCount);
        }
        setRiskRequestPageSize(nextRiskPageSize);
        setActiveFilter(filter);
        setCurrentPage(1);
        setExpandedId(null);
    };

    const pageTitle = 'Vulnerabilities';
    const vulnerabilityLabel = (cert: VulnerabilityCertificate) => {
        if (cert.riskLevel) return cert.riskLevel;
        if (cert.vulnerabilityCount.errors > 0) return 'Critical';
        if (cert.vulnerabilityCount.warnings > 0) return 'High';
        return 'Low';
    };

    const formatDate = (date?: string) => {
        if (!date) return 'N/A';
        const parsed = new Date(date);
        return Number.isNaN(parsed.getTime()) ? date : parsed.toLocaleDateString();
    };

    const shortHash = (value?: string) => {
        if (!value) return 'N/A';
        return value.length > 18 ? `${value.slice(0, 18)}...` : value;
    };

    return (
        <div className="space-y-6">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-text-primary">{pageTitle}</h1>
                    <p className="text-text-muted text-sm mt-1">Risk-ranked certificates based on expiry, shared keys, weak encryption, validity, and ZLint issues</p>
                </div>
                <button
                    onClick={() => setShowFormula((value) => !value)}
                    className="inline-flex items-center gap-2 self-start px-3 py-2 rounded-md border border-card-border text-sm text-text-secondary hover:text-text-primary hover:bg-card-border/40 transition-colors"
                    aria-expanded={showFormula}
                >
                    <InfoIcon className="w-4 h-4" />
                    Score Formula
                </button>
            </div>

            {showFormula && (
                <Card>
                    <div className="grid grid-cols-1 md:grid-cols-5 gap-3">
                        {[
                            ['Expired', '30'],
                            ['Shared key', '30'],
                            ['Weak RSA', '20'],
                            ['Long validity', '10'],
                            ['ZLint issues', 'Max 10'],
                        ].map(([label, value]) => (
                            <div key={label} className="rounded-md border border-card-border bg-background/40 p-3">
                                <p className="text-xs text-text-muted">{label}</p>
                                <p className="text-lg font-semibold text-text-primary">{value}</p>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-text-muted mt-3">
                        Positive signals reduce the score slightly: valid certificate, strong key, modern validity period, and clean ZLint results.
                        Filter chips select the main risk signal, while each row still shows the full combined score.
                    </p>
                </Card>
            )}

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="hover-lift cursor-pointer" onClick={() => applyFilter({ source: 'risk', label: 'Critical Risk', riskLevel: 'Critical' })}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-red/15 flex items-center justify-center">
                            <AlertIcon className="w-5 h-5 text-accent-red" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.critical}</p>
                            <p className="text-xs text-text-muted">Critical Risk</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift cursor-pointer" onClick={() => applyFilter({ source: 'risk', label: 'High Risk', riskLevel: 'High' })}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-orange/15 flex items-center justify-center">
                            <AlertIcon className="w-5 h-5 text-accent-orange" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.high}</p>
                            <p className="text-xs text-text-muted">High Risk</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift cursor-pointer" onClick={() => applyFilter({ source: 'risk', label: 'Medium Risk', riskLevel: 'Medium' })}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-yellow/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-yellow" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.medium}</p>
                            <p className="text-xs text-text-muted">Medium Risk</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift cursor-pointer" onClick={() => applyFilter({ source: 'risk', label: 'Total Risky' })}>
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-green/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-green" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.total}</p>
                            <p className="text-xs text-text-muted">Total Risky</p>
                        </div>
                    </div>
                </Card>
            </div>

            <div className="flex flex-wrap gap-2">
                {[
                    { label: 'Ranked Risk', filter: { source: 'risk', label: 'Ranked Risk' } as FilterMode },
                    { label: 'Expired', filter: { source: 'certificates', label: 'Expired', riskFilter: 'expired' } as FilterMode },
                    { label: 'Shared Keys', filter: { source: 'certificates', label: 'Shared Keys', riskFilter: 'shared-key' } as FilterMode },
                    { label: 'Weak Encryption', filter: { source: 'certificates', label: 'Weak Encryption', riskFilter: 'weak-encryption' } as FilterMode },
                    { label: 'Long Validity', filter: { source: 'certificates', label: 'Long Validity', riskFilter: 'long-validity' } as FilterMode },
                    { label: 'ZLint Issues', filter: { source: 'certificates', label: 'ZLint Issues', riskFilter: 'zlint' } as FilterMode },
                ].map((item) => (
                    <button
                        key={item.label}
                        onClick={() => applyFilter(item.filter)}
                        className={`px-3 py-1.5 rounded-md text-xs font-medium border transition-colors ${
                            activeFilter.label === item.label
                                ? 'bg-primary-blue text-white border-primary-blue'
                                : 'border-card-border text-text-secondary hover:text-text-primary hover:bg-card-border/40'
                        }`}
                    >
                        {item.label}
                    </button>
                ))}
            </div>

            <Card title="Vulnerability Details" subtitle={`${activeFilter.label} certificates`}>
                {isLoading ? (
                    <div className="py-20 text-center text-text-muted">Loading vulnerabilities...</div>
                ) : error ? (
                    <div className="py-20 text-center text-accent-red">{error}</div>
                ) : certificates.length === 0 ? (
                    <div className="py-20 text-center text-text-muted">No risky certificates found for the selected scope.</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[900px]">
                            <thead>
                                <tr className="border-b border-card-border text-left text-xs uppercase text-text-muted">
                                    <th className="px-4 py-3 w-10"></th>
                                    <th className="px-4 py-3">Domain</th>
                                    <th className="px-4 py-3">Risk Score</th>
                                    <th className="px-4 py-3">Level</th>
                                    <th className="px-4 py-3">Main Factors</th>
                                    <th className="px-4 py-3">ZLint</th>
                                    <th className="px-4 py-3">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {certificates.map((cert) => {
                                    const isExpanded = expandedId === cert.id;
                                    const sharedDetails = cert.sharedKeyDetails;
                                    return (
                                        <React.Fragment key={cert.id}>
                                            <tr className="border-b border-card-border hover:bg-background/50 transition-colors">
                                                <td className="px-4 py-4">
                                                    <button
                                                        onClick={() => setExpandedId(isExpanded ? null : cert.id)}
                                                        className="w-8 h-8 rounded-md border border-card-border flex items-center justify-center text-text-secondary hover:text-text-primary hover:bg-card-border/40 transition-colors"
                                                        aria-label={isExpanded ? 'Collapse certificate details' : 'Expand certificate details'}
                                                    >
                                                        <ChevronRightIcon className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-90' : ''}`} />
                                                    </button>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <button
                                                        onClick={() => router.push(`/certificate/${cert.id}`)}
                                                        className="font-medium text-primary-blue hover:underline text-left"
                                                    >
                                                        {cert.domain}
                                                    </button>
                                                    <p className="text-xs text-text-muted truncate max-w-[260px]">{cert.issuer}</p>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex items-center gap-3">
                                                        <div className="h-2 w-20 rounded-full bg-card-border overflow-hidden">
                                                            <div
                                                                className="h-full rounded-full bg-accent-red"
                                                                style={{ width: `${Math.min(100, cert.riskScore || 0)}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-sm font-semibold text-text-primary">{cert.riskScore || 0}</span>
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(vulnerabilityLabel(cert))}`}>
                                                        {vulnerabilityLabel(cert)}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-4">
                                                    <div className="flex flex-wrap gap-2 max-w-[360px]">
                                                        {(cert.riskFactors || []).slice(0, 3).map((factor) => (
                                                            <button
                                                                key={`${cert.id}-${factor.label}`}
                                                                onClick={() => {
                                                                    const label = factor.label.toLowerCase();
                                                                    if (label.includes('expired')) applyFilter({ source: 'certificates', label: 'Expired', riskFilter: 'expired' });
                                                                    else if (label.includes('shared')) applyFilter({ source: 'certificates', label: 'Shared Keys', riskFilter: 'shared-key' });
                                                                    else if (label.includes('weak encryption')) applyFilter({ source: 'certificates', label: 'Weak Encryption', riskFilter: 'weak-encryption' });
                                                                    else if (label.includes('long validity')) applyFilter({ source: 'certificates', label: 'Long Validity', riskFilter: 'long-validity' });
                                                                    else if (label.includes('zlint')) applyFilter({ source: 'certificates', label: 'ZLint Issues', riskFilter: 'zlint' });
                                                                }}
                                                                className="px-2 py-1 rounded-md bg-accent-red/10 text-accent-red text-xs font-medium hover:bg-accent-red/20"
                                                                title={factor.label}
                                                            >
                                                                {factor.label}
                                                            </button>
                                                        ))}
                                                        {(!cert.riskFactors || cert.riskFactors.length === 0) && (
                                                            <span className="text-xs text-text-muted">No major risk factor</span>
                                                        )}
                                                    </div>
                                                </td>
                                                <td className="px-4 py-4 text-text-secondary">
                                                    {cert.vulnerabilityCount.errors} errors / {cert.vulnerabilityCount.warnings} warnings
                                                </td>
                                                <td className="px-4 py-4">
                                                    <span className={`text-sm font-medium ${getStatusColor(cert.status)}`}>
                                                        {cert.status.replace('_', ' ')}
                                                    </span>
                                                </td>
                                            </tr>

                                            {isExpanded && (
                                                <tr className="border-b border-card-border bg-card-border/10">
                                                    <td colSpan={7} className="px-4 py-4">
                                                        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                                                            <div className="p-3 rounded-md bg-card-bg border border-card-border">
                                                                <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                                                                    <KeyIcon className="w-4 h-4" />
                                                                    Shared Key
                                                                </div>
                                                                <p className="font-mono text-xs text-text-primary break-all">
                                                                    {shortHash(sharedDetails?.publicKeyHash || cert.publicKeyHash || cert.spkiFingerprint)}
                                                                </p>
                                                                <p className="text-xs text-text-muted mt-2">
                                                                    {sharedDetails ? `${sharedDetails.certificateCount} certificates share this key` : 'No shared-key group found'}
                                                                </p>
                                                            </div>

                                                            <div className="p-3 rounded-md bg-card-bg border border-card-border">
                                                                <p className="text-xs text-text-muted mb-2">Expiration</p>
                                                                <p className={`text-sm font-medium ${getStatusColor(cert.status)}`}>{formatDate(cert.validTo)}</p>
                                                                <p className="text-xs text-text-muted mt-2">
                                                                    Validity: {cert.validityDays || Math.round((cert.validityLength || 0) / 86400) || 'N/A'} days
                                                                </p>
                                                            </div>

                                                            <div className="p-3 rounded-md bg-card-bg border border-card-border">
                                                                <p className="text-xs text-text-muted mb-2">Issuer</p>
                                                                <p className="text-sm font-medium text-text-primary">{cert.issuer || 'Unknown'}</p>
                                                                <p className="text-xs text-text-muted mt-2">Validation: {cert.validationLevel || 'Unknown'}</p>
                                                            </div>

                                                            <div className="p-3 rounded-md bg-card-bg border border-card-border">
                                                                <p className="text-xs text-text-muted mb-2">Sample Shared Domains</p>
                                                                <div className="space-y-1">
                                                                    {(sharedDetails?.sampleDomains || []).slice(0, 4).map((domain) => (
                                                                        <button
                                                                            key={`${cert.id}-${domain}`}
                                                                            onClick={() => router.push(`/certificate/${cert.id}`)}
                                                                            className="block text-xs text-primary-blue hover:underline truncate max-w-full text-left"
                                                                            title={domain}
                                                                        >
                                                                            {domain}
                                                                        </button>
                                                                    ))}
                                                                    {!(sharedDetails?.sampleDomains || []).length && (
                                                                        <p className="text-xs text-text-muted">No sample domains available</p>
                                                                    )}
                                                                </div>
                                                            </div>
                                                        </div>

                                                        <div className="mt-4 flex justify-end">
                                                            <button
                                                                onClick={() => router.push(`/certificate/${cert.id}`)}
                                                                className="px-4 py-2 rounded-md bg-primary-blue text-white text-sm font-medium hover:bg-primary-blue/85 transition-colors"
                                                            >
                                                                View Full Certificate Details
                                                            </button>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </React.Fragment>
                                    );
                                })}
                            </tbody>
                        </table>
                    </div>
                )}

                {totalPages > 1 && (
                    <div className="mt-4 pt-4 border-t border-card-border">
                        <Pagination currentPage={currentPage} totalPages={totalPages} onPageChange={handlePageChange} />
                    </div>
                )}
            </Card>
        </div>
    );
}
