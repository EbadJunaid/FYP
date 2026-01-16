'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { CardProps } from '@/types/dashboard';
import { ChevronRightIcon } from '@/components/icons/Icons';

// Info icon component
const InfoIcon = ({ className = '' }: { className?: string }) => (
    <svg
        className={className}
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
    >
        <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
        />
    </svg>
);

interface ExtendedCardProps extends CardProps {
    detailsLink?: string;
    onViewDetails?: () => void;
    infoTooltip?: string; // New prop for tooltip text
}

export default function Card({
    title,
    subtitle,
    headerAction,
    children,
    className = '',
    onClick,
    isClickable = false,
    detailsLink,
    onViewDetails,
    infoTooltip,
}: ExtendedCardProps) {
    const [showTooltip, setShowTooltip] = useState(false);

    const handleClick = () => {
        if (onClick && isClickable) {
            onClick();
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (isClickable && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            onClick?.();
        }
    };

    const handleViewDetails = (e: React.MouseEvent) => {
        e.stopPropagation();
        onViewDetails?.();
    };

    return (
        <div
            className={`
        bg-card-bg border border-card-border rounded-2xl overflow-hidden
        transition-all duration-200 flex flex-col
        ${isClickable ? 'cursor-pointer hover-lift' : ''}
        ${className}
      `}
            onClick={handleClick}
            onKeyDown={handleKeyDown}
            role={isClickable ? 'button' : undefined}
            tabIndex={isClickable ? 0 : undefined}
        >
            {/* Card Header */}
            {(title || headerAction || detailsLink) && (
                <div className="flex items-center justify-between px-5 py-4 border-b border-card-border">
                    <div className="flex items-center gap-2">
                        <div>
                            {title && (
                                <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
                            )}
                            {subtitle && (
                                <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
                            )}
                        </div>
                        {/* Info Icon with Tooltip */}
                        {infoTooltip && (
                            <div
                                className="relative"
                                onMouseEnter={() => setShowTooltip(true)}
                                onMouseLeave={() => setShowTooltip(false)}
                                onClick={(e) => e.stopPropagation()}
                            >
                                <InfoIcon className="w-4 h-4 text-text-muted hover:text-primary-blue cursor-help transition-colors" />
                                {showTooltip && (
                                    <div className="absolute z-50 left-1/2 -translate-x-1/2 top-full mt-2 w-48 px-3 py-2 bg-background border border-card-border rounded-lg shadow-lg text-xs text-text-secondary">
                                        <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-2 h-2 bg-background border-l border-t border-card-border rotate-45" />
                                        {infoTooltip}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                    <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        {headerAction}
                        {detailsLink && (
                            <Link
                                href={detailsLink}
                                className="flex items-center gap-1 text-xs text-primary-blue hover:text-primary-purple font-medium transition-colors"
                            >
                                View details
                                <ChevronRightIcon className="w-4 h-4" />
                            </Link>
                        )}
                        {onViewDetails && !detailsLink && (
                            <button
                                onClick={handleViewDetails}
                                className="flex items-center gap-1 text-xs text-primary-blue hover:text-primary-purple font-medium transition-colors"
                            >
                                View details
                                <ChevronRightIcon className="w-4 h-4" />
                            </button>
                        )}
                    </div>
                </div>
            )}

            {/* Card Content */}
            <div className="p-5 flex-1">
                {children}
            </div>
        </div>
    );
}
