'use client';

import React, { useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import useSWR from 'swr';
import Card from '@/components/Card';
import ExportButton from '@/components/ExportButton';
import { KeyIcon, AlertIcon, ShieldIcon } from '@/components/icons/Icons';

// TypeScript interfaces
interface CertificateDetail {
    certificate_id: string;
    certificate_fingerprint: string;
    certificate_fingerprint_short: string;
    domain: string;
    sans: string[];
    sans_count: number;
    has_wildcard: boolean;
    wildcard_sans: string[];
    subject_cn: string;
    subject_dn: string;
    issuer_organization: string;
    issuer_cn: string;
    issuer_dn: string;
    issuer_country: string;
    validity_start: string;
    validity_end: string;
    validity_days: number;
    is_expired: boolean;
    days_until_expiry: number | null;
    is_expiring_soon: boolean;
    validation_level: string;
    key_algorithm: string;
    key_size: number;
    key_type: string;
    signature_algorithm: string;
    is_self_signed: boolean;
    serial_number: string;
    extended_key_usage: string[];
    ocsp_urls: string[];
    issuer_urls: string[];
    scanned_at: string | null;
}

interface SharedKeyIssuerInfo {
    organization: string;
    common_name?: string;
    certificate_count: number;
}

interface SharedKeyDetail {
    public_key_hash: string;
    public_key_hash_short: string;
    certificate_count: number;
    total_domains: number;
    sample_domains: string[];
    total_sans: number;
    sample_sans: string[];
    unique_sans: string[];
    key_algorithm: string;
    key_size: number;
    key_type: string;
    issuers: SharedKeyIssuerInfo[];
    issuer_count: number;
    risk_level: 'HIGH' | 'MEDIUM' | 'LOW';
    risk_factors: string[];
    certificates: CertificateDetail[];
    computed_at: string;
    last_updated: string;
}

interface SharedKeyDetailResponse {
    success: boolean;
    data: SharedKeyDetail;
}

const SELECTED_SCOPE_KEY = 'selected_certificate_scope';

const getStoredScope = () => {
    if (typeof window === 'undefined') return 'all';
    const params = new URLSearchParams(window.location.search);
    const urlScope = params.get('scope');
    if (urlScope) return urlScope;
    return localStorage.getItem(SELECTED_SCOPE_KEY) || 'all';
};

// Fetcher for shared key detail
const detailFetcher = async (publicKeyHash: string): Promise<SharedKeyDetail> => {
    const scope = getStoredScope();
    const response = await fetch(`http://localhost:8000/api/shared-keys/detail/${publicKeyHash}/?scope=${encodeURIComponent(scope)}`);
    const json: SharedKeyDetailResponse = await response.json();
    if (!json.success) {
        throw new Error('Failed to fetch shared key details');
    }
    return json.data;
};

export default function SharedKeyDetailPage() {
    const params = useParams();
    const router = useRouter();
    const publicKeyHash = params.publicKeyHash as string;

    const [expandedCertIndex, setExpandedCertIndex] = useState<number | null>(null);

    // Fetch shared key detail
    const { data: detail, isLoading, error } = useSWR<SharedKeyDetail>(
        publicKeyHash ? `shared-key-detail-${publicKeyHash}` : null,
        () => detailFetcher(publicKeyHash),
        { revalidateOnFocus: false, dedupingInterval: 300000 }
    );

    const handleBackClick = () => {
        router.push('/dashboard/shared-keys');
    };

    const toggleCertificate = (index: number) => {
        setExpandedCertIndex(expandedCertIndex === index ? null : index);
    };

    if (isLoading) {
        return (
            <div className="flex items-center justify-center h-screen">
                <div className="text-text-muted">Loading shared key details...</div>
            </div>
        );
    }

    if (error || !detail) {
        return (
            <div className="flex flex-col items-center justify-center h-screen gap-4">
                <div className="text-text-primary text-lg">Failed to load shared key details</div>
                <button onClick={handleBackClick} className="px-4 py-2 bg-primary-blue text-white rounded-lg hover:bg-primary-blue/80 transition-colors">
                    Back to Shared Keys
                </button>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            {/* Header with Back Button */}
            <div className="flex items-center gap-4">
                <button
                    onClick={handleBackClick}
                    className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors flex items-center gap-2"
                >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                    </svg>
                    Back to Shared Keys
                </button>
            </div>

            {/* Title */}
            <div>
                <h1 className="text-2xl font-bold text-text-primary">Shared Key Details</h1>
                <p className="text-text-muted mt-1">
                    {detail.certificate_count} certificates sharing the same public key
                </p>
            </div>

            {/* Overview Cards */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card className="bg-card-bg border border-card-border">
                    <div className="flex items-center gap-3">
                        <KeyIcon className="w-8 h-8 text-primary-blue" />
                        <div>
                            <div className="text-text-secondary text-sm">Key Type</div>
                            <div className="text-text-primary text-xl font-semibold">{detail.key_type}</div>
                        </div>
                    </div>
                </Card>

                <Card className="bg-card-bg border border-card-border">
                    <div className="flex items-center gap-3">
                        <ShieldIcon className="w-8 h-8 text-accent-yellow" />
                        <div>
                            <div className="text-text-secondary text-sm">Certificates</div>
                            <div className="text-text-primary text-xl font-semibold">{detail.certificate_count}</div>
                        </div>
                    </div>
                </Card>

                <Card className="bg-card-bg border border-card-border">
                    <div className="flex items-center gap-3">
                        <AlertIcon className="w-8 h-8 text-accent-red" />
                        <div>
                            <div className="text-text-secondary text-sm">Total SANs at Risk</div>
                            <div className="text-text-primary text-xl font-semibold">{detail.total_sans}</div>
                        </div>
                    </div>
                </Card>

                <Card className="bg-card-bg border border-card-border">
                    <div className="flex items-center gap-3">
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                            detail.risk_level === 'HIGH' ? 'bg-red-500/20 text-red-500' :
                            detail.risk_level === 'MEDIUM' ? 'bg-orange-500/20 text-orange-500' :
                            'bg-green-500/20 text-green-500'
                        }`}>
                            ⚠
                        </div>
                        <div>
                            <div className="text-text-secondary text-sm">Risk Level</div>
                            <div className={`text-xl font-semibold ${
                                detail.risk_level === 'HIGH' ? 'text-red-500' :
                                detail.risk_level === 'MEDIUM' ? 'text-orange-500' :
                                'text-green-500'
                            }`}>{detail.risk_level}</div>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Public Key Hash */}
            <Card title="Public Key Hash">
                <div className="font-mono text-sm text-text-primary break-all bg-card-border/30 p-4 rounded-lg">
                    {detail.public_key_hash}
                </div>
            </Card>

            {/* Risk Factors */}
            <Card title="Risk Factors" infoTooltip="Security implications of this shared key">
                <ul className="space-y-2">
                    {detail.risk_factors.map((factor, idx) => (
                        <li key={idx} className="flex items-start gap-3 text-text-primary">
                            <span className="text-accent-red mt-0.5">•</span>
                            <span>{factor}</span>
                        </li>
                    ))}
                </ul>
            </Card>

            {/* Issuers */}
            <Card
                title="Certificate Authorities"
                subtitle={`${detail.issuer_count} issuer${detail.issuer_count > 1 ? 's' : ''} involved`}
                headerAction={
                    detail.issuers.length > 0 ? (
                        <ExportButton
                            data={detail.issuers.map(issuer => ({
                                Organization: issuer.organization,
                                'Common Name': issuer.common_name || 'N/A',
                                'Certificate Count': issuer.certificate_count,
                            }))}
                            columns={[
                                { header: 'Organization', key: 'Organization' },
                                { header: 'Common Name', key: 'Common Name' },
                                { header: 'Certificate Count', key: 'Certificate Count' },
                            ]}
                            filename="shared-key-issuers"
                            filterLabel="Certificate authorities"
                            totalCount={detail.issuer_count}
                        />
                    ) : undefined
                }
            >
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-card-border">
                                <th className="text-left py-3 px-4 text-text-secondary font-medium">Organization</th>
                                <th className="text-left py-3 px-4 text-text-secondary font-medium">Common Name</th>
                                <th className="text-center py-3 px-4 text-text-secondary font-medium">Certificate Count</th>
                            </tr>
                        </thead>
                        <tbody>
                            {detail.issuers.map((issuer, idx) => (
                                <tr key={idx} className="border-b border-card-border/50">
                                    <td className="py-3 px-4 text-text-primary">{issuer.organization}</td>
                                    <td className="py-3 px-4 text-text-muted">{issuer.common_name || 'N/A'}</td>
                                    <td className="text-center py-3 px-4">
                                        <span className="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold bg-primary-blue/20 text-primary-blue">
                                            {issuer.certificate_count}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>

            {/* All Unique SANs */}
            <Card title="All Unique Subject Alternative Names (SANs)" subtitle={`${detail.unique_sans.length} unique SANs across all certificates`}>
                <div className="bg-card-border/30 p-4 rounded-lg max-h-96 overflow-y-auto">
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                        {detail.unique_sans.map((san, idx) => (
                            <div key={idx} className="text-sm text-text-primary truncate" title={san}>
                                • {san}
                            </div>
                        ))}
                    </div>
                </div>
            </Card>

            {/* Certificates Accordion */}
            <Card title="All Certificates" subtitle={`${detail.certificate_count} certificates with detailed information`}>
                <div className="space-y-2">
                    {detail.certificates.map((cert, index) => (
                        <div key={cert.certificate_fingerprint} className="border border-card-border rounded-lg overflow-hidden">
                            {/* Accordion Header */}
                            <button
                                onClick={() => toggleCertificate(index)}
                                className="w-full flex items-center justify-between px-4 py-3 hover:bg-card-border/20 transition-colors text-left"
                            >
                                <div className="flex items-center gap-4 flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className="text-xs font-mono text-text-muted">
                                            {cert.certificate_fingerprint_short || cert.certificate_fingerprint.substring(0, 16)}...
                                        </span>
                                    </div>
                                    <a 
                                        href={`https://${cert.domain}`} 
                                        target="_blank" 
                                        rel="noopener noreferrer" 
                                        onClick={(e) => e.stopPropagation()}
                                        className="text-sm font-medium text-primary-blue hover:underline"
                                    >
                                        {cert.domain}
                                    </a>
                                    <div className="text-xs text-text-muted">
                                        {cert.sans_count} SAN{cert.sans_count > 1 ? 's' : ''}
                                    </div>
                                </div>
                                <svg
                                    className={`w-5 h-5 text-text-secondary transition-transform ${expandedCertIndex === index ? 'rotate-180' : ''}`}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                </svg>
                            </button>

                            {/* Accordion Content */}
                            {expandedCertIndex === index && (
                                <div className="px-4 py-4 bg-card-border/10 border-t border-card-border">
                                    <div className="space-y-4">
                                        {/* Certificate Fingerprint */}
                                        <div>
                                            <div className="text-xs text-text-secondary mb-1">Certificate Fingerprint (SHA256)</div>
                                            <div className="font-mono text-xs text-text-primary break-all bg-card-bg p-2 rounded">
                                                {cert.certificate_fingerprint}
                                            </div>
                                        </div>

                                        {/* All SANs */}
                                        <div>
                                            <div className="text-xs text-text-secondary mb-2">Subject Alternative Names ({cert.sans_count})</div>
                                            <div className="bg-card-bg p-3 rounded max-h-48 overflow-y-auto">
                                                <div className="grid grid-cols-1 md:grid-cols-2 gap-1.5">
                                                    {cert.sans.map((san, sidx) => (
                                                        <div key={`${cert.certificate_fingerprint}-san-${sidx}`} className="text-xs flex items-start gap-2">
                                                            <span className="text-primary-blue">•</span>
                                                            <a 
                                                                href={`https://${san}`} 
                                                                target="_blank" 
                                                                rel="noopener noreferrer"
                                                                className="text-primary-blue hover:underline break-all"
                                                            >
                                                                {san}
                                                            </a>
                                                        </div>
                                                    ))}
                                                </div>
                                            </div>
                                        </div>

                                        {/* Certificate Details Grid */}
                                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Subject CN</div>
                                                <div className="text-sm text-text-primary">{cert.subject_cn}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Issuer Organization</div>
                                                <div className="text-sm text-text-primary">{cert.issuer_organization}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Issuer CN</div>
                                                <div className="text-sm text-text-primary">{cert.issuer_cn}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Issuer Country</div>
                                                <div className="text-sm text-text-primary">{cert.issuer_country || 'N/A'}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Validity Start</div>
                                                <div className="text-sm text-text-primary">{new Date(cert.validity_start).toLocaleDateString()}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Validity End</div>
                                                {/* COMMENTED: non-deterministic pre-computed fields
                                                <div className={`text-sm ${cert.is_expired ? 'text-accent-red' : cert.is_expiring_soon ? 'text-accent-yellow' : 'text-text-primary'}`}>
                                                */}
                                                <div className="text-sm text-text-primary">
                                                    {new Date(cert.validity_end).toLocaleDateString()}
                                                    {/* COMMENTED: is_expired / is_expiring_soon
                                                    {cert.is_expired && ' (EXPIRED)'}
                                                    {!cert.is_expired && cert.is_expiring_soon && ' (Expiring Soon)'}
                                                    */}
                                                </div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Validity Period</div>
                                                <div className="text-sm text-text-primary">{cert.validity_days} days</div>
                                            </div>
                                            {/* COMMENTED: non-deterministic pre-computed field
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Days Until Expiry</div>
                                                <div className="text-sm text-text-primary">{cert.days_until_expiry != null ? cert.days_until_expiry : 'N/A'}</div>
                                            </div>
                                            */}
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Validation Level</div>
                                                <div className="text-sm text-text-primary">{cert.validation_level}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Key Type</div>
                                                <div className="text-sm text-text-primary">{cert.key_type}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Signature Algorithm</div>
                                                <div className="text-sm text-text-primary">{cert.signature_algorithm}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Self-Signed</div>
                                                <div className="text-sm text-text-primary">{cert.is_self_signed ? 'Yes' : 'No'}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Serial Number</div>
                                                <div className="text-sm text-text-primary font-mono">{cert.serial_number}</div>
                                            </div>
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Has Wildcard</div>
                                                <div className="text-sm text-text-primary">{cert.has_wildcard ? 'Yes' : 'No'}</div>
                                            </div>
                                        </div>

                                        {/* Extended Key Usage */}
                                        {cert.extended_key_usage && cert.extended_key_usage.length > 0 && (
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Extended Key Usage</div>
                                                <div className="text-sm text-text-primary">{cert.extended_key_usage.join(', ')}</div>
                                            </div>
                                        )}

                                        {/* OCSP URLs */}
                                        {cert.ocsp_urls && cert.ocsp_urls.length > 0 && (
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">OCSP URLs</div>
                                                <div className="space-y-1">
                                                    {cert.ocsp_urls.map((url, uidx) => (
                                                        <a 
                                                            key={uidx} 
                                                            href={url} 
                                                            target="_blank" 
                                                            rel="noopener noreferrer"
                                                            className="text-sm text-primary-blue hover:underline break-all block"
                                                        >
                                                            {url}
                                                        </a>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Issuer URLs */}
                                        {cert.issuer_urls && cert.issuer_urls.length > 0 && (
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Issuer URLs</div>
                                                <div className="space-y-1">
                                                    {cert.issuer_urls.map((url, uidx) => (
                                                        <a 
                                                            key={uidx} 
                                                            href={url} 
                                                            target="_blank" 
                                                            rel="noopener noreferrer"
                                                            className="text-sm text-primary-blue hover:underline break-all block"
                                                        >
                                                            {url}
                                                        </a>
                                                    ))}
                                                </div>
                                            </div>
                                        )}

                                        {/* Scanned At */}
                                        {cert.scanned_at && (
                                            <div>
                                                <div className="text-xs text-text-secondary mb-1">Scanned At</div>
                                                <div className="text-sm text-text-primary">{new Date(cert.scanned_at).toLocaleString()}</div>
                                            </div>
                                        )}

                                        {/* More Details Button */}
                                        {cert.certificate_id && (
                                            <div className="pt-4 border-t border-card-border">
                                                <button
                                                    onClick={() => router.push(`/certificate/${cert.certificate_id}`)}
                                                    className="w-full px-4 py-2.5 bg-primary-blue text-white rounded-lg hover:bg-primary-blue/80 transition-colors font-medium text-sm flex items-center justify-center gap-2"
                                                >
                                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                                                    </svg>
                                                    View Full Certificate Details
                                                </button>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </Card>

            {/* Metadata */}
            <Card>
                <div className="flex items-center justify-between text-sm text-text-muted">
                    <div>Computed: {new Date(detail.computed_at).toLocaleString()}</div>
                    <div>Last Updated: {new Date(detail.last_updated).toLocaleString()}</div>
                </div>
            </Card>
        </div>
    );
}
