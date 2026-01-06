'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { usePathname } from 'next/navigation';
import { useTheme } from '@/context/ThemeContext';
import {
    SearchIcon,
    BellIcon,
    SunIcon,
    MoonIcon,
    MenuIcon,
    FilterIcon,
} from '@/components/icons/Icons';

interface HeaderProps {
    onMenuClick: () => void;
    onSearch: (query: string) => void;
    onFilterClick: () => void;
}

// Page title mapping
const pageTitles: Record<string, string> = {
    '/': 'Overview',
    '/dashboard/overview': 'Overview',
    '/dashboard/active-vs-expired': 'Active vs Expired',
    '/dashboard/validity-analytics': 'Validity Analytics',
    '/dashboard/signature-hash': 'Signature & Hash',
    '/dashboard/ca-analytics': 'CA Analytics',
    '/dashboard/san-analytics': 'SAN Analytics',
    '/dashboard/trends': 'Trends',
    '/dashboard/type-distribution': 'Type Distribution',
    '/dashboard/issuer-organizations': 'Issuer Organizations',
    '/dashboard/issuer-countries': 'Issuer Countries',
    '/dashboard/subject-names': 'Subject Names',
    '/dashboard/cas-vs-domains': 'CAs vs Domains',
    '/dashboard/cas-vs-urls': 'CAs vs URLs',
    '/dashboard/cas-vs-public-keys': 'CAs vs Public Keys',
    '/dashboard/shared-public-keys': 'Shared Public Keys',
};

// Notification data type
interface Notification {
    id: string;
    type: 'error' | 'warning' | 'success';
    title: string;
    description: string;
    time: string;
}

// Mock notifications
const mockNotifications: Notification[] = [
    {
        id: '1',
        type: 'error',
        title: 'Critical vulnerability detected',
        description: 'example.com • 2 min ago',
        time: '2 min ago',
    },
    {
        id: '2',
        type: 'warning',
        title: 'Certificate expiring in 7 days',
        description: 'api.example.com • 1 hour ago',
        time: '1 hour ago',
    },
    {
        id: '3',
        type: 'success',
        title: 'Scan completed successfully',
        description: 'blog.example.com • 3 hours ago',
        time: '3 hours ago',
    },
    {
        id: '4',
        type: 'warning',
        title: '3 new vulnerabilities found',
        description: 'staging.app.io • 5 hours ago',
        time: '5 hours ago',
    },
];

export default function Header({ onMenuClick, onSearch, onFilterClick }: HeaderProps) {
    const pathname = usePathname();
    const { theme, toggleTheme } = useTheme();
    const [searchQuery, setSearchQuery] = useState('');
    const [showNotifications, setShowNotifications] = useState(false);
    const searchInputRef = useRef<HTMLInputElement>(null);
    const notificationRef = useRef<HTMLDivElement>(null);

    // Debounce timer ref
    const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

    // Get current page title dynamically
    const currentPageTitle = pageTitles[pathname] || 'Dashboard';

    // Ctrl+K keyboard shortcut to focus search
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                searchInputRef.current?.focus();
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, []);

    // Close notifications when clicking outside
    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (notificationRef.current && !notificationRef.current.contains(e.target as Node)) {
                setShowNotifications(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Debounced search handler
    const debouncedSearch = useCallback((query: string) => {
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        debounceTimerRef.current = setTimeout(() => {
            onSearch(query);
        }, 300);
    }, [onSearch]);

    const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const value = e.target.value;
        setSearchQuery(value);
        debouncedSearch(value);
    };

    const handleSearchSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (debounceTimerRef.current) {
            clearTimeout(debounceTimerRef.current);
        }
        onSearch(searchQuery);
    };

    const getNotificationIcon = (type: string) => {
        switch (type) {
            case 'error':
                return <span className="text-accent-red text-sm">!</span>;
            case 'warning':
                return <span className="text-accent-yellow text-sm">⚠</span>;
            case 'success':
                return <span className="text-accent-green text-sm">✓</span>;
            default:
                return <span className="text-text-muted text-sm">•</span>;
        }
    };

    const getNotificationBg = (type: string) => {
        switch (type) {
            case 'error':
                return 'bg-accent-red/15';
            case 'warning':
                return 'bg-accent-yellow/15';
            case 'success':
                return 'bg-accent-green/15';
            default:
                return 'bg-card-border';
        }
    };

    return (
        <header className="sticky top-0 z-30 bg-background/80 backdrop-blur-lg border-b border-card-border">
            <div className="flex items-center justify-between h-16 px-4 lg:px-6">
                {/* Left Section - Mobile Menu & Breadcrumb */}
                <div className="flex items-center gap-4">
                    {/* Mobile Menu Button */}
                    <button
                        onClick={onMenuClick}
                        className="lg:hidden p-2 rounded-lg text-text-secondary hover:bg-card-bg hover:text-text-primary transition-colors"
                        aria-label="Open menu"
                    >
                        <MenuIcon size={24} />
                    </button>

                    {/* Dynamic Breadcrumb */}
                    <div className="hidden sm:flex items-center gap-2 text-sm">
                        <span className="text-text-primary font-medium">{currentPageTitle}</span>
                        {pathname !== '/' && (
                            <>
                                <span className="text-text-muted">/</span>
                                <span className="text-text-muted">Dashboard</span>
                            </>
                        )}
                    </div>
                </div>

                {/* Center Section - Search */}
                <form onSubmit={handleSearchSubmit} className="flex-1 max-w-xl mx-4">
                    <div className="relative">
                        <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted" />
                        <input
                            ref={searchInputRef}
                            type="text"
                            value={searchQuery}
                            onChange={handleSearchChange}
                            placeholder="Enter domain to analyze..."
                            className="w-full h-10 pl-10 pr-16 bg-card-bg border border-card-border rounded-xl 
                         text-sm text-text-primary placeholder-text-muted
                         focus:outline-none focus:ring-2 focus:ring-primary-blue/50 focus:border-primary-blue
                         transition-all duration-200"
                        />
                        <div className="absolute right-3 top-1/2 -translate-y-1/2 hidden sm:flex items-center gap-1">
                            <kbd className="px-1.5 py-0.5 text-xs text-text-muted bg-background border border-card-border rounded">
                                Ctrl
                            </kbd>
                            <kbd className="px-1.5 py-0.5 text-xs text-text-muted bg-background border border-card-border rounded">
                                K
                            </kbd>
                        </div>
                    </div>
                </form>

                {/* Right Section - Actions */}
                <div className="flex items-center gap-2">
                    {/* Theme Toggle */}
                    <button
                        onClick={toggleTheme}
                        className="p-2.5 rounded-xl text-text-secondary hover:bg-card-bg hover:text-text-primary transition-colors"
                        aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
                    >
                        {theme === 'dark' ? <SunIcon size={20} /> : <MoonIcon size={20} />}
                    </button>

                    {/* Notifications */}
                    <div className="relative" ref={notificationRef}>
                        <button
                            onClick={() => setShowNotifications(!showNotifications)}
                            className="relative p-2.5 rounded-xl text-text-secondary hover:bg-card-bg hover:text-text-primary transition-colors"
                            aria-label="Notifications"
                        >
                            <BellIcon size={20} />
                            {/* Notification Badge */}
                            <span className="absolute top-1 right-1 w-2 h-2 bg-accent-red rounded-full" />
                        </button>

                        {/* Notifications Dropdown */}
                        {showNotifications && (
                            <div className="absolute right-0 top-full mt-2 w-80 bg-card-bg border border-card-border rounded-xl shadow-xl animate-fade-in z-50">
                                <div className="flex items-center justify-between px-4 py-3 border-b border-card-border">
                                    <h3 className="text-sm font-semibold text-text-primary">
                                        Notifications ({mockNotifications.length})
                                    </h3>
                                    <button className="text-xs text-primary-blue hover:text-primary-purple transition-colors">
                                        Mark all read
                                    </button>
                                </div>
                                <div className="p-2 space-y-1 max-h-80 overflow-y-auto">
                                    {mockNotifications.map((notification) => (
                                        <div
                                            key={notification.id}
                                            className="flex gap-3 p-3 rounded-lg hover:bg-background cursor-pointer transition-colors"
                                        >
                                            <div className={`w-8 h-8 rounded-full ${getNotificationBg(notification.type)} flex items-center justify-center flex-shrink-0`}>
                                                {getNotificationIcon(notification.type)}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm text-text-primary">{notification.title}</p>
                                                <p className="text-xs text-text-muted mt-0.5">{notification.description}</p>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                                <div className="px-4 py-3 border-t border-card-border">
                                    <button className="w-full text-xs text-primary-blue hover:text-primary-purple font-medium transition-colors">
                                        View all notifications
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Filters Button */}
                    <button
                        onClick={onFilterClick}
                        className="flex items-center gap-2 px-3 py-2 rounded-xl text-text-secondary hover:bg-card-bg hover:text-text-primary transition-colors border border-card-border"
                        aria-label="Open filters"
                    >
                        <FilterIcon size={18} />
                        <span className="hidden sm:inline text-sm font-medium">Filters</span>
                    </button>
                </div>
            </div>
        </header>
    );
}
