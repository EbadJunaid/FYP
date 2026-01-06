'use client';

import React from 'react';
import Card from '@/components/Card';
import { GeographicEntry } from '@/types/dashboard';

interface GeographicDistributionCardProps {
    data: GeographicEntry[];
    onItemClick?: (item: GeographicEntry) => void;
}

export default function GeographicDistributionCard({ data, onItemClick }: GeographicDistributionCardProps) {
    return (
        <Card
            title="Geographic Distribution"
            subtitle="Server Locations"
            className="hover-lift h-full"
            detailsLink="/dashboard/issuer-countries"
        >
            <div className="space-y-3">
                {data.map((item) => (
                    <div
                        key={item.id}
                        onClick={() => onItemClick?.(item)}
                        className="flex items-center gap-3 cursor-pointer group"
                    >
                        {/* Progress Bar */}
                        <div className="flex-1 h-7 bg-background rounded-lg overflow-hidden relative">
                            <div
                                className="h-full rounded-lg transition-all duration-500 group-hover:opacity-80"
                                style={{
                                    width: `${item.percentage}%`,
                                    backgroundColor: item.color,
                                }}
                            />
                            <span className="absolute inset-0 flex items-center px-3 text-xs font-medium text-white mix-blend-difference">
                                {item.country}
                            </span>
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}
