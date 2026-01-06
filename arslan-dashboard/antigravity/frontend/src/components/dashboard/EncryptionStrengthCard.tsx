'use client';

import React from 'react';
import Card from '@/components/Card';
import BarChartComponent from '@/components/charts/BarChartComponent';
import { EncryptionStrength } from '@/types/dashboard';

interface EncryptionStrengthCardProps {
    data: EncryptionStrength[];
    onViewDetails?: () => void;
    onBarClick?: (item: EncryptionStrength) => void;
}

export default function EncryptionStrengthCard({
    data,
    onViewDetails,
    onBarClick,
}: EncryptionStrengthCardProps) {
    return (
        <Card
            title="Encryption Strength Distribution"
            className="hover-lift h-full"
            detailsLink="/dashboard/signature-hash"
        >
            <div className="h-full min-h-[320px]">
                <BarChartComponent data={data} onBarClick={onBarClick} />
            </div>
        </Card>
    );
}
