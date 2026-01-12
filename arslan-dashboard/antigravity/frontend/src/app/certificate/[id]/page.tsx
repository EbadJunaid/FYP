'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Card from '@/components/Card';
import { fetchCertificateById } from '@/controllers/pageController';
import { Certificate } from '@/services/apiClient';
import { CertificateIcon, GlobeIcon, ClockIcon, ShieldIcon, AlertIcon, CheckCircleIcon, ErrorCircleIcon } from '@/components/icons/Icons';

const getStatusColor = (status: string) => {
    switch (status) {
        case 'VALID':
            return 'text-accent-green bg-accent-green/15';
        case 'EXPIRED':
            return 'text-accent-red bg-accent-red/15';
        case 'EXPIRING_SOON':
            return 'text-accent-yellow bg-accent-yellow/15';
        case 'WEAK':
            return 'text-accent-orange bg-accent-orange/15';
        default:
            return 'text-text-muted bg-card-border';
    }
};

const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return 'text-accent-green bg-accent-green/15';
    if (grade.startsWith('B')) return 'text-primary-blue bg-primary-blue/15';
    if (grade === 'C') return 'text-accent-yellow bg-accent-yellow/15';
    return 'text-accent-red bg-accent-red/15';
};

export default function CertificateDetailPage() {
    const params = useParams();
    const router = useRouter();
    const [certificate, setCertificate] = useState<Certificate | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const loadCertificate = async () => {
            if (!params.id) return;

            setIsLoading(true);
            setError(null);

            try {
                const cert = await fetchCertificateById(params.id as string);
                if (cert) {
                    setCertificate(cert);
                } else {
                    setError('Certificate not found');
                }
            } catch (err) {
                console.error('Error loading certificate:', err);
                setError('Failed to load certificate details');
            }

            setIsLoading(false);
        };

        loadCertificate();
    }, [params.id]);

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading certificate details...</div>
            </div>
        );
    }

    if (error || !certificate) {
        return (
            <div className="flex flex-col items-center justify-center h-64 gap-4">
                <ErrorCircleIcon className="w-12 h-12 text-accent-red" />
                <p className="text-text-muted">{error || 'Certificate not found'}</p>
                <button
                    onClick={() => router.back()}
                    className="px-4 py-2 bg-primary-blue text-white rounded-lg hover:bg-primary-blue/80 transition-colors"
                >
                    Go Back
                </button>
            </div>
        );
    }

    const formatDate = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                year: 'numeric',
                month: 'long',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="space-y-6">
            {/* Header */}
            <div className="flex items-start justify-between">
                <div>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => router.back()}
                            className="p-2 rounded-lg hover:bg-card-border transition-colors"
                        >
                            <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                        <a
                            href={`https://${certificate.domain}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-2xl font-bold text-primary-blue hover:underline"
                        >
                            {certificate.domain}
                        </a>
                    </div>
                    <div className="ml-10 mt-1">
                        <p className="text-text-muted">Certificate Details</p>
                        <p className="text-xs text-text-secondary font-mono mt-1">
                            ID: {certificate.id}
                        </p>
                    </div>
                </div>
                <div className="flex items-center gap-3">
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getGradeColor(certificate.grade)}`}>
                        Grade {certificate.grade}
                    </span>
                    <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStatusColor(certificate.status)}`}>
                        {certificate.status.replace('_', ' ')}
                    </span>
                </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-blue/15 flex items-center justify-center">
                            <CertificateIcon className="w-5 h-5 text-primary-blue" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Encryption</p>
                            <p className="text-lg font-semibold text-text-primary">{certificate.encryptionType}</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-green/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-green" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Key Length</p>
                            <p className="text-lg font-semibold text-text-primary">{certificate.keyLength} bits</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-purple/15 flex items-center justify-center">
                            <GlobeIcon className="w-5 h-5 text-primary-purple" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Country</p>
                            <p className="text-lg font-semibold text-text-primary">{certificate.country}</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${certificate.vulnerabilityCount.errors > 0 ? 'bg-accent-red/15' : 'bg-accent-green/15'
                            }`}>
                            <AlertIcon className={`w-5 h-5 ${certificate.vulnerabilityCount.errors > 0 ? 'text-accent-red' : 'text-accent-green'
                                }`} />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Vulnerabilities</p>
                            <p className="text-lg font-semibold text-text-primary">{certificate.vulnerabilities}</p>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Details Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Validity Section */}
                <Card title="Validity Information">
                    <div className="space-y-4">
                        <div className="flex justify-between items-center py-2 border-b border-card-border">
                            <span className="text-text-muted">Valid From</span>
                            <span className="text-text-primary font-medium">{formatDate(certificate.validFrom)}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-card-border">
                            <span className="text-text-muted">Valid To</span>
                            <span className="text-text-primary font-medium">{formatDate(certificate.validTo)}</span>
                        </div>
                        <div className="flex justify-between items-center py-2 border-b border-card-border">
                            <span className="text-text-muted">Status</span>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(certificate.status)}`}>
                                {certificate.status.replace('_', ' ')}
                            </span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-text-muted">Validation Level</span>
                            <span className="text-text-primary font-medium">{certificate.validationLevel}</span>
                        </div>
                    </div>
                </Card>

                {/* Issuer Section */}
                <Card title="Issuer Information">
                    <div className="space-y-4">
                        <div className="flex justify-between items-center py-2 border-b border-card-border">
                            <span className="text-text-muted">Organization</span>
                            <span className="text-text-primary font-medium">{certificate.issuer}</span>
                        </div>
                        <div className="py-2 border-b border-card-border">
                            <span className="text-text-muted block mb-1">Issuer DN</span>
                            <span className="text-text-secondary text-sm break-all">{certificate.issuerDn}</span>
                        </div>
                        <div className="flex justify-between items-center py-2">
                            <span className="text-text-muted">Signature Algorithm</span>
                            <span className="text-text-primary font-medium">{certificate.signatureAlgorithm}</span>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Subject Alternative Names */}
            {certificate.san && certificate.san.length > 0 && (
                <Card title="Subject Alternative Names (SANs)">
                    <div className="flex flex-wrap gap-2">
                        {certificate.san.map((name, index) => (
                            <span
                                key={index}
                                className="px-3 py-1 bg-card-border rounded-full text-sm text-text-secondary"
                            >
                                {name}
                            </span>
                        ))}
                    </div>
                </Card>
            )}

            {/* Vulnerability Details */}
            <Card title="Security Analysis">
                <div className="space-y-4">
                    <div className="flex items-center gap-4">
                        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${certificate.vulnerabilityCount.errors > 0 ? 'bg-accent-red/15' : 'bg-accent-green/15'
                            }`}>
                            {certificate.vulnerabilityCount.errors > 0 ? (
                                <ErrorCircleIcon className="w-6 h-6 text-accent-red" />
                            ) : (
                                <CheckCircleIcon className="w-6 h-6 text-accent-green" />
                            )}
                        </div>
                        <div>
                            <p className="text-lg font-semibold text-text-primary">
                                {certificate.vulnerabilityCount.errors > 0
                                    ? `${certificate.vulnerabilityCount.errors} Critical Issue(s) Found`
                                    : certificate.vulnerabilityCount.warnings > 0
                                        ? `${certificate.vulnerabilityCount.warnings} Warning(s) Found`
                                        : 'No Issues Found'}
                            </p>
                            <p className="text-text-muted text-sm">
                                {certificate.vulnerabilityCount.errors > 0
                                    ? 'Immediate attention required'
                                    : certificate.vulnerabilityCount.warnings > 0
                                        ? 'Review recommended'
                                        : 'Certificate is secure'}
                            </p>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4 mt-4">
                        <div className="p-4 bg-background rounded-lg">
                            <p className="text-xs text-text-muted mb-1">Errors</p>
                            <p className={`text-2xl font-bold ${certificate.vulnerabilityCount.errors > 0 ? 'text-accent-red' : 'text-text-primary'
                                }`}>
                                {certificate.vulnerabilityCount.errors}
                            </p>
                        </div>
                        <div className="p-4 bg-background rounded-lg">
                            <p className="text-xs text-text-muted mb-1">Warnings</p>
                            <p className={`text-2xl font-bold ${certificate.vulnerabilityCount.warnings > 0 ? 'text-accent-yellow' : 'text-text-primary'
                                }`}>
                                {certificate.vulnerabilityCount.warnings}
                            </p>
                        </div>
                    </div>

                    {/* Detailed Zlint Errors/Warnings List */}
                    {certificate.zlintDetails && Object.keys(certificate.zlintDetails).length > 0 && (
                        <div className="mt-6 space-y-4">
                            {/* Errors List */}
                            {Object.entries(certificate.zlintDetails)
                                .filter(([, v]) => v.result === 'error')
                                .length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-semibold text-accent-red mb-2 flex items-center gap-2">
                                            <ErrorCircleIcon className="w-4 h-4" />
                                            Error Details
                                        </h4>
                                        <div className="space-y-2">
                                            {Object.entries(certificate.zlintDetails)
                                                .filter(([, v]) => v.result === 'error')
                                                .slice(0, 10)
                                                .map(([key, value]) => (
                                                    <div
                                                        key={key}
                                                        className="p-3 bg-accent-red/10 border border-accent-red/20 rounded-lg"
                                                    >
                                                        <p className="text-sm text-text-primary font-medium">
                                                            {key.replace(/_/g, ' ')}
                                                        </p>
                                                        {value.details && (
                                                            <p className="text-xs text-text-muted mt-1">{value.details}</p>
                                                        )}
                                                    </div>
                                                ))}
                                        </div>
                                    </div>
                                )}

                            {/* Warnings List */}
                            {Object.entries(certificate.zlintDetails)
                                .filter(([, v]) => v.result === 'warn')
                                .length > 0 && (
                                    <div>
                                        <h4 className="text-sm font-semibold text-accent-yellow mb-2 flex items-center gap-2">
                                            <AlertIcon className="w-4 h-4" />
                                            Warning Details
                                        </h4>
                                        <div className="space-y-2">
                                            {Object.entries(certificate.zlintDetails)
                                                .filter(([, v]) => v.result === 'warn')
                                                .slice(0, 10)
                                                .map(([key, value]) => (
                                                    <div
                                                        key={key}
                                                        className="p-3 bg-accent-yellow/10 border border-accent-yellow/20 rounded-lg"
                                                    >
                                                        <p className="text-sm text-text-primary font-medium">
                                                            {key.replace(/_/g, ' ')}
                                                        </p>
                                                        {value.details && (
                                                            <p className="text-xs text-text-muted mt-1">{value.details}</p>
                                                        )}
                                                    </div>
                                                ))}
                                        </div>
                                    </div>
                                )}
                        </div>
                    )}
                </div>
            </Card>
        </div>
    );
}
