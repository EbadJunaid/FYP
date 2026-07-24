'use client';

import React from 'react';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import { ScanEntry } from '@/types/dashboard';

interface RecentScansCardProps {
    data: ScanEntry[];
    title?: string;
    onRowClick?: (entry: ScanEntry) => void;
    headerAction?: React.ReactNode;
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
}

export default function RecentScansCard({
    data,
    title = 'Recent Scans',
    onRowClick,
    headerAction,
    currentPage,
    totalPages,
    onPageChange,
}: RecentScansCardProps) {
    return (
        <Card
            title={title}
            headerAction={headerAction}
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
