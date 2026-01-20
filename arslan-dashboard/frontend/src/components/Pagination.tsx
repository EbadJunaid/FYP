'use client';

import React from 'react';
import { ChevronRightIcon } from '@/components/icons/Icons';

interface PaginationProps {
    currentPage: number;
    totalPages: number;
    onPageChange: (page: number) => void;
    className?: string;
}

export default function Pagination({
    currentPage,
    totalPages,
    onPageChange,
    className = '',
}: PaginationProps) {
    const handlePrevious = () => {
        if (currentPage > 1) {
            onPageChange(currentPage - 1);
        }
    };

    const handleNext = () => {
        if (currentPage < totalPages) {
            onPageChange(currentPage + 1);
        }
    };

    return (
        <div className={`flex items-center justify-center w-full mt-4 pt-4 border-t border-card-border ${className}`}>
            {/* Previous Button - positioned left */}
            <div className="flex-1 flex justify-start">
                <button
                    onClick={handlePrevious}
                    disabled={currentPage <= 1}
                    className={`
                        flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
                        transition-all duration-200
                        ${currentPage <= 1
                            ? 'text-text-muted cursor-not-allowed opacity-50'
                            : 'text-text-secondary hover:text-text-primary hover:bg-card-bg border border-card-border'
                        }
                    `}
                >
                    <ChevronRightIcon className="w-4 h-4 rotate-180" />
                    Previous
                </button>
            </div>

            {/* Page Info - centered */}
            <div className="flex items-center justify-center">
                <span className="text-sm text-text-secondary">
                    Page <span className="font-medium text-text-primary">{currentPage}</span> of{' '}
                    <span className="font-medium text-text-primary">{totalPages}</span>
                </span>
            </div>

            {/* Next Button - positioned right */}
            <div className="flex-1 flex justify-end">
                <button
                    onClick={handleNext}
                    disabled={currentPage >= totalPages}
                    className={`
                        flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg
                        transition-all duration-200
                        ${currentPage >= totalPages
                            ? 'text-text-muted cursor-not-allowed opacity-50'
                            : 'text-text-secondary hover:text-text-primary hover:bg-card-bg border border-card-border'
                        }
                    `}
                >
                    Next
                    <ChevronRightIcon className="w-4 h-4" />
                </button>
            </div>
        </div>
    );
}

