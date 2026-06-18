'use client';

import React, { useState, useEffect } from 'react';
import Card from '@/components/Card';
import Pagination from '@/components/Pagination';
import { AlertIcon, ShieldIcon } from '@/components/icons/Icons';
import { fetchVulnerabilities } from '@/controllers/pageController';
import { Certificate } from '@/services/apiClient';

interface VulnerabilityCertificate extends Certificate {
    vulnerabilityCount: { errors: number; warnings: number };
}

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
    const [certificates, setCertificates] = useState<VulnerabilityCertificate[]>([]);
    const [summary, setSummary] = useState({ critical: 0, warning: 0, total: 0 });
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const pageSize = 10;

    useEffect(() => {
        const loadVulnerabilities = async () => {
            setIsLoading(true);
            setError(null);

            try {
                const data = await fetchVulnerabilities(currentPage, pageSize);
                setCertificates(data.certificates || []);
                setSummary(data.summary || { critical: 0, warning: 0, total: 0 });
                setTotalPages(data.pagination?.totalPages || 1);
            } catch (err) {
                setError('Unable to load vulnerabilities.');
                console.error('Error loading vulnerabilities page:', err);
            } finally {
                setIsLoading(false);
            }
        };

        loadVulnerabilities();
    }, [currentPage]);

    const handlePageChange = (page: number) => {
        setCurrentPage(page);
    };

    const pageTitle = 'Vulnerabilities';
    const vulnerabilityLabel = (cert: VulnerabilityCertificate) => {
        if (cert.vulnerabilityCount.errors > 0) return 'Critical';
        if (cert.vulnerabilityCount.warnings > 0) return 'High';
        return 'Low';
    };

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">{pageTitle}</h1>
                <p className="text-text-muted text-sm mt-1">Review certificates flagged with vulnerabilities</p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-red/15 flex items-center justify-center">
                            <AlertIcon className="w-5 h-5 text-accent-red" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.critical}</p>
                            <p className="text-xs text-text-muted">Critical</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-orange/15 flex items-center justify-center">
                            <AlertIcon className="w-5 h-5 text-accent-orange" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.warning}</p>
                            <p className="text-xs text-text-muted">Warning</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-yellow/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-yellow" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{summary.total}</p>
                            <p className="text-xs text-text-muted">Total Certificates</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-green/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-green" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{certificates.length}</p>
                            <p className="text-xs text-text-muted">On This Page</p>
                        </div>
                    </div>
                </Card>
            </div>

            <Card title="Vulnerability Details" subtitle={`${summary.total} certificates with vulnerabilities`}>
                {isLoading ? (
                    <div className="py-20 text-center text-text-muted">Loading vulnerabilities...</div>
                ) : error ? (
                    <div className="py-20 text-center text-accent-red">{error}</div>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full min-w-[700px]">
                            <thead>
                                <tr className="border-b border-card-border text-left text-xs uppercase text-text-muted">
                                    <th className="px-4 py-3">Domain</th>
                                    <th className="px-4 py-3">Issuer</th>
                                    <th className="px-4 py-3">Severity</th>
                                    <th className="px-4 py-3">Errors</th>
                                    <th className="px-4 py-3">Warnings</th>
                                    <th className="px-4 py-3">Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {certificates.map((cert) => (
                                    <tr key={cert.id} className="border-b border-card-border hover:bg-background/50 transition-colors">
                                        <td className="px-4 py-4">
                                            <p className="font-medium text-text-primary">{cert.domain}</p>
                                            <p className="text-xs text-text-muted">{cert.vulnerabilities || 'No details'}</p>
                                        </td>
                                        <td className="px-4 py-4 text-text-secondary">{cert.issuer}</td>
                                        <td className="px-4 py-4">
                                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(vulnerabilityLabel(cert))}`}>
                                                {vulnerabilityLabel(cert)}
                                            </span>
                                        </td>
                                        <td className="px-4 py-4 text-text-secondary">{cert.vulnerabilityCount.errors}</td>
                                        <td className="px-4 py-4 text-text-secondary">{cert.vulnerabilityCount.warnings}</td>
                                        <td className="px-4 py-4">
                                            <span className={`text-sm font-medium ${getStatusColor(cert.status)}`}>
                                                {cert.status.replace('_', ' ')}
                                            </span>
                                        </td>
                                    </tr>
                                ))}
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
