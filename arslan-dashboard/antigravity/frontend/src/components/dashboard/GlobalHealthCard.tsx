'use client';

import React from 'react';
import GaugeChart from '@/components/charts/GaugeChart';
import { TrendUpIcon } from '@/components/icons/Icons';

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
            {/* Title */}
            <p className="text-xs text-text-muted uppercase tracking-wider mb-4">GLOBAL HEALTH</p>

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
                    <div className="flex items-center gap-0.5 mt-1 px-1.5 py-0.5 rounded bg-accent-green/20 text-accent-green text-[10px] font-medium">
                        <TrendUpIcon size={10} />
                        <span>+{trend}%</span>
                    </div>
                </div>
            </div>
        </div>
    );
}
