'use client';

import React, { useState, useEffect } from 'react';
import Card from '@/components/Card';
import LineChartComponent from '@/components/charts/LineChartComponent';
import { ValidityTrendPoint } from '@/types/dashboard';

interface ValidityTrendCardProps {
    data: ValidityTrendPoint[];
    onClick?: () => void;
    isFullWidth?: boolean;
}

export default function ValidityTrendCard({ data, onClick, isFullWidth = false }: ValidityTrendCardProps) {
    const [showFullData, setShowFullData] = useState(false);

    // Handle responsive data display
    useEffect(() => {
        const handleResize = () => {
            // Show full data when screen is below xl (1280px) where card takes full width
            setShowFullData(window.innerWidth < 1280 || isFullWidth);
        };

        handleResize();
        window.addEventListener('resize', handleResize);
        return () => window.removeEventListener('resize', handleResize);
    }, [isFullWidth]);

    // Slice data based on display mode: 8 months for desktop, full for expanded
    const displayData = showFullData ? data : data.slice(-8);
    const subtitle = showFullData
        ? `Certificate Expiration Timeline (${data.length} Months)`
        : 'Certificate Expiration Timeline (8 Months)';

    return (
        <Card
            title="Validity Trend"
            subtitle={subtitle}
            onClick={onClick}
            isClickable={!!onClick}
            className="hover-lift h-full"
            detailsLink="/dashboard/validity-analytics"
        >
            <div className="h-[200px]">
                <LineChartComponent data={displayData} />
            </div>
        </Card>
    );
}
