'use client';

import React from 'react';
import Link from 'next/link';
import { CardProps } from '@/types/dashboard';
import { ChevronRightIcon } from '@/components/icons/Icons';

interface ExtendedCardProps extends CardProps {
    detailsLink?: string;
    onViewDetails?: () => void;
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
}: ExtendedCardProps) {
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
                    <div>
                        {title && (
                            <h3 className="text-sm font-semibold text-text-primary">{title}</h3>
                        )}
                        {subtitle && (
                            <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>
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
