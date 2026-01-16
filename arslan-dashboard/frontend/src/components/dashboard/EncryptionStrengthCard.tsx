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
            infoTooltip="Distribution of encryption algorithms and key lengths used by certificates. Click on a bar to filter certificates by that algorithm."
        >
            <div className="h-full min-h-[320px]">
                <BarChartComponent data={data} onBarClick={onBarClick} />
            </div>
        </Card>
    );
}
