'use client';

import { useEffect, useState } from 'react';

/**
 * Hook to generate cache-busting SWR keys that include database URL parameters.
 * This ensures SWR fetches fresh data when the database is switched.
 *
 * @param baseKey - The base SWR key (e.g., 'overview-metrics')
 * @returns A unique key including database parameters from the URL
 */
export function useDatabaseKey(baseKey: string): string {
    const [key, setKey] = useState(() => {
        // Initialize on mount
        if (typeof window === 'undefined') {
            return `${baseKey}|db:default|t:`;
        }
        const params = new URLSearchParams(window.location.search);
        const db = params.get('db') || 'default';
        const timestamp = params.get('t') || '';
        return `${baseKey}|db:${db}|t:${timestamp}`;
    });

    useEffect(() => {
        // Update when component mounts or URL changes
        const updateKey = () => {
            if (typeof window !== 'undefined') {
                const params = new URLSearchParams(window.location.search);
                const db = params.get('db') || 'default';
                const timestamp = params.get('t') || '';
                setKey(`${baseKey}|db:${db}|t:${timestamp}`);
            }
        };

        updateKey();

        // Listen for popstate events (back/forward navigation)
        window.addEventListener('popstate', updateKey);
        
        return () => {
            window.removeEventListener('popstate', updateKey);
        };
    }, [baseKey]);

    return key;
}
