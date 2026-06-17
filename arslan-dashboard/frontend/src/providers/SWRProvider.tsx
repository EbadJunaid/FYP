'use client';

import React, { ReactNode } from 'react';
import { SWRConfig } from 'swr';

interface SWRProviderProps {
    children: ReactNode;
}

const SELECTED_DB_KEY = 'selected_certificate_database';
const SELECTED_SCOPE_KEY = 'selected_certificate_scope';

const getCurrentScope = () => {
    if (typeof window === 'undefined') return 'all';
    const db = localStorage.getItem(SELECTED_DB_KEY) || 'global';
    if (db === 'pakistani') return 'pk';
    if (db === 'indian') return 'in';
    if (db === 'united-states') return 'us';
    return localStorage.getItem(SELECTED_SCOPE_KEY) || 'all';
};

const appendScope = (url: string) => {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}scope=${encodeURIComponent(getCurrentScope())}`;
};

// Global fetcher function
const fetcher = async (url: string) => {
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000/api';
    const fullUrl = appendScope(url.startsWith('http') ? url : `${apiBase}${url}`);

    const res = await fetch(fullUrl);
    if (!res.ok) {
        const error = new Error('An error occurred while fetching the data.');
        throw error;
    }
    return res.json();
};

/**
 * SWR Provider with global configuration
 * - Stale-while-revalidate pattern for instant UI
 * - Automatic background revalidation
 * - Error retry with exponential backoff
 */
export default function SWRProvider({ children }: SWRProviderProps) {
    return (
        <SWRConfig
            value={{
                fetcher,
                // Revalidation settings
                revalidateOnFocus: false,        // Don't refetch on window focus
                revalidateOnReconnect: true,     // Refetch when network reconnects
                revalidateIfStale: true,         // Revalidate if data is stale

                // Deduplication: prevent multiple identical requests
                dedupingInterval: 2000,          // Dedupe within 2 seconds

                // Error handling
                errorRetryCount: 3,              // Retry failed requests 3 times
                errorRetryInterval: 5000,        // Wait 5s between retries
                shouldRetryOnError: true,

                // Keep previous data while loading new
                keepPreviousData: true,

                // Performance
                focusThrottleInterval: 5000,     // Throttle focus revalidation
            }}
        >
            {children}
        </SWRConfig>
    );
}
