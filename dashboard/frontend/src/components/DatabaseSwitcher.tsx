'use client';

import React, { useState, useRef, useEffect, useMemo } from 'react';
import { ChevronDownIcon } from '@heroicons/react/24/outline';
import { SearchIcon } from '@/components/icons/Icons';

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
const THEME_KEY = 'ssl-guardian-theme';

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
    const [countrySearch, setCountrySearch] = useState('');
    const dropdownRef = useRef<HTMLDivElement>(null);
    const searchInputRef = useRef<HTMLInputElement>(null);

    const filteredDatabases = useMemo(() => {
        const query = countrySearch.trim().toLowerCase();
        if (!query) return availableDatabases;

        return availableDatabases.filter((db) => {
            const searchable = [
                db.name,
                db.description || '',
                db.scope,
                db.id,
            ].join(' ').toLowerCase();
            return searchable.includes(query);
        });
    }, [availableDatabases, countrySearch]);

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

    useEffect(() => {
        const handleShortcut = (event: KeyboardEvent) => {
            if (event.altKey && event.key.toLowerCase() === 'k') {
                event.preventDefault();
                setIsOpen(true);
                setTimeout(() => searchInputRef.current?.focus(), 0);
            }
        };

        window.addEventListener('keydown', handleShortcut);
        return () => window.removeEventListener('keydown', handleShortcut);
    }, []);

    useEffect(() => {
        if (isOpen) {
            setTimeout(() => searchInputRef.current?.focus(), 0);
        }
    }, [isOpen]);

    const handleDatabaseChange = async (database: Database) => {
        if (isSwitching || database.id === currentDb.id) {
            setIsOpen(false);
            return;
        }
        
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
            const theme = localStorage.getItem(THEME_KEY);
            localStorage.clear();
            sessionStorage.clear();
            if (theme) localStorage.setItem(THEME_KEY, theme);
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
                <span className="text-xs text-text-muted hidden sm:inline">Country:</span>
                <span>{isSwitching ? 'Switching...' : (currentDb.name || '').replace(/\s*domains$/i, '')}</span>
                {!isSwitching && (
                    <ChevronDownIcon className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
                )}
                {isSwitching && (
                    <div className="w-4 h-4 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
                )}
            </button>

            {isOpen && (
                <div className="absolute right-0 top-full mt-2 w-72 bg-card-bg border border-card-border rounded-lg shadow-lg z-50">
                    <div className="p-3 border-b border-card-border">
                        <div className="relative">
                            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted" />
                        <input
                            ref={searchInputRef}
                            value={countrySearch}
                            onChange={(event) => setCountrySearch(event.target.value)}
                            placeholder="Search country"
                            className="w-full h-9 rounded-full border border-border bg-background pl-9 pr-16 text-sm text-text-primary outline-none transition placeholder:text-text-muted focus:border-primary-blue focus:ring-2 focus:ring-primary-blue/20"
                        />
                            <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1">
                                <kbd className="px-1.5 py-0.5 text-[10px] text-text-muted bg-background border border-card-border rounded">Alt</kbd>
                                <kbd className="px-1.5 py-0.5 text-[10px] text-text-muted bg-background border border-card-border rounded">K</kbd>
                            </div>
                        </div>
                    </div>

                    <div className="max-h-56 overflow-y-auto overscroll-contain">
                        {filteredDatabases.length > 0 ? (
                            filteredDatabases.map((db) => (
                                <button
                                    key={db.id}
                                    onClick={() => handleDatabaseChange(db)}
                                    className={`w-full px-4 py-3 text-left hover:bg-card-bg-hover transition-colors ${
                                        currentDb.id === db.id ? 'bg-primary-blue/10' : ''
                                    }`}
                                >
                                    <div className="flex items-center justify-between gap-3">
                                        <div className="min-w-0">
                                                        <div className="truncate text-sm font-medium text-text-primary">{db.name.replace(/\s*domains$/i, '')}</div>
                                                        <div className="mt-0.5 truncate text-xs text-text-muted">{db.description}</div>
                                        </div>
                                        {currentDb.id === db.id && (
                                            <div className="h-2 w-2 shrink-0 rounded-full bg-accent-green"></div>
                                        )}
                                    </div>
                                </button>
                            ))
                        ) : (
                            <div className="px-4 py-6 text-center text-sm text-text-muted">
                                No such country available
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}
