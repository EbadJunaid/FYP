'use client';

import React, { createContext, useContext, useState, useEffect, useRef, ReactNode } from 'react';
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

const THEME_KEY = 'ssl-guardian-theme';

function getInitialTheme(defaultTheme: Theme): Theme {
    if (typeof window === 'undefined') {
        return defaultTheme;
    }

    const savedTheme = window.localStorage.getItem(THEME_KEY) as Theme | null;
    return savedTheme === 'light' || savedTheme === 'dark' ? savedTheme : defaultTheme;
}

export function ThemeProvider({ children, defaultTheme = 'dark' }: ThemeProviderProps) {
    const [theme, setThemeState] = useState<Theme>(defaultTheme);
    const hasLoadedStoredTheme = useRef(false);

    useEffect(() => {
        if (!hasLoadedStoredTheme.current) {
            hasLoadedStoredTheme.current = true;
            const storedTheme = getInitialTheme(defaultTheme);
            const root = document.documentElement;
            root.classList.remove('light', 'dark');
            root.classList.add(storedTheme);
            localStorage.setItem(THEME_KEY, storedTheme);

            if (storedTheme !== theme) {
                queueMicrotask(() => setThemeState(storedTheme));
            }
            return;
        }

        const root = document.documentElement;
        root.classList.remove('light', 'dark');
        root.classList.add(theme);
        localStorage.setItem(THEME_KEY, theme);
    }, [defaultTheme, theme]); // Only re-run when theme actually changes

    const toggleTheme = () => {
        setThemeState(prev => (prev === 'dark' ? 'light' : 'dark'));
    };

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
    };

    // Prevent rendering children until theme is loaded to avoid flash
    // But always provide context to prevent errors
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
