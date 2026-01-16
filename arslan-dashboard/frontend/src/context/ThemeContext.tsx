'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Theme } from '@/types/dashboard';

interface ThemeContextType {
    theme: Theme;
    toggleTheme: () => void;
    setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

interface ThemeProviderProps {
    children: ReactNode;
    defaultTheme?: Theme;
}

export function ThemeProvider({ children, defaultTheme = 'dark' }: ThemeProviderProps) {
    const [theme, setThemeState] = useState<Theme>(defaultTheme);
    const [mounted, setMounted] = useState(false);

    // Load theme from localStorage on mount
    useEffect(() => {
        setMounted(true);
        const savedTheme = localStorage.getItem('ssl-guardian-theme') as Theme | null;
        if (savedTheme && (savedTheme === 'light' || savedTheme === 'dark')) {
            setThemeState(savedTheme);
        }
    }, []);

    // Apply theme class to document
    useEffect(() => {
        if (mounted) {
            const root = document.documentElement;
            root.classList.remove('light', 'dark');
            root.classList.add(theme);
            localStorage.setItem('ssl-guardian-theme', theme);
        }
    }, [theme, mounted]);

    const toggleTheme = () => {
        setThemeState(prev => (prev === 'dark' ? 'light' : 'dark'));
    };

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
    };

    // Always provide context, even before mount
    return (
        <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (context === undefined) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}
