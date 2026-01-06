'use client';

import React, { useState } from 'react';
import Card from '@/components/Card';
import Pagination from '@/components/Pagination';
import { AlertIcon, ShieldIcon } from '@/components/icons/Icons';

// Mock vulnerability types
interface Vulnerability {
    id: string;
    name: string;
    severity: 'Critical' | 'High' | 'Medium' | 'Low';
    affectedDomains: number;
    discoveredDate: string;
    status: 'Open' | 'In Progress' | 'Resolved';
    description: string;
}

// Mock vulnerabilities data
const mockVulnerabilities: Vulnerability[] = [
    {
        id: '1',
        name: 'Weak SSL/TLS Protocol',
        severity: 'Critical',
        affectedDomains: 3,
        discoveredDate: 'Oct 23, 2023',
        status: 'Open',
        description: 'TLS 1.0/1.1 protocols in use',
    },
    {
        id: '2',
        name: 'Certificate Chain Incomplete',
        severity: 'High',
        affectedDomains: 5,
        discoveredDate: 'Oct 22, 2023',
        status: 'In Progress',
        description: 'Missing intermediate certificates',
    },
    {
        id: '3',
        name: 'Expired Certificate',
        severity: 'Critical',
        affectedDomains: 1,
        discoveredDate: 'Oct 21, 2023',
        status: 'Open',
        description: 'Certificate has expired',
    },
    {
        id: '4',
        name: 'Weak Cipher Suites',
        severity: 'Medium',
        affectedDomains: 8,
        discoveredDate: 'Oct 20, 2023',
        status: 'In Progress',
        description: 'RC4 and 3DES ciphers detected',
    },
    {
        id: '5',
        name: 'HSTS Not Enabled',
        severity: 'Medium',
        affectedDomains: 12,
        discoveredDate: 'Oct 19, 2023',
        status: 'Open',
        description: 'HTTP Strict Transport Security not configured',
    },
    {
        id: '6',
        name: 'Self-Signed Certificate',
        severity: 'Low',
        affectedDomains: 2,
        discoveredDate: 'Oct 18, 2023',
        status: 'Resolved',
        description: 'Certificate not issued by trusted CA',
    },
    {
        id: '7',
        name: 'Certificate Transparency Missing',
        severity: 'Low',
        affectedDomains: 4,
        discoveredDate: 'Oct 17, 2023',
        status: 'Open',
        description: 'No CT logs found',
    },
    {
        id: '8',
        name: 'Revoked Certificate',
        severity: 'Critical',
        affectedDomains: 1,
        discoveredDate: 'Oct 16, 2023',
        status: 'In Progress',
        description: 'Certificate has been revoked',
    },
];

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
        case 'Open':
            return 'text-accent-red';
        case 'In Progress':
            return 'text-accent-yellow';
        case 'Resolved':
            return 'text-accent-green';
        default:
            return 'text-text-muted';
    }
};

export default function VulnerabilitiesPage() {
    const [vulnerabilities] = useState<Vulnerability[]>(mockVulnerabilities);
    const [currentPage, setCurrentPage] = useState(1);
    const [filter, setFilter] = useState<string>('all');
    const itemsPerPage = 5;

    // Filter vulnerabilities
    const filteredVulnerabilities = filter === 'all'
        ? vulnerabilities
        : vulnerabilities.filter(v => v.severity.toLowerCase() === filter);

    // Paginate
    const totalPages = Math.ceil(filteredVulnerabilities.length / itemsPerPage);
    const paginatedData = filteredVulnerabilities.slice(
        (currentPage - 1) * itemsPerPage,
        currentPage * itemsPerPage
    );

    // Summary stats
    const criticalCount = vulnerabilities.filter(v => v.severity === 'Critical').length;
    const highCount = vulnerabilities.filter(v => v.severity === 'High').length;
    const mediumCount = vulnerabilities.filter(v => v.severity === 'Medium').length;
    const lowCount = vulnerabilities.filter(v => v.severity === 'Low').length;
    const openCount = vulnerabilities.filter(v => v.status === 'Open').length;

    return (
        <div className="space-y-6">
            {/* Page Header */}
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-text-primary">Vulnerabilities</h1>
                    <p className="text-text-muted text-sm mt-1">Monitor and manage security vulnerabilities</p>
                </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-red/15 flex items-center justify-center">
                            <AlertIcon className="w-5 h-5 text-accent-red" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{criticalCount}</p>
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
                            <p className="text-2xl font-bold text-text-primary">{highCount}</p>
                            <p className="text-xs text-text-muted">High</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-yellow/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-yellow" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{mediumCount}</p>
                            <p className="text-xs text-text-muted">Medium</p>
                        </div>
                    </div>
                </Card>

                <Card className="hover-lift">
                    <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-accent-green/15 flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-accent-green" />
                        </div>
                        <div>
                            <p className="text-2xl font-bold text-text-primary">{lowCount}</p>
                            <p className="text-xs text-text-muted">Low</p>
                        </div>
                    </div>
                </Card>
            </div>

            {/* Filter Tabs */}
            <div className="flex items-center gap-2">
                {['all', 'critical', 'high', 'medium', 'low'].map((f) => (
                    <button
                        key={f}
                        onClick={() => { setFilter(f); setCurrentPage(1); }}
                        className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${filter === f
                                ? 'bg-primary-blue text-white'
                                : 'bg-card-bg border border-card-border text-text-secondary hover:text-text-primary'
                            }`}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </button>
                ))}
            </div>

            {/* Vulnerabilities Table */}
            <Card title="Vulnerability Details" subtitle={`${openCount} open vulnerabilities`}>
                <div className="overflow-x-auto">
                    <table className="w-full min-w-[600px]">
                        <thead>
                            <tr className="border-b border-card-border">
                                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase">Vulnerability</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase">Severity</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase">Affected Domains</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase">Discovered</th>
                                <th className="px-4 py-3 text-left text-xs font-semibold text-text-muted uppercase">Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {paginatedData.map((vuln) => (
                                <tr
                                    key={vuln.id}
                                    className="border-b border-card-border hover:bg-background/50 cursor-pointer transition-colors"
                                    onClick={() => console.log('Vulnerability clicked:', vuln)}
                                >
                                    <td className="px-4 py-4">
                                        <p className="font-medium text-text-primary">{vuln.name}</p>
                                        <p className="text-xs text-text-muted">{vuln.description}</p>
                                    </td>
                                    <td className="px-4 py-4">
                                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getSeverityColor(vuln.severity)}`}>
                                            {vuln.severity}
                                        </span>
                                    </td>
                                    <td className="px-4 py-4 text-text-secondary">{vuln.affectedDomains}</td>
                                    <td className="px-4 py-4 text-text-secondary">{vuln.discoveredDate}</td>
                                    <td className="px-4 py-4">
                                        <span className={`text-sm font-medium ${getStatusColor(vuln.status)}`}>
                                            {vuln.status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>

                {totalPages > 1 && (
                    <div className="mt-4 pt-4 border-t border-card-border">
                        <Pagination
                            currentPage={currentPage}
                            totalPages={totalPages}
                            onPageChange={setCurrentPage}
                        />
                    </div>
                )}
            </Card>
        </div>
    );
}
