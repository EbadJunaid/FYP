'use client';

import React, { useState } from 'react';
import GaugeChart from '@/components/charts/GaugeChart';
import { TrendUpIcon } from '@/components/icons/Icons';

// Info icon component
const InfoIcon = ({ className = '' }: { className?: string }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
);

interface GlobalHealthCardProps {
    score: number;
    maxScore: number;
    trend?: number;
    status: 'SECURE' | 'AT_RISK' | 'CRITICAL';
    lastUpdated: string;
    onClick?: () => void;
}

export default function GlobalHealthCard({
    score,
    maxScore,
    trend,
    status,
    
    lastUpdated,
    onClick,
}: GlobalHealthCardProps) {
    const [showTooltip, setShowTooltip] = useState(false);

    const getStatusBadge = () => {
        switch (status) {
            case 'SECURE':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-accent-green text-white">
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                        SECURE
                    </span>
                );
            case 'AT_RISK':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-accent-yellow text-white">
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                        AT RISK
                    </span>
                );
            case 'CRITICAL':
                return (
                    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-accent-red text-white">
                        <span className="w-1.5 h-1.5 rounded-full bg-white" />
                        CRITICAL
                    </span>
                );
        }
    };

    const getGaugeStatus = () => {
        if (score >= 80) return 'secure';
        if (score >= 50) return 'warning';
        return 'critical';
    };

    return (
        <div
            className={`bg-card-bg border border-card-border rounded-2xl p-5 hover-lift transition-all duration-200 ${onClick ? 'cursor-pointer' : ''}`}
            onClick={onClick}
        >
            {/* Title with Info Icon */}
            <div className="flex items-center justify-between mb-4">
                <p className="text-xs text-text-muted uppercase tracking-wider">GLOBAL HEALTH</p>
                <div
                    className="relative"
                    onMouseEnter={() => setShowTooltip(true)}
                    onMouseLeave={() => setShowTooltip(false)}
                    onClick={(e) => e.stopPropagation()}
                >
                    <InfoIcon className="w-4 h-4 text-text-muted hover:text-primary-blue cursor-help transition-colors" />
                    {showTooltip && (
                        <div className="absolute z-50 right-0 top-full mt-2 w-52 px-3 py-2 bg-background border border-card-border rounded-lg shadow-lg text-xs text-text-secondary">
                            <div className="absolute -top-1 right-2 w-2 h-2 bg-background border-l border-t border-card-border rotate-45" />
                            Overall SSL health score based on certificate grades, expiration status, and vulnerability count.
                        </div>
                    )}
                </div>
            </div>

            {/* Main Content Row */}
            <div className="flex items-center justify-between">
                {/* Left Side - Score and Status */}
                <div className="flex flex-col">
                    <div className="flex items-baseline gap-1 mb-3">
                        <span className="text-4xl font-bold text-text-primary">{score}</span>
                        <span className="text-lg text-text-muted">/{maxScore}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        {getStatusBadge()}
                        <span className="text-xs text-text-muted">Updated {lastUpdated}</span>
                    </div>
                </div>

                {/* Right Side - Gauge with Trend Below */}
                <div className="flex flex-col items-center">
                    <GaugeChart
                        value={score}
                        maxValue={maxScore}
                        size={90}
                        strokeWidth={10}
                        status={getGaugeStatus()}
                        showValue={false}
                    />
                    {/* Trend Indicator - Below the gauge */}
                    {/* <div className="flex items-center gap-0.5 mt-1 px-1.5 py-0.5 rounded bg-accent-green/20 text-accent-green text-[10px] font-medium">
                        <TrendUpIcon size={10} />
                        <span>+{trend}%</span>
                    </div> */}
                </div>
            </div>
        </div>
    );
}
