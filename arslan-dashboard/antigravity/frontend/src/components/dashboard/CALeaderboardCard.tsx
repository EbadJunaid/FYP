'use client';

import React from 'react';
import Card from '@/components/Card';
import ProgressBar from '@/components/charts/ProgressBar';
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
        >
            <div className="space-y-3">
                {data.map((ca) => (
                    <div
                        key={ca.id}
                        onClick={() => onItemClick?.(ca)}
                        className="cursor-pointer"
                    >
                        <ProgressBar
                            value={ca.count}
                            maxValue={ca.maxCount}
                            label={ca.name}
                            valueLabel={`${ca.count}%`}
                            color={ca.color}
                            height="sm"
                        />
                    </div>
                ))}
            </div>
        </Card>
    );
}
