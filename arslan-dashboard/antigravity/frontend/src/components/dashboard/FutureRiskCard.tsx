'use client';

import React, { useState } from 'react';
import Card from '@/components/Card';
import DonutChart from '@/components/charts/DonutChart';
import { KeyIcon, SignatureIcon, CloseIcon } from '@/components/icons/Icons';
import { FutureRisk, ProjectedThreat } from '@/types/dashboard';

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

// Modal Component for "Not Developed" message
const NotDevelopedModal: React.FC<{ isOpen: boolean; onClose: () => void }> = ({ isOpen, onClose }) => {
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            {/* Overlay */}
            <div
                className="absolute inset-0 bg-black/50 backdrop-blur-sm"
                onClick={onClose}
            />

            {/* Modal */}
            <div className="relative bg-card-bg border border-card-border rounded-2xl p-6 max-w-sm w-full shadow-xl animate-fade-in">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 p-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-background transition-colors"
                >
                    <CloseIcon size={18} />
                </button>

                <div className="text-center">
                    <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-accent-yellow/15 flex items-center justify-center">
                        <svg className="w-8 h-8 text-accent-yellow" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <circle cx="12" cy="12" r="10" />
                            <path d="M12 8v4M12 16h.01" />
                        </svg>
                    </div>
                    <h3 className="text-lg font-semibold text-text-primary mb-2">Coming Soon</h3>
                    <p className="text-sm text-text-muted">
                        This feature is not developed yet. It will be done later.
                    </p>
                    <button
                        onClick={onClose}
                        className="mt-4 px-6 py-2 bg-primary-blue text-white rounded-lg text-sm font-medium hover:bg-primary-blue/80 transition-colors"
                    >
                        Got it
                    </button>
                </div>
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
