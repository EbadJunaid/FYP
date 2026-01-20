'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldIcon, ChevronRightIcon } from '@/components/icons/Icons';
import { NavItem } from '@/types/dashboard';

// Navigation items configuration matching the image exactly
const navItems: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: 'overview', href: '/' },
    { id: 'active-vs-expired', label: 'Active vs Expired', icon: 'active', href: '/dashboard/active-vs-expired' },
    { id: 'validity-analytics', label: 'Validity Analytics', icon: 'validity', href: '/dashboard/validity-analytics' },
    { id: 'signature-hash', label: 'Signature & Hash', icon: 'signature', href: '/dashboard/signature-hash' },
    { id: 'ca-analytics', label: 'CA Analytics', icon: 'ca', href: '/dashboard/ca-analytics' },
    { id: 'san-analytics', label: 'SAN Analytics', icon: 'san', href: '/dashboard/san-analytics' },
    { id: 'trends', label: 'Trends', icon: 'trends', href: '/dashboard/trends' },
    // { id: 'type-distribution', label: 'Type Distribution', icon: 'type', href: '/dashboard/type-distribution' },
    // { id: 'issuer-organizations', label: 'Issuer Organizations', icon: 'issuer', href: '/dashboard/issuer-organizations' },
    // { id: 'issuer-countries', label: 'Issuer Countries', icon: 'countries', href: '/dashboard/issuer-countries' },
    // { id: 'subject-names', label: 'Subject Names', icon: 'subject', href: '/dashboard/subject-names' },
    // { id: 'cas-vs-domains', label: 'CAs vs Domains', icon: 'domains', href: '/dashboard/cas-vs-domains' },
    // { id: 'cas-vs-urls', label: 'CAs vs URLs', icon: 'urls', href: '/dashboard/cas-vs-urls' },
    // { id: 'cas-vs-public-keys', label: 'CAs vs Public Keys', icon: 'keys', href: '/dashboard/cas-vs-public-keys' },
    { id: 'shared-keys', label: 'Shared Public Keys', icon: 'shared', href: '/dashboard/shared-keys' },
];

// Sidebar Icon Component
const SidebarIcon: React.FC<{ icon: string; isActive: boolean }> = ({ icon, isActive }) => {
    const className = `w-5 h-5 ${isActive ? 'text-primary-blue' : 'text-sidebar-text'}`;

    const icons: Record<string, React.ReactNode> = {
        overview: (
            <svg className={className} viewBox="0 0 24 24" fill="currentColor">
                <rect x="3" y="3" width="7" height="7" rx="1" />
                <rect x="14" y="3" width="7" height="7" rx="1" />
                <rect x="3" y="14" width="7" height="7" rx="1" />
                <rect x="14" y="14" width="7" height="7" rx="1" />
            </svg>
        ),
        active: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 12l2 2 4-4" />
                <circle cx="12" cy="12" r="9" />
            </svg>
        ),
        validity: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="3" y="4" width="18" height="16" rx="2" />
                <path d="M3 10h18" />
            </svg>
        ),
        signature: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8v4l2 2" />
            </svg>
        ),
        ca: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 2L3 7v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V7l-9-5z" />
            </svg>
        ),
        san: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M4 6h16M4 12h16M4 18h10" />
            </svg>
        ),
        trends: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 20h18M5 17l4-4 4 4 6-8" />
            </svg>
        ),
        type: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 3v9l6 3" />
            </svg>
        ),
        issuer: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <rect x="2" y="7" width="20" height="14" rx="2" />
                <path d="M16 7V5a4 4 0 00-8 0v2" />
            </svg>
        ),
        countries: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <path d="M2 12h20M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z" />
            </svg>
        ),
        subject: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="9" />
                <path d="M12 8v4" />
                <circle cx="12" cy="16" r="1" fill="currentColor" />
            </svg>
        ),
        domains: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M17 21v-2a4 4 0 00-4-4H5a4 4 0 00-4 4v2" />
                <circle cx="9" cy="7" r="4" />
                <path d="M23 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" />
            </svg>
        ),
        urls: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71" />
                <path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71" />
            </svg>
        ),
        keys: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 2l-2 2m-7.61 7.61a5.5 5.5 0 11-7.778 7.778 5.5 5.5 0 017.777-7.777zm0 0L15.5 7.5m0 0l3 3L22 7l-3-3m-3.5 3.5L19 4" />
            </svg>
        ),
        shared: (
            <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="18" cy="5" r="3" />
                <circle cx="6" cy="12" r="3" />
                <circle cx="18" cy="19" r="3" />
                <path d="M8.59 13.51l6.83 3.98M15.41 6.51l-6.82 3.98" />
            </svg>
        ),
    };

    return <>{icons[icon] || icons.overview}</>;
};

interface SidebarProps {
    activeItem?: string;
}

export default function Sidebar({ activeItem }: SidebarProps) {
    const pathname = usePathname();

    // Determine active item from pathname
    const getActiveItem = () => {
        if (activeItem) return activeItem;
        if (pathname === '/') return 'overview';
        const currentPath = pathname.split('/').pop();
        return currentPath || 'overview';
    };

    const currentActive = getActiveItem();

    const handleClick = (e: React.MouseEvent, item: NavItem) => {
        // If clicking Overview and already on root, prevent navigation
        if (item.id === 'overview' && pathname === '/') {
            e.preventDefault();
        }
    };

    return (
        <aside className="fixed left-0 top-0 h-screen w-64 bg-sidebar-bg border-r border-card-border flex-col hidden lg:flex z-40">
            {/* Logo Section */}
            <div className="flex items-center gap-3 px-6 py-5 border-b border-card-border">
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary-blue to-primary-purple flex items-center justify-center">
                    <ShieldIcon className="w-6 h-6 text-white" />
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-lg font-bold text-white">Certificate Analysis</span>
                    <ChevronRightIcon className="w-4 h-4 text-text-muted" />
                </div>
            </div>

            {/* Navigation Menu */}
            <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                    const isActive = item.id === currentActive || pathname === item.href;
                    return (
                        <Link
                            key={item.id}
                            href={item.href}
                            onClick={(e) => handleClick(e, item)}
                            className={`
                flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                transition-all duration-200 group
                ${isActive
                                    ? 'bg-primary-blue/10 text-primary-blue border border-primary-blue/20'
                                    : 'text-sidebar-text hover:bg-white/5 hover:text-white border border-transparent'
                                }
              `}
                        >
                            <SidebarIcon icon={item.icon} isActive={isActive} />
                            <span>{item.label}</span>
                        </Link>
                    );
                })}
            </nav>
        </aside>
    );
}
