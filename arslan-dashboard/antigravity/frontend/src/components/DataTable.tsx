'use client';

import React from 'react';
import { ScanEntry, SSLGrade, CertificateStatus } from '@/types/dashboard';
import { GlobeIcon } from '@/components/icons/Icons';
import Pagination from '@/components/Pagination';

interface DataTableProps {
    data: ScanEntry[];
    onRowClick?: (entry: ScanEntry) => void;
    className?: string;
    // Pagination props
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
    showPagination?: boolean;
}

// SSL Grade Badge Component
const GradeBadge: React.FC<{ grade: SSLGrade }> = ({ grade }) => {
    const getGradeStyles = () => {
        if (grade === 'A+' || grade === 'A' || grade === 'A-') {
            return 'grade-a';
        } else if (grade === 'B+' || grade === 'B') {
            return 'grade-b';
        } else if (grade === 'C') {
            return 'grade-c';
        } else {
            return 'grade-f';
        }
    };

    return (
        <span className={`inline-flex items-center justify-center w-9 h-7 rounded-md text-xs font-bold ${getGradeStyles()}`}>
            {grade}
        </span>
    );
};

// Status Badge Component
const StatusBadge: React.FC<{ status: CertificateStatus }> = ({ status }) => {
    const getStatusStyles = () => {
        switch (status) {
            case 'VALID':
                return { dot: 'bg-accent-green', text: 'text-accent-green' };
            case 'EXPIRED':
                return { dot: 'bg-accent-red', text: 'text-accent-red' };
            case 'WEAK':
                return { dot: 'bg-accent-orange', text: 'text-accent-orange' };
            case 'EXPIRING_SOON':
                return { dot: 'bg-accent-yellow', text: 'text-accent-yellow' };
            default:
                return { dot: 'bg-text-muted', text: 'text-text-muted' };
        }
    };

    const styles = getStatusStyles();

    return (
        <span className={`inline-flex items-center gap-1.5 ${styles.text}`}>
            <span className={`w-2 h-2 rounded-full ${styles.dot}`} />
            <span className="text-xs font-medium">{status.replace('_', ' ')}</span>
        </span>
    );
};

// Vulnerabilities Badge
const VulnBadge: React.FC<{ text: string }> = ({ text }) => {
    const isCritical = text.toLowerCase().includes('critical');
    const isLow = text.toLowerCase().includes('low');
    const isMedium = text.toLowerCase().includes('medium');
    const isNone = text.toLowerCase().includes('found');

    let colorClass = 'text-text-muted';
    if (isCritical) colorClass = 'text-accent-red';
    else if (isMedium) colorClass = 'text-accent-orange';
    else if (isLow) colorClass = 'text-accent-yellow';
    else if (isNone) colorClass = 'text-accent-green';

    return <span className={`text-sm ${colorClass}`}>{text}</span>;
};

export default function DataTable({
    data,
    onRowClick,
    className = '',
    currentPage,
    totalPages,
    onPageChange,
    showPagination = true,
}: DataTableProps) {
    const handleRowClick = (entry: ScanEntry) => {
        console.log('Row clicked:', entry);
        onRowClick?.(entry);
    };

    return (
        <div className={`w-full ${className}`}>
            {/* Table Container with responsive scroll */}
            <div className="overflow-x-auto xl:overflow-x-visible">
                <table className="w-full min-w-[800px]">
                    <thead>
                        <tr className="border-b border-card-border">
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                Domain
                            </th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                Scan Date
                            </th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                SSL Grade
                            </th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                Vulnerabilities
                            </th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                Issuer
                            </th>
                            <th className="text-left py-3 px-4 text-xs font-semibold text-text-muted uppercase tracking-wider">
                                Status
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.length === 0 ? (
                            <tr>
                                <td colSpan={6} className="py-8 text-center text-text-muted">
                                    No data available
                                </td>
                            </tr>
                        ) : (
                            data.map((entry) => (
                                <tr
                                    key={entry.id}
                                    onClick={() => handleRowClick(entry)}
                                    className="border-b border-card-border table-row-hover cursor-pointer transition-colors"
                                >
                                    <td className="py-4 px-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-8 h-8 rounded-lg bg-primary-blue/15 flex items-center justify-center">
                                                <GlobeIcon className="w-4 h-4 text-primary-blue" />
                                            </div>
                                            <span className="text-sm font-medium text-text-primary">{entry.domain}</span>
                                        </div>
                                    </td>
                                    <td className="py-4 px-4">
                                        <span className="text-sm text-text-secondary">{entry.scanDate}</span>
                                    </td>
                                    <td className="py-4 px-4">
                                        <GradeBadge grade={entry.sslGrade} />
                                    </td>
                                    <td className="py-4 px-4">
                                        <VulnBadge text={entry.vulnerabilities} />
                                    </td>
                                    <td className="py-4 px-4">
                                        <span className="text-sm text-text-secondary">{entry.issuer}</span>
                                    </td>
                                    <td className="py-4 px-4">
                                        <StatusBadge status={entry.status} />
                                    </td>
                                </tr>
                            ))
                        )}
                    </tbody>
                </table>
            </div>

            {/* Pagination */}
            {showPagination && totalPages > 0 && (
                <Pagination
                    currentPage={currentPage}
                    totalPages={totalPages}
                    onPageChange={onPageChange}
                />
            )}
        </div>
    );
}
