'use client';

import React, { useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { CloseIcon, ShieldIcon } from '@/components/icons/Icons';
import { NavItem } from '@/types/dashboard';

// Navigation items configuration matching the sidebar exactly
const navItems: NavItem[] = [
    { id: 'overview', label: 'Overview', icon: 'overview', href: '/' },
    { id: 'active-vs-expired', label: 'Active vs Expired', icon: 'active', href: '/dashboard/active-vs-expired' },
    { id: 'validity-analytics', label: 'Validity Analytics', icon: 'validity', href: '/dashboard/validity-analytics' },
    { id: 'signature-hash', label: 'Signature & Hash', icon: 'signature', href: '/dashboard/signature-hash' },
    { id: 'ca-analytics', label: 'CA Analytics', icon: 'ca', href: '/dashboard/ca-analytics' },
    { id: 'san-analytics', label: 'SAN Analytics', icon: 'san', href: '/dashboard/san-analytics' },
    { id: 'trends', label: 'Trends', icon: 'trends', href: '/dashboard/trends' },
    { id: 'type-distribution', label: 'Type Distribution', icon: 'type', href: '/dashboard/type-distribution' },
    { id: 'issuer-organizations', label: 'Issuer Organizations', icon: 'issuer', href: '/dashboard/issuer-organizations' },
    { id: 'issuer-countries', label: 'Issuer Countries', icon: 'countries', href: '/dashboard/issuer-countries' },
    { id: 'subject-names', label: 'Subject Names', icon: 'subject', href: '/dashboard/subject-names' },
    { id: 'cas-vs-domains', label: 'CAs vs Domains', icon: 'domains', href: '/dashboard/cas-vs-domains' },
    { id: 'cas-vs-urls', label: 'CAs vs URLs', icon: 'urls', href: '/dashboard/cas-vs-urls' },
    { id: 'cas-vs-public-keys', label: 'CAs vs Public Keys', icon: 'keys', href: '/dashboard/cas-vs-public-keys' },
    { id: 'shared-public-keys', label: 'Shared Public Keys', icon: 'shared', href: '/dashboard/shared-public-keys' },
];

interface MobileDrawerProps {
    isOpen: boolean;
    onClose: () => void;
    activeItem?: string;
}

export default function MobileDrawer({ isOpen, onClose, activeItem }: MobileDrawerProps) {
    const pathname = usePathname();

    // Prevent body scroll when drawer is open
    useEffect(() => {
        if (isOpen) {
            document.body.style.overflow = 'hidden';
        } else {
            document.body.style.overflow = 'unset';
        }
        return () => {
            document.body.style.overflow = 'unset';
        };
    }, [isOpen]);

    // Close on escape key
    useEffect(() => {
        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        if (isOpen) {
            window.addEventListener('keydown', handleEscape);
        }
        return () => window.removeEventListener('keydown', handleEscape);
    }, [isOpen, onClose]);

    if (!isOpen) return null;

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
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 lg:hidden">
            {/* Overlay */}
            <div
                className="absolute inset-0 bg-black/40 backdrop-blur-sm"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Drawer */}
            <aside className="absolute left-0 top-0 h-full w-72 bg-sidebar-bg border-r border-card-border flex flex-col animate-fade-in">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-5 border-b border-card-border">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary-blue to-primary-purple flex items-center justify-center">
                            <ShieldIcon className="w-5 h-5 text-white" />
                        </div>
                        <span className="text-lg font-bold text-white">Certificate Analysis</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 rounded-lg text-text-muted hover:text-white hover:bg-white/10 transition-colors"
                        aria-label="Close menu"
                    >
                        <CloseIcon size={20} />
                    </button>
                </div>

                {/* Navigation Menu */}
                <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
                    {navItems.map((item) => {
                        const isActive = item.id === currentActive || pathname === item.href;
                        return (
                            <Link
                                key={item.id}
                                href={item.href}
                                onClick={(e) => handleClick(e, item)}
                                className={`
                  flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium
                  transition-all duration-200
                  ${isActive
                                        ? 'bg-primary-blue/10 text-primary-blue border border-primary-blue/20'
                                        : 'text-sidebar-text hover:bg-white/5 hover:text-white border border-transparent'
                                    }
                `}
                            >
                                <span className="w-2 h-2 rounded-full bg-current opacity-50" />
                                <span>{item.label}</span>
                            </Link>
                        );
                    })}
                </nav>
            </aside>
        </div>
    );
}
