'use client';

import React from 'react';
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from 'recharts';
import { ValidityTrendPoint } from '@/types/dashboard';

interface LineChartComponentProps {
    data: ValidityTrendPoint[];
    onClick?: () => void;
    className?: string;
}

// Custom Tooltip Component
const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number }>;
    label?: string;
}) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-sidebar-bg border border-card-border rounded-lg px-3 py-2 shadow-lg">
                <p className="text-xs text-text-muted">{label}</p>
                <p className="text-sm font-semibold text-primary-blue">
                    {payload[0].value} expirations
                </p>
            </div>
        );
    }
    return null;
};

export default function LineChartComponent({
    data,
    onClick,
    className = '',
}: LineChartComponentProps) {
    return (
        <div
            className={`w-full h-full min-h-[180px] ${onClick ? 'cursor-pointer' : ''} ${className}`}
            onClick={onClick}
        >
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart
                    data={data}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                >
                    <defs>
                        <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.4} />
                            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                    <CartesianGrid
                        strokeDasharray="3 3"
                        stroke="var(--card-border)"
                        vertical={false}
                    />
                    <XAxis
                        dataKey="month"
                        tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                        axisLine={{ stroke: 'var(--card-border)' }}
                        tickLine={false}
                    />
                    <YAxis
                        tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                        axisLine={false}
                        tickLine={false}
                    />
                    <Tooltip content={<CustomTooltip />} />
                    <Area
                        type="monotone"
                        dataKey="expirations"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        fill="url(#areaGradient)"
                        dot={{
                            r: 4,
                            fill: '#3b82f6',
                            stroke: '#1e293b',
                            strokeWidth: 2,
                        }}
                        activeDot={{
                            r: 6,
                            fill: '#3b82f6',
                            stroke: 'white',
                            strokeWidth: 2,
                        }}
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
