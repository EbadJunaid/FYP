'use client';

import React from 'react';
import Link from 'next/link';
import { TrendUpIcon, TrendDownIcon, ChevronRightIcon } from '@/components/icons/Icons';

interface MetricCardProps {
    icon: React.ReactNode;
    iconBgColor?: string;
    value: string | number;
    label: string;
    trend?: number;
    badge?: {
        text: string;
        variant: 'success' | 'warning' | 'error' | 'info';
    };
    onClick?: () => void;
    detailsLink?: string;
}

export default function MetricCard({
    icon,
    iconBgColor = 'bg-primary-blue/15',
    value,
    label,
    trend,
    badge,
    onClick,
    detailsLink,
}: MetricCardProps) {
    const getBadgeStyles = (variant: 'success' | 'warning' | 'error' | 'info') => {
        switch (variant) {
            case 'success':
                return 'bg-accent-green text-white';
            case 'warning':
                return 'bg-accent-orange text-white';
            case 'error':
                return 'bg-accent-red text-white';
            case 'info':
                return 'bg-primary-blue text-white';
        }
    };

    return (
        <div
            className={`bg-card-bg border border-card-border rounded-2xl p-5 hover-lift transition-all duration-200 ${onClick ? 'cursor-pointer' : ''}`}
            onClick={onClick}
        >
            {/* Top Row - Icon and Badge/Trend */}
            <div className="flex items-start justify-between mb-4">
                {/* Icon */}
                <div className={`w-12 h-12 rounded-xl ${iconBgColor} flex items-center justify-center`}>
                    {icon}
                </div>

                {/* Badge or Trend or View Details */}
                <div className="flex items-center gap-2">
                    {badge && (
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-semibold ${getBadgeStyles(badge.variant)}`}>
                            {badge.text}
                        </span>
                    )}
                    {trend !== undefined && !badge && (
                        <div className={`flex items-center gap-0.5 text-xs ${trend >= 0 ? 'text-accent-green' : 'text-accent-red'}`}>
                            {trend >= 0 ? <TrendUpIcon size={14} /> : <TrendDownIcon size={14} />}
                            <span>{trend >= 0 ? '+' : ''}{trend}%</span>
                        </div>
                    )}
                </div>
            </div>

            {/* Label */}
            <p className="text-xs text-text-muted mb-1">{label}</p>

            {/* Value and View Details */}
            <div className="flex items-end justify-between">
                <p className="text-3xl font-bold text-text-primary">{value}</p>
                {detailsLink && (
                    <Link
                        href={detailsLink}
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 text-xs text-primary-blue hover:text-primary-purple font-medium transition-colors"
                    >
                        View details
                        <ChevronRightIcon className="w-4 h-4" />
                    </Link>
                )}
            </div>
        </div>
    );
}
