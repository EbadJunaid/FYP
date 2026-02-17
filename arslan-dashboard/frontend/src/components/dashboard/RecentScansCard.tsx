'use client';

import React from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import { DownloadIcon } from '@/components/icons/Icons';
import { ScanEntry } from '@/types/dashboard';

interface RecentScansCardProps {
    data: ScanEntry[];
    title?: string; // Dynamic title based on active filter
    onRowClick?: (entry: ScanEntry) => void;
    onDownloadClick?: () => void;
    // Pagination props
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

export default function RecentScansCard({
    data,
    title = 'Recent Scans', // Default title
    onRowClick,
    onDownloadClick,
    currentPage,
    totalPages,
    onPageChange,
}: RecentScansCardProps) {
    return (
        <Card
            title={title}
            headerAction={
                <button
                    onClick={onDownloadClick}
                    className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-background transition-colors"
                    aria-label="Download scans"
                >
                    <DownloadIcon size={18} />
                </button>
            }
            infoTooltip="List of SSL certificates with key details. Click on a row to view certificate details."
        >
            <DataTable
                data={data}
                onRowClick={onRowClick}
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={onPageChange}
                showPagination={true}
            />
        </Card>
    );
}
