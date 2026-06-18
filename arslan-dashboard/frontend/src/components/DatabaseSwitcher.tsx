'use client';

import React, { useState, useRef, useEffect } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';

interface Database {
    id: string;
    name: string;
    description?: string;
    mainDb?: string;
    resultsDb?: string;
    main?: string;
    results?: string;
    main_db?: string;
    results_db?: string;
    scope: string;
}

const DEFAULT_DATABASE: Database = {
    id: 'global',
    name: 'Global',
    description: 'All certificates',
    scope: 'all'
};

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';
const SELECTED_DB_KEY = 'selected_certificate_database';
const SELECTED_SCOPE_KEY = 'selected_certificate_scope';

const normalizeDatabases = (data: Record<string, Omit<Database, 'id'> & { id?: string }>): Database[] => {
    const databases = Object.entries(data || {}).map(([id, config]) => ({
        id: config.id || id,
        name: config.name || id,
        description: config.description || `${config.scope || 'all'} scope`,
        mainDb: config.mainDb || config.main || config.main_db,
        resultsDb: config.resultsDb || config.results || config.results_db,
        scope: config.scope || 'all',
    }));
    return databases.length ? databases : [DEFAULT_DATABASE];
};

/**
 * Database Switcher Component
 * Dropdown to switch between different MongoDB databases
 */
export default function DatabaseSwitcher() {
    const [isOpen, setIsOpen] = useState(false);
    const [availableDatabases, setAvailableDatabases] = useState<Database[]>([DEFAULT_DATABASE]);
    const [currentDb, setCurrentDb] = useState<Database>(DEFAULT_DATABASE);
    const [isSwitching, setIsSwitching] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    // On mount, fetch the actual current database from backend
    useEffect(() => {
        const fetchCurrentDb = async () => {
            try {
                const params = new URLSearchParams(window.location.search);
                const dbFromUrl = params.get('db');
                const scopeFromUrl = params.get('scope');
                const storedDb = localStorage.getItem(SELECTED_DB_KEY);
                const storedScope = localStorage.getItem(SELECTED_SCOPE_KEY);
                const preferredDbId = dbFromUrl || storedDb;

                const availableResponse = await fetch(`${API_BASE_URL}/databases/available/`);
                const availableData = availableResponse.ok ? await availableResponse.json() : {};
                const databases = normalizeDatabases(availableData);
                setAvailableDatabases(databases);

                const preferredDb = databases.find(d => d.id === preferredDbId);
                const preferredScope = scopeFromUrl || preferredDb?.scope || storedScope || 'all';
                const currentResponse = await fetch(`${API_BASE_URL}/databases/current/?scope=${encodeURIComponent(preferredScope)}`);
                const currentData = currentResponse.ok ? await currentResponse.json() : null;
                const db = preferredDb
                    || databases.find(d => d.scope === preferredScope)
                    || databases.find(d => d.id === currentData?.id)
                    || DEFAULT_DATABASE;

                setCurrentDb(db);
                localStorage.setItem(SELECTED_DB_KEY, db.id);
                localStorage.setItem(SELECTED_SCOPE_KEY, db.scope);

                if (scopeFromUrl !== db.scope) {
                    const nextParams = new URLSearchParams(window.location.search);
                    nextParams.set('db', db.id);
                    nextParams.set('scope', db.scope);
                    window.history.replaceState(null, '', `${window.location.pathname}?${nextParams.toString()}`);
                }
            } catch (error) {
                console.error('Error fetching current database:', error);
            }
        };
        fetchCurrentDb();
    }, []);

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
                setIsOpen(false);
            }
        };

        if (isOpen) {
            document.addEventListener('mousedown', handleClickOutside);
        }

        return () => {
            document.removeEventListener('mousedown', handleClickOutside);
        };
    }, [isOpen]);

    const handleDatabaseChange = async (database: Database) => {
        if (isSwitching || database.id === currentDb.id) return;
        
        setIsSwitching(true);
        setIsOpen(false);
        
        try {
            // Call backend API to switch database
            const response = await fetch(`${API_BASE_URL}/databases/switch/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ database_id: database.id }),
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Failed to switch database');
            }
            
            const result = await response.json();
            console.log('Database switched successfully:', result);
            
            // Update local state
            setCurrentDb(database);
            
            // Clear all browser caches to ensure fresh data
            if ('caches' in window) {
                // Clear all cache storage
                caches.keys().then(names => {
                    names.forEach(name => {
                        caches.delete(name);
                    });
                });
            }
            
            // Clear localStorage and sessionStorage (except theme preferences)
            const theme = localStorage.getItem('theme');
            localStorage.clear();
            sessionStorage.clear();
            if (theme) localStorage.setItem('theme', theme);
            localStorage.setItem(SELECTED_DB_KEY, database.id);
            localStorage.setItem(SELECTED_SCOPE_KEY, database.scope);
            
            // Store the new database ID to verify after reload
            sessionStorage.setItem('switched_db', database.id);
            
            // Force hard reload with cache bypass
            window.location.href = window.location.href.split('?')[0]
                + '?db=' + encodeURIComponent(database.id)
                + '&scope=' + encodeURIComponent(database.scope)
                + '&t=' + Date.now();
            
        } catch (error) {
            console.error('Error switching database:', error);
            alert(`Failed to switch database: ${error instanceof Error ? error.message : 'Unknown error'}`);
            setIsSwitching(false);
        }
    };

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                onClick={() => setIsOpen(!isOpen)}
                disabled={isSwitching}
                className="flex items-center gap-2 px-3 py-1.5 bg-card-bg border border-card-border rounded-lg text-sm text-text-primary font-medium hover:bg-card-bg-hover transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
                <span className="text-xs text-text-muted hidden sm:inline">Database:</span>
                <span>{isSwitching ? 'Switching...' : currentDb.name}</span>
                {!isSwitching && (
                    <ChevronDownIcon className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                )}
                {isSwitching && (
                    <div className="w-4 h-4 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 top-full mt-2 w-64 bg-card-bg border border-card-border rounded-lg shadow-lg z-50">
                    {availableDatabases.map((db) => (
                        <button
                            key={db.id}
                            onClick={() => handleDatabaseChange(db)}
                            className={`w-full px-4 py-3 text-left hover:bg-card-bg-hover transition-colors first:rounded-t-lg last:rounded-b-lg ${
                                currentDb.id === db.id ? 'bg-primary-blue/10' : ''
                            }`}
                        >
                            <div className="flex items-center justify-between">
                                <div>
                                    <div className="text-sm font-medium text-text-primary">{db.name}</div>
                                    <div className="text-xs text-text-muted mt-0.5">{db.description}</div>
                                </div>
                                {currentDb.id === db.id && (
                                    <div className="w-2 h-2 rounded-full bg-accent-green"></div>
                                )}
                            </div>
                        </button>
                    ))}
                </div>
            )}
        </div>
    );
}
