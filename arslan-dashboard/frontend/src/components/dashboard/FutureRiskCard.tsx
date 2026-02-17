'use client';

import React, { useState } from 'react';
import Card from '@/components/Card';
import DonutChart from '@/components/charts/DonutChart';
import { KeyIcon, SignatureIcon } from '@/components/icons/Icons';
import { FutureRisk, ProjectedThreat } from '@/types/dashboard';
import NotDevelopedModal from '@/components/NotDevelopedModal';

interface FutureRiskCardProps {
    data: FutureRisk;
}

const ThreatItem: React.FC<{ threat: ProjectedThreat }> = ({ threat }) => {
    const getIcon = () => {
        switch (threat.icon) {
            case 'key':
                return <KeyIcon className="w-4 h-4 text-accent-yellow" />;
            case 'signature':
                return <SignatureIcon className="w-4 h-4 text-accent-red" />;
            default:
                return <KeyIcon className="w-4 h-4 text-text-muted" />;
        }
    };

    const getBgColor = () => {
        switch (threat.icon) {
            case 'key':
                return 'bg-accent-yellow/15';
            case 'signature':
                return 'bg-accent-red/15';
            default:
                return 'bg-card-border';
        }
    };

    return (
        <div className="flex items-center gap-3 p-3 rounded-xl bg-background hover:bg-primary-blue/5 transition-colors cursor-pointer">
            <div className={`w-8 h-8 rounded-lg ${getBgColor()} flex items-center justify-center flex-shrink-0`}>
                {getIcon()}
            </div>
            <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-text-primary truncate">{threat.title}</p>
                <p className="text-xs text-text-muted truncate">{threat.description}</p>
            </div>
        </div>
    );
};

export default function FutureRiskCard({ data }: FutureRiskCardProps) {
    const [showModal, setShowModal] = useState(false);

    // Only show modal - NO table update, NO scroll
    const handleCardClick = () => {
        setShowModal(true);
    };

    const handleViewDetails = () => {
        setShowModal(true);
    };

    return (
        <>
            <Card
                title="Future Risk Predictor"
                onClick={handleCardClick}
                isClickable={true}
                headerAction={
                    <div className="flex items-center gap-1.5">
                        <span className="text-[10px] text-text-muted uppercase">Confidence</span>
                        <span className="text-sm font-bold text-primary-blue">{data.confidenceLevel}%</span>
                    </div>
                }
                className="hover-lift h-full"
                onViewDetails={handleViewDetails}
                infoTooltip="AI-predicted future security risks based on current certificate configurations and industry trends."
            >
                <div className="space-y-4">
                    {/* Donut Chart */}
                    <div className="flex justify-center">
                        <DonutChart
                            value={data.confidenceLevel}
                            maxValue={100}
                            size={130}
                            strokeWidth={12}
                            label={`${data.riskLevel} Risk Level`}
                            sublabel="RISK LEVEL"
                            riskLevel={data.riskLevel}
                        />
                    </div>

                    {/* Projected Threats */}
                    <div className="space-y-2">
                        <p className="text-xs text-text-muted uppercase tracking-wider">Projected Threats</p>
                        {data.projectedThreats.map((threat) => (
                            <ThreatItem key={threat.id} threat={threat} />
                        ))}
                    </div>
                </div>
            </Card>

            {/* Not Developed Modal */}
            <NotDevelopedModal isOpen={showModal} onClose={() => setShowModal(false)} />
        </>
    );
}
