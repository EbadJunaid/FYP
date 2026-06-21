'use client';

import React, { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { fetchCertificateById } from '@/controllers/pageController';
import { Certificate } from '@/services/apiClient';
import { CertificateIcon, GlobeIcon, ClockIcon, ShieldIcon, AlertIcon, CheckCircleIcon, ErrorCircleIcon, InfoIcon } from '@/components/icons/Icons';

// Info tooltips for all sections
const sectionInfo = {
    validity: 'Certificate validity information shows when the certificate was issued and when it expires.',
    issuer: 'The Certificate Authority (CA) that issued and signed this certificate.',
    subject: 'The entity (domain/organization) that this certificate was issued to.',
    details: 'Technical certificate details including serial number and validity period.',
    fingerprints: 'Cryptographic hashes used to uniquely identify and verify this certificate.',
    keyUsage: 'Specific purposes for which the certificate key can be used.',
    extKeyUsage: 'Additional authorized uses for this certificate beyond standard key usage.',
    san: 'All domain names and IP addresses that this certificate is valid for.',
    security: 'Security analysis results from certificate lint checks (zlint).',
};

const getStatusColor = (status: string) => {
    switch (status) {
        case 'VALID':
            return 'text-accent-green bg-accent-green/15 border-accent-green/30';
        case 'EXPIRED':
            return 'text-accent-red bg-accent-red/15 border-accent-red/30';
        case 'EXPIRING_SOON':
            return 'text-accent-yellow bg-accent-yellow/15 border-accent-yellow/30';
        case 'WEAK':
            return 'text-accent-orange bg-accent-orange/15 border-accent-orange/30';
        default:
            return 'text-text-muted bg-card-border border-card-border';
    }
};

const getGradeColor = (grade: string) => {
    if (grade.startsWith('A')) return 'text-accent-green bg-accent-green/15 border-accent-green/30';
    if (grade.startsWith('B')) return 'text-primary-blue bg-primary-blue/15 border-primary-blue/30';
    if (grade === 'C') return 'text-accent-yellow bg-accent-yellow/15 border-accent-yellow/30';
    return 'text-accent-red bg-accent-red/15 border-accent-red/30';
};

// Info tooltip component
const InfoTooltip = ({ text }: { text: string }) => (
    <div className="group relative inline-flex ml-2">
        <InfoIcon className="w-4 h-4 text-text-muted hover:text-text-secondary cursor-help" />
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-3 py-2 bg-card-bg border border-card-border rounded-lg shadow-lg text-xs text-text-secondary w-64 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all z-50">
            {text}
            <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 border-4 border-transparent border-t-card-border" />
        </div>
    </div>
);

// Section header component
const SectionHeader = ({ title, info }: { title: string; info: string }) => (
    <div className="flex items-center mb-4">
        <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
        <InfoTooltip text={info} />
    </div>
);

// Detail row component
const DetailRow = ({ label, value, mono = false }: { label: string; value: React.ReactNode; mono?: boolean }) => (
    <div className="flex justify-between items-start py-3 border-b border-card-border/50 last:border-0">
        <span className="text-text-muted text-sm">{label}</span>
        <span className={`text-text-primary text-sm font-medium text-right max-w-[60%] ${mono ? 'font-mono text-xs break-all' : ''}`}>
            {value}
        </span>
    </div>
);

// Badge component
const Badge = ({ children, variant = 'default' }: { children: React.ReactNode; variant?: 'success' | 'warning' | 'error' | 'info' | 'default' }) => {
    const colors = {
        success: 'text-accent-green bg-accent-green/15 border-accent-green/30',
        warning: 'text-accent-yellow bg-accent-yellow/15 border-accent-yellow/30',
        error: 'text-accent-red bg-accent-red/15 border-accent-red/30',
        info: 'text-primary-blue bg-primary-blue/15 border-primary-blue/30',
        default: 'text-text-muted bg-card-border border-card-border',
    };
    return (
        <span className={`px-2.5 py-1 rounded-lg text-xs font-medium border ${colors[variant]}`}>
            {children}
        </span>
    );
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
                <div className="flex items-center gap-3">
                    <div className="w-6 h-6 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
                    <span className="text-text-muted">Loading certificate details...</span>
                </div>
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
                month: 'short',
                day: 'numeric',
            });
        } catch {
            return dateStr;
        }
    };

    const formatDays = (seconds: number) => Math.round(seconds / 86400);

    return (
        <div className="space-y-6 pb-8">
            {/* Header */}
            <div className="bg-gradient-to-r from-card-bg to-card-bg/50 border border-card-border rounded-2xl p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => router.back()}
                            className="p-2 rounded-lg bg-background hover:bg-card-border transition-colors"
                        >
                            <svg className="w-5 h-5 text-text-muted" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                            </svg>
                        </button>
                        <div>
                            <a
                                href={`https://${certificate.domain}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xl font-bold text-primary-blue hover:underline flex items-center gap-2"
                            >
                                {certificate.domain}
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                                </svg>
                            </a>
                            <p className="text-xs text-text-muted mt-1 font-mono">ID: {certificate.id}</p>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                        <span className={`px-4 py-2 rounded-xl text-sm font-bold border ${getGradeColor(certificate.grade)}`}>
                            Grade {certificate.grade}
                        </span>
                        <span className={`px-4 py-2 rounded-xl text-sm font-bold border ${getStatusColor(certificate.status)}`}>
                            {certificate.status.replace('_', ' ')}
                        </span>
                    </div>
                </div>
            </div>

            {/* Quick Stats */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-card-bg border border-card-border rounded-xl p-4 hover:border-primary-blue/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-blue/15 flex items-center justify-center">
                            <CertificateIcon className="w-5 h-5 text-primary-blue" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Encryption</p>
                            <p className="text-sm font-semibold text-text-primary">{certificate.encryptionType}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-card-bg border border-card-border rounded-xl p-4 hover:border-accent-green/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-green/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-green" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Key Length</p>
                            <p className="text-sm font-semibold text-text-primary">{certificate.keyLength} bits</p>
                        </div>
                    </div>
                </div>
                <div className="bg-card-bg border border-card-border rounded-xl p-4 hover:border-primary-purple/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-primary-purple/15 flex items-center justify-center">
                            <GlobeIcon className="w-5 h-5 text-primary-purple" />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Validation</p>
                            <p className="text-sm font-semibold text-text-primary">{certificate.validationLevel}</p>
                        </div>
                    </div>
                </div>
                <div className="bg-card-bg border border-card-border rounded-xl p-4 hover:border-accent-yellow/50 transition-colors">
                    <div className="flex items-center gap-3">
                        <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${certificate.vulnerabilityCount.errors > 0 ? 'bg-accent-red/15' : 'bg-accent-green/15'}`}>
                            <AlertIcon className={`w-5 h-5 ${certificate.vulnerabilityCount.errors > 0 ? 'text-accent-red' : 'text-accent-green'}`} />
                        </div>
                        <div>
                            <p className="text-xs text-text-muted">Issues</p>
                            <p className="text-sm font-semibold text-text-primary">{certificate.vulnerabilities}</p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Main Content */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Validity */}
                <div className="bg-card-bg border border-card-border rounded-xl p-5">
                    <SectionHeader title="Validity Information" info={sectionInfo.validity} />
                    <div className="space-y-0">
                        <DetailRow label="Valid From" value={formatDate(certificate.validFrom)} />
                        <DetailRow label="Valid Until" value={formatDate(certificate.validTo)} />
                        <DetailRow label="Status" value={
                            <Badge variant={certificate.status === 'VALID' ? 'success' : certificate.status === 'EXPIRED' ? 'error' : 'warning'}>
                                {certificate.status.replace('_', ' ')}
                            </Badge>
                        } />
                        <DetailRow label="Validity Period" value={certificate.validityLength ? `${formatDays(certificate.validityLength)} days` : 'N/A'} />
                    </div>
                </div>

                {/* Issuer */}
                <div className="bg-card-bg border border-card-border rounded-xl p-5">
                    <SectionHeader title="Issuer Information" info={sectionInfo.issuer} />
                    <div className="space-y-0">
                        <DetailRow label="Organization" value={certificate.issuer} />
                        <DetailRow label="Signature Algorithm" value={certificate.signatureAlgorithm} />
                        <DetailRow label="Issuer DN" value={certificate.issuerDn} mono />
                    </div>
                </div>

                {/* Subject */}
                <div className="bg-card-bg border border-card-border rounded-xl p-5">
                    <SectionHeader title="Subject Information" info={sectionInfo.subject} />
                    <div className="space-y-0">
                        <DetailRow label="Common Name" value={certificate.commonName || certificate.domain} />
                        <DetailRow label="Subject DN" value={certificate.subjectDn || `CN=${certificate.domain}`} mono />
                        <DetailRow label="Self-Signed" value={
                            <Badge variant={certificate.selfSigned ? 'warning' : 'success'}>
                                {certificate.selfSigned ? 'Yes' : 'No'}
                            </Badge>
                        } />
                        <DetailRow label="Is CA" value={
                            <Badge variant={certificate.isCa ? 'info' : 'default'}>
                                {certificate.isCa ? 'Yes' : 'No'}
                            </Badge>
                        } />
                    </div>
                </div>

                {/* Details */}
                <div className="bg-card-bg border border-card-border rounded-xl p-5">
                    <SectionHeader title="Certificate Details" info={sectionInfo.details} />
                    <div className="space-y-0">
                        <DetailRow label="Serial Number" value={certificate.serialNumber || 'N/A'} mono />
                        <DetailRow label="Version" value="v3" />
                        <DetailRow label="Country" value={certificate.country} />
                    </div>
                </div>
            </div>

            {/* Public Key Information */}
            <div className="bg-card-bg border border-card-border rounded-xl p-5">
                <SectionHeader title="Public Key Information" info="Details about the certificate public key including modulus and SPKI fingerprints." />
                <div className="space-y-4">
                    <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-text-muted mb-1">Public Key (Modulus)</p>
                        <p className="text-xs font-mono text-text-secondary break-all max-h-40 overflow-y-auto">
                            {certificate.publicKey || 'N/A'}
                        </p>
                    </div>
                    <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-text-muted mb-1">SPKI Subject Fingerprint</p>
                        <p className="text-xs font-mono text-text-secondary break-all">{certificate.spkiSubjectFingerprint || 'N/A'}</p>
                    </div>
                    <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-text-muted mb-1">Parsed SPKI Fingerprint (SHA-256)</p>
                        <p className="text-xs font-mono text-text-secondary break-all">{certificate.spkiFingerprint || 'N/A'}</p>
                    </div>
                </div>
            </div>

            {/* Fingerprints */}
            <div className="bg-card-bg border border-card-border rounded-xl p-5">
                <SectionHeader title="Fingerprints" info={sectionInfo.fingerprints} />
                <div className="grid gap-4">
                    <div className="bg-background/50 rounded-lg p-4">
                        <p className="text-xs text-text-muted mb-1">SHA-256</p>
                        <p className="text-xs font-mono text-text-secondary break-all">{certificate.fingerprintSha256 || 'N/A'}</p>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-background/50 rounded-lg p-4">
                            <p className="text-xs text-text-muted mb-1">SHA-1</p>
                            <p className="text-xs font-mono text-text-secondary break-all">{certificate.fingerprintSha1 || 'N/A'}</p>
                        </div>
                        <div className="bg-background/50 rounded-lg p-4">
                            <p className="text-xs text-text-muted mb-1">MD5</p>
                            <p className="text-xs font-mono text-text-secondary break-all">{certificate.fingerprintMd5 || 'N/A'}</p>
                        </div>
                    </div>

                </div>
            </div>

            {/* Key Usage */}
            {certificate.keyUsage && (
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    <div className="bg-card-bg border border-card-border rounded-xl p-5">
                        <SectionHeader title="Key Usage" info={sectionInfo.keyUsage} />
                        <div className="flex flex-wrap gap-2">
                            {certificate.keyUsage.digitalSignature && <Badge variant="success">Digital Signature</Badge>}
                            {certificate.keyUsage.keyEncipherment && <Badge variant="info">Key Encipherment</Badge>}
                            {certificate.keyUsage.dataEncipherment && <Badge variant="info">Data Encipherment</Badge>}
                            {certificate.keyUsage.keyCertSign && <Badge variant="warning">Key Cert Sign</Badge>}
                            {certificate.keyUsage.crlSign && <Badge variant="warning">CRL Sign</Badge>}
                        </div>
                    </div>

                    {certificate.extendedKeyUsage && (
                        <div className="bg-card-bg border border-card-border rounded-xl p-5">
                            <SectionHeader title="Extended Key Usage" info={sectionInfo.extKeyUsage} />
                            <div className="flex flex-wrap gap-2">
                                {certificate.extendedKeyUsage.serverAuth && <Badge variant="success">Server Auth</Badge>}
                                {certificate.extendedKeyUsage.clientAuth && <Badge variant="info">Client Auth</Badge>}
                                {certificate.extendedKeyUsage.codeSigning && <Badge variant="warning">Code Signing</Badge>}
                                {certificate.extendedKeyUsage.emailProtection && <Badge variant="info">Email Protection</Badge>}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* SANs */}
            {certificate.san && certificate.san.length > 0 && (
                <div className="bg-card-bg border border-card-border rounded-xl p-5">
                    <SectionHeader title="Subject Alternative Names (SANs)" info={sectionInfo.san} />
                    <div className="flex flex-wrap gap-2">
                        {certificate.san.map((name, index) => (
                            <span
                                key={index}
                                className="px-3 py-1.5 bg-background rounded-lg text-sm text-text-secondary border border-card-border/50"
                            >
                                {name}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Security Analysis */}
            <div className="bg-card-bg border border-card-border rounded-xl p-5">
                <SectionHeader title="Security Analysis" info={sectionInfo.security} />
                <div className="flex items-center gap-4 mb-4">
                    <div className={`w-14 h-14 rounded-xl flex items-center justify-center ${certificate.vulnerabilityCount.errors > 0 ? 'bg-accent-red/15' : 'bg-accent-green/15'
                        }`}>
                        {certificate.vulnerabilityCount.errors > 0 ? (
                            <ErrorCircleIcon className="w-7 h-7 text-accent-red" />
                        ) : (
                            <CheckCircleIcon className="w-7 h-7 text-accent-green" />
                        )}
                    </div>
                    <div>
                        <p className="text-lg font-semibold text-text-primary">
                            {certificate.vulnerabilityCount.errors > 0
                                ? `${certificate.vulnerabilityCount.errors} Critical Issue(s)`
                                : certificate.vulnerabilityCount.warnings > 0
                                    ? `${certificate.vulnerabilityCount.warnings} Warning(s)`
                                    : 'No Issues Found'}
                        </p>
                        <p className="text-sm text-text-muted">
                            {certificate.vulnerabilityCount.errors > 0
                                ? 'Immediate attention required'
                                : certificate.vulnerabilityCount.warnings > 0
                                    ? 'Review recommended'
                                    : 'Certificate passed all checks'}
                        </p>
                    </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                    <div className="bg-background/50 rounded-lg p-4 text-center">
                        <p className={`text-3xl font-bold ${certificate.vulnerabilityCount.errors > 0 ? 'text-accent-red' : 'text-text-primary'}`}>
                            {certificate.vulnerabilityCount.errors}
                        </p>
                        <p className="text-xs text-text-muted mt-1">Errors</p>
                    </div>
                    <div className="bg-background/50 rounded-lg p-4 text-center">
                        <p className={`text-3xl font-bold ${certificate.vulnerabilityCount.warnings > 0 ? 'text-accent-yellow' : 'text-text-primary'}`}>
                            {certificate.vulnerabilityCount.warnings}
                        </p>
                        <p className="text-xs text-text-muted mt-1">Warnings</p>
                    </div>
                </div>

                {/* Zlint Details */}
                {certificate.zlintDetails && Object.keys(certificate.zlintDetails).length > 0 && (
                    <div className="mt-6 space-y-4">
                        {Object.entries(certificate.zlintDetails)
                            .filter(([, v]) => v.result === 'error')
                            .length > 0 && (
                                <div>
                                    <h4 className="text-sm font-semibold text-accent-red mb-2 flex items-center gap-2">
                                        <ErrorCircleIcon className="w-4 h-4" />
                                        Errors
                                    </h4>
                                    <div className="space-y-2">
                                        {Object.entries(certificate.zlintDetails)
                                            .filter(([, v]) => v.result === 'error')
                                            .map(([key, value]) => (
                                                <div key={key} className="p-3 bg-accent-red/10 border border-accent-red/20 rounded-lg">
                                                    <p className="text-sm text-text-primary font-medium">{key.replace(/_/g, ' ')}</p>
                                                    {value.details && <p className="text-xs text-text-muted mt-1">{value.details}</p>}
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            )}

                        {Object.entries(certificate.zlintDetails)
                            .filter(([, v]) => v.result === 'warn')
                            .length > 0 && (
                                <div>
                                    <h4 className="text-sm font-semibold text-accent-yellow mb-2 flex items-center gap-2">
                                        <AlertIcon className="w-4 h-4" />
                                        Warnings
                                    </h4>
                                    <div className="space-y-2">
                                        {Object.entries(certificate.zlintDetails)
                                            .filter(([, v]) => v.result === 'warn')
                                            .map(([key, value]) => (
                                                <div key={key} className="p-3 bg-accent-yellow/10 border border-accent-yellow/20 rounded-lg">
                                                    <p className="text-sm text-text-primary font-medium">{key.replace(/_/g, ' ')}</p>
                                                    {value.details && <p className="text-xs text-text-muted mt-1">{value.details}</p>}
                                                </div>
                                            ))}
                                    </div>
                                </div>
                            )}
                    </div>
                )}
            </div>
        </div>
    );
}
