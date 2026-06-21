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
            subtitle="Domain Countries"
            className="hover-lift h-full"
            detailsLink="/dashboard/issuer-countries"
            infoTooltip="Certificate distribution by domain country (derived from TLD). Click on a country to filter certificates from that region."
        >
            <div className="space-y-3">
                {data.map((item) => (
                    <div
                        key={item.id}
                        onClick={() => onItemClick?.(item)}
                        className="cursor-pointer group"
                    >
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-sm text-text-primary group-hover:text-primary-blue transition-colors">
                                {item.country}
                            </span>
                            <span className="text-sm font-medium text-text-secondary">
                                {item.percentage}%
                            </span>
                        </div>
                        <div className="h-2 bg-background rounded-full overflow-hidden">
                            <div
                                className="h-full rounded-full transition-all duration-500 group-hover:opacity-80"
                                style={{
                                    width: `${Math.min(item.percentage * 2, 100)}%`,
                                    backgroundColor: item.color,
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}
