'use client';

import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react';

interface SearchContextType {
    searchQuery: string;
    setSearchQuery: (query: string) => void;
    handleSearch: (query: string) => void;
}

const SearchContext = createContext<SearchContextType | undefined>(undefined);

export function SearchProvider({ children }: { children: ReactNode }) {
    const [searchQuery, setSearchQuery] = useState('');

    const handleSearch = useCallback((query: string) => {
        setSearchQuery(query);
    }, []);

    return (
        <SearchContext.Provider value={{ searchQuery, setSearchQuery, handleSearch }}>
            {children}
        </SearchContext.Provider>
    );
}

export function useSearch() {
    const context = useContext(SearchContext);
    if (context === undefined) {
        throw new Error('useSearch must be used within a SearchProvider');
    }
    return context;
}

// Optional hook that doesn't throw if context is missing (for pages that may work without search)
export function useSearchOptional() {
    return useContext(SearchContext);
}
