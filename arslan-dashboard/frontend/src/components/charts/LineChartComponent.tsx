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
    onDataPointClick?: (dataPoint: ValidityTrendPoint) => void;
    className?: string;
}

// Custom Tooltip Component
const CustomTooltip = ({ active, payload, label }: {
    active?: boolean;
    payload?: Array<{ value: number; payload: ValidityTrendPoint }>;
    label?: string;
}) => {
    if (active && payload && payload.length) {
        return (
            <div className="bg-sidebar-bg border border-card-border rounded-lg px-3 py-2 shadow-lg">
                <p className="text-xs text-text-muted">{label}</p>
                <p className="text-sm font-semibold text-primary-blue">
                    {payload[0].value} expirations
                </p>
                <p className="text-xs text-accent-yellow mt-1">Click to filter</p>
            </div>
        );
    }
    return null;
};

// Custom active dot with click handler
interface ActiveDotProps {
    cx?: number;
    cy?: number;
    payload?: ValidityTrendPoint;
    onDataPointClick?: (dataPoint: ValidityTrendPoint) => void;
}

const ClickableActiveDot = ({ cx, cy, payload, onDataPointClick }: ActiveDotProps) => {
    if (!cx || !cy) return null;

    return (
        <circle
            cx={cx}
            cy={cy}
            r={8}
            fill="#3b82f6"
            stroke="white"
            strokeWidth={3}
            className="cursor-pointer"
            onClick={(e) => {
                e.stopPropagation();
                if (payload && onDataPointClick) {
                    onDataPointClick(payload);
                }
            }}
        />
    );
};

export default function LineChartComponent({
    data,
    onClick,
    onDataPointClick,
    className = '',
}: LineChartComponentProps) {
    return (
        <div
            className={`w-full h-full min-h-[180px] ${className}`}
            onClick={!onDataPointClick ? onClick : undefined}
        >
            <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
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
                            r: 5,
                            fill: '#3b82f6',
                            stroke: '#1e293b',
                            strokeWidth: 2,
                            className: onDataPointClick ? 'cursor-pointer' : '',
                        }}
                        activeDot={
                            onDataPointClick
                                ? <ClickableActiveDot onDataPointClick={onDataPointClick} />
                                : {
                                    r: 6,
                                    fill: '#3b82f6',
                                    stroke: 'white',
                                    strokeWidth: 2,
                                }
                        }
                    />
                </AreaChart>
            </ResponsiveContainer>
        </div>
    );
}
