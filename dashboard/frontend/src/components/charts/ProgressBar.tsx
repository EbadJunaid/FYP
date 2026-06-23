'use client';

import React from 'react';

interface ProgressBarProps {
    value: number;
    maxValue?: number;
    label?: string;
    showValue?: boolean;
    valueLabel?: string;
    color?: string;
    bgColor?: string;
    height?: 'sm' | 'md' | 'lg';
    className?: string;
    onClick?: () => void;
}

export default function ProgressBar({
    value,
    maxValue = 100,
    label,
    showValue = true,
    valueLabel,
    color = 'bg-primary-blue',
    bgColor = 'bg-card-border',
    height = 'md',
    className = '',
    onClick,
}: ProgressBarProps) {
    const percentage = Math.min((value / maxValue) * 100, 100);

    const heightClasses = {
        sm: 'h-1.5',
        md: 'h-2.5',
        lg: 'h-4',
    };

    return (
        <div
            className={`w-full ${onClick ? 'cursor-pointer' : ''} ${className}`}
            onClick={onClick}
        >
            {/* Label Row */}
            {(label || showValue) && (
                <div className="flex items-center justify-between mb-2">
                    {label && (
                        <span className="text-sm text-text-primary font-medium">{label}</span>
                    )}
                    {showValue && (
                        <span className="text-sm text-text-muted">
                            {valueLabel || `${value}/${maxValue}`}
                        </span>
                    )}
                </div>
            )}

            {/* Progress Bar */}
            <div className={`w-full ${bgColor} rounded-full overflow-hidden ${heightClasses[height]}`}>
                <div
                    className={`${color} h-full rounded-full transition-all duration-500 ease-out`}
                    style={{ width: `${percentage}%` }}
                />
            </div>
        </div>
    );
}
