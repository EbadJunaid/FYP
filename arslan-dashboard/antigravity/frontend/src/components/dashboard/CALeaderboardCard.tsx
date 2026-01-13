'use client';

import React from 'react';
import Card from '@/components/Card';
import { CALeaderboardEntry } from '@/types/dashboard';

interface CALeaderboardCardProps {
    data: CALeaderboardEntry[];
    onItemClick?: (item: CALeaderboardEntry) => void;
}

export default function CALeaderboardCard({ data, onItemClick }: CALeaderboardCardProps) {
    return (
        <Card
            title="CA Leaderboard"
            subtitle="Certificate Authority Ranking"
            className="hover-lift h-full"
            detailsLink="/dashboard/ca-analytics"
            infoTooltip="Top certificate authorities by issuance count. Click on a CA to filter certificates issued by that authority."
        >
            <div className="space-y-3">
                {data.map((ca) => (
                    <div
                        key={ca.id}
                        onClick={() => onItemClick?.(ca)}
                        className="cursor-pointer group"
                    >
                        <div className="flex justify-between items-center mb-1">
                            <span className="text-sm text-text-primary group-hover:text-primary-blue transition-colors">
                                {ca.name}
                            </span>
                            <span className="text-sm font-medium text-text-secondary">
                                {ca.percentage}%
                            </span>
                        </div>
                        <div className="h-2 bg-background rounded-full overflow-hidden">
                            <div
                                className="h-full rounded-full transition-all duration-500 group-hover:opacity-80"
                                style={{
                                    width: `${Math.min(ca.percentage * 2, 100)}%`,
                                    backgroundColor: ca.color,
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}
