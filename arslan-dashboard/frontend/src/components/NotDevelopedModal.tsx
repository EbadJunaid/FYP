'use client';

import React from 'react';
import { CloseIcon } from '@/components/icons/Icons';

interface NotDevelopedModalProps {
    isOpen: boolean;
    onClose: () => void;
}

const NotDevelopedModal: React.FC<NotDevelopedModalProps> = ({ isOpen, onClose }) => {
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
                    <p className="text-base text-text-muted">
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

export default NotDevelopedModal;
