'use client';

import React, { useState, useRef, useEffect } from 'react';
import {
    downloadCSV,
    downloadPDF,
    ExportColumn,
} from '@/utils/exportUtils';

interface ExportButtonProps {
    /** In-memory data array (for inline tables or client-side export) */
    data?: Record<string, unknown>[];
    /** Column definitions */
    columns: ExportColumn[];
    /** Filename (without extension) */
    filename: string;
    /** Server URL for full filtered export (DataTable pages) */
    serverUrl?: string;
    /** Filter label shown in the dropdown */
    filterLabel?: string;
    /** Total record count */
    totalCount?: number;
    /** Optional extra class names */
    className?: string;
}

export default function ExportButton({
    data,
    columns,
    filename,
    serverUrl,
    filterLabel = 'All data',
    totalCount,
    className = '',
}: ExportButtonProps) {
    const [open, setOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const ref = useRef<HTMLDivElement>(null);

    // Close on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false);
            }
        };
        document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, []);

    const handleCSV = () => {
        setOpen(false);
        if (serverUrl) {
            const a = document.createElement('a');
            a.href = serverUrl;
            a.download = `${filename}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        } else if (data) {
            downloadCSV(data, columns, filename);
        }
    };

    const handlePDF = async () => {
        setOpen(false);
        setLoading(true);
        try {
            if (serverUrl) {
                const jsonUrl = serverUrl.includes('?')
                    ? `${serverUrl}&format=json`
                    : `${serverUrl}?format=json`;
                const response = await fetch(jsonUrl);
                if (!response.ok) throw new Error(`Download failed: ${response.statusText}`);
                const allData: Record<string, unknown>[] = await response.json();
                downloadPDF(allData, columns, filename, filename);
            } else if (data) {
                downloadPDF(data, columns, filename, filename);
            }
        } catch (err) {
            console.error('PDF export failed:', err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div ref={ref} className={`relative ${className}`}>
            <button
                onClick={() => setOpen((o) => !o)}
                disabled={loading}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-text-secondary hover:text-primary-blue transition-colors disabled:opacity-50"
            >
                {loading ? (
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                )}
                Export
            </button>

            {open && (
                <div className="absolute right-0 top-full mt-1 z-50 w-56 bg-card-bg border border-card-border rounded-xl shadow-lg overflow-hidden">
                    <div className="px-3 py-2 border-b border-card-border">
                        <p className="text-xs text-text-muted">
                            {loading ? 'Exporting...' : filterLabel}
                        </p>
                        {totalCount !== undefined && !loading && (
                            <p className="text-xs text-text-muted">{totalCount.toLocaleString()} records</p>
                        )}
                    </div>
                    <button
                        onClick={handleCSV}
                        disabled={loading}
                        className="w-full px-3 py-2.5 text-left text-sm text-text-primary hover:bg-background transition-colors flex items-center gap-2"
                    >
                        <svg className="w-4 h-4 text-accent-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        Export as CSV
                    </button>
                    <button
                        onClick={handlePDF}
                        disabled={loading}
                        className="w-full px-3 py-2.5 text-left text-sm text-text-primary hover:bg-background transition-colors flex items-center gap-2 border-t border-card-border"
                    >
                        <svg className="w-4 h-4 text-accent-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
                        </svg>
                        Export as PDF
                    </button>
                </div>
            )}
        </div>
    );
}
