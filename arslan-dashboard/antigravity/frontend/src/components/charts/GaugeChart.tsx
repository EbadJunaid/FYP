'use client';

import React from 'react';

interface GaugeChartProps {
    value: number;
    maxValue?: number;
    size?: number;
    strokeWidth?: number;
    className?: string;
    showValue?: boolean;
    valueLabel?: string;
    status?: 'secure' | 'warning' | 'critical';
}

export default function GaugeChart({
    value,
    maxValue = 100,
    size = 120,
    strokeWidth = 12,
    className = '',
    showValue = true,
    valueLabel,
    status = 'secure',
}: GaugeChartProps) {
    const percentage = Math.min((value / maxValue) * 100, 100);

    // SVG calculations for semi-circle
    const radius = (size - strokeWidth) / 2;
    const circumference = Math.PI * radius; // Half circle
    const strokeDasharray = circumference;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    // Color based on status
    const getGradientId = () => {
        switch (status) {
            case 'secure':
                return 'gaugeGradientGreen';
            case 'warning':
                return 'gaugeGradientYellow';
            case 'critical':
                return 'gaugeGradientRed';
            default:
                return 'gaugeGradientGreen';
        }
    };

    return (
        <div className={`relative inline-flex flex-col items-center ${className}`}>
            <svg
                width={size}
                height={size / 2 + 20}
                viewBox={`0 0 ${size} ${size / 2 + 20}`}
                className="transform"
            >
                {/* Gradient Definitions */}
                <defs>
                    <linearGradient id="gaugeGradientGreen" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#10b981" />
                        <stop offset="50%" stopColor="#06b6d4" />
                        <stop offset="100%" stopColor="#3b82f6" />
                    </linearGradient>
                    <linearGradient id="gaugeGradientYellow" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#f59e0b" />
                        <stop offset="100%" stopColor="#f97316" />
                    </linearGradient>
                    <linearGradient id="gaugeGradientRed" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor="#ef4444" />
                        <stop offset="100%" stopColor="#ec4899" />
                    </linearGradient>
                </defs>

                {/* Background Arc */}
                <path
                    d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
                    fill="none"
                    stroke="var(--card-border)"
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                />

                {/* Foreground Arc */}
                <path
                    d={`M ${strokeWidth / 2} ${size / 2} A ${radius} ${radius} 0 0 1 ${size - strokeWidth / 2} ${size / 2}`}
                    fill="none"
                    stroke={`url(#${getGradientId()})`}
                    strokeWidth={strokeWidth}
                    strokeLinecap="round"
                    strokeDasharray={strokeDasharray}
                    strokeDashoffset={strokeDashoffset}
                    className="transition-all duration-700 ease-out"
                    style={{ transformOrigin: 'center' }}
                />

                {/* Center Value */}
                {showValue && (
                    <text
                        x={size / 2}
                        y={size / 2 - 5}
                        textAnchor="middle"
                        className="fill-text-primary"
                        style={{ fontSize: size / 4, fontWeight: 700 }}
                    >
                        {value}
                    </text>
                )}

                {valueLabel && (
                    <text
                        x={size / 2}
                        y={size / 2 + 15}
                        textAnchor="middle"
                        className="fill-text-muted"
                        style={{ fontSize: size / 10 }}
                    >
                        {valueLabel}
                    </text>
                )}
            </svg>
        </div>
    );
}
