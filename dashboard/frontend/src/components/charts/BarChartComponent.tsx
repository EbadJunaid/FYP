'use client';

import React from 'react';
import { EncryptionStrength } from '@/types/dashboard';

interface BarChartComponentProps {
    data: EncryptionStrength[];
    onBarClick?: (item: EncryptionStrength) => void;
    className?: string;
}

export default function BarChartComponent({
    data,
    onBarClick,
    className = '',
}: BarChartComponentProps) {
    // Sort by percentage descending
    const sortedData = [...data].sort((a, b) => b.percentage - a.percentage);

    // Get color based on type
    const getBarColor = (type: string) => {
        switch (type) {
            case 'Strong':
                return 'bg-accent-green';
            case 'Standard':
                return 'bg-primary-blue';
            case 'Modern':
                return 'bg-primary-cyan';
            case 'Weak':
            case 'Deprecated':
                return 'bg-accent-red';
            default:
                return 'bg-primary-blue';
        }
    };

    // Get text color based on type
    const getTextColor = (type: string) => {
        switch (type) {
            case 'Weak':
            case 'Deprecated':
                return 'text-accent-red';
            default:
                return 'text-text-primary';
        }
    };

    return (
        <div className={`flex flex-col justify-between h-full min-h-[280px] ${className}`}>
            {sortedData.map((item, index) => (
                <div
                    key={item.id}
                    className={`group ${onBarClick ? 'cursor-pointer hover:bg-card-background/50 rounded-lg p-2 -ml-2 -mr-2 transition-all duration-200' : ''} ${index < sortedData.length - 1 ? 'mb-auto' : ''}`}
                    onClick={() => onBarClick?.(item)}
                >
                    {/* Label Row */}
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <span className={`text-sm font-medium transition-colors ${onBarClick ? 'group-hover:text-primary-blue' : ''} ${getTextColor(item.type)}`}>
                                {item.name}
                            </span>
                            <span className={`text-xs px-1.5 py-0.5 rounded transition-transform ${onBarClick ? 'group-hover:scale-105' : ''} ${item.type === 'Weak' || item.type === 'Deprecated'
                                ? 'bg-accent-red/15 text-accent-red'
                                : item.type === 'Strong'
                                    ? 'bg-accent-green/15 text-accent-green'
                                    : 'bg-primary-blue/15 text-primary-blue'
                                }`}>
                                {item.type}
                            </span>
                        </div>
                        <span className="text-sm text-text-muted">{item.percentage}%</span>
                    </div>

                    {/* Bar */}
                    <div className="h-3 bg-card-border rounded-full overflow-hidden">
                        <div
                            className={`h-full rounded-full transition-all duration-500 ease-out ${onBarClick ? 'group-hover:opacity-80 group-hover:shadow-md' : ''} ${getBarColor(item.type)}`}
                            style={{ width: `${item.percentage}%` }}
                        />
                    </div>
                </div>
            ))}
        </div>
    );
}
