'use client';

import React from 'react';

interface DonutChartProps {
    value: number;
    maxValue?: number;
    size?: number;
    strokeWidth?: number;
    label?: string;
    sublabel?: string;
    riskLevel?: 'High' | 'Medium' | 'Low';
    className?: string;
    onClick?: () => void;
}

export default function DonutChart({
    value,
    maxValue = 100,
    size = 140,
    strokeWidth = 14,
    label,
    sublabel,
    riskLevel = 'Medium',
    className = '',
    onClick,
}: DonutChartProps) {
    const percentage = Math.min((value / maxValue) * 100, 100);
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (percentage / 100) * circumference;

    // Rotation to start from top
    const rotation = -90;

    // Get gradient based on risk level
    const getGradientColors = () => {
        switch (riskLevel) {
            case 'High':
                return { start: '#ef4444', end: '#f97316' };
            case 'Medium':
                return { start: '#f59e0b', end: '#fbbf24' };
            case 'Low':
                return { start: '#10b981', end: '#06b6d4' };
            default:
                return { start: '#3b82f6', end: '#8b5cf6' };
        }
    };

    const gradientColors = getGradientColors();

    // Get risk level colors
    const getRiskLevelStyle = () => {
        switch (riskLevel) {
            case 'High':
                return {
                    bg: 'bg-gradient-to-r from-accent-red to-accent-orange',
                    text: 'text-white',
                    glow: 'shadow-lg shadow-accent-red/30'
                };
            case 'Medium':
                return {
                    bg: 'bg-gradient-to-r from-accent-yellow to-yellow-400',
                    text: 'text-gray-900',
                    glow: 'shadow-lg shadow-accent-yellow/30'
                };
            case 'Low':
                return {
                    bg: 'bg-gradient-to-r from-accent-green to-primary-cyan',
                    text: 'text-white',
                    glow: 'shadow-lg shadow-accent-green/30'
                };
            default:
                return { bg: 'bg-primary-blue', text: 'text-white', glow: '' };
        }
    };

    const riskStyle = getRiskLevelStyle();

    return (
        <div
            className={`flex flex-col items-center ${onClick ? 'cursor-pointer' : ''} ${className}`}
            onClick={onClick}
        >
            <div className="relative">
                <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
                    <defs>
                        <linearGradient id={`donutGradient-${riskLevel}`} x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor={gradientColors.start} />
                            <stop offset="100%" stopColor={gradientColors.end} />
                        </linearGradient>
                    </defs>

                    {/* Background Circle */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke="var(--card-border)"
                        strokeWidth={strokeWidth}
                    />

                    {/* Progress Circle */}
                    <circle
                        cx={size / 2}
                        cy={size / 2}
                        r={radius}
                        fill="none"
                        stroke={`url(#donutGradient-${riskLevel})`}
                        strokeWidth={strokeWidth}
                        strokeLinecap="round"
                        strokeDasharray={circumference}
                        strokeDashoffset={strokeDashoffset}
                        transform={`rotate(${rotation} ${size / 2} ${size / 2})`}
                        className="transition-all duration-700 ease-out"
                    />
                </svg>

                {/* Center Content */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    {sublabel && (
                        <span className="text-[10px] text-text-muted uppercase tracking-wider mb-1">
                            {sublabel}
                        </span>
                    )}
                    <span className="text-2xl font-bold text-text-primary">{value}%</span>
                </div>
            </div>

            {/* Risk Level Badge */}
            {label && (
                <div className={`mt-4 px-4 py-2 rounded-full ${riskStyle.bg} ${riskStyle.glow}`}>
                    <span className={`text-sm font-bold ${riskStyle.text}`}>{label}</span>
                </div>
            )}
        </div>
    );
}
