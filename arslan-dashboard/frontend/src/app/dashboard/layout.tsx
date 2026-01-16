'use client';

import React, { useState } from 'react';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MobileDrawer from '@/components/layout/MobileDrawer';
import FilterModal from '@/components/FilterModal';
import { ThemeProvider } from '@/context/ThemeContext';
import { SearchProvider, useSearch } from '@/context/SearchContext';
import { FilterOptions } from '@/types/dashboard';

const initialFilters: FilterOptions = {
    dateRange: { start: null, end: null },
    status: [],
    vulnerabilityType: [],
    issuer: [],
    sslGrade: [],
};

// Inner layout component that uses search context
function DashboardLayoutInner({ children }: { children: React.ReactNode }) {
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [filterModalOpen, setFilterModalOpen] = useState(false);
    const [filters, setFilters] = useState<FilterOptions>(initialFilters);
    const { handleSearch } = useSearch();

    const handleFilter = (newFilters: FilterOptions) => {
        setFilters(newFilters);
        console.log('Applied filters:', newFilters);
    };

    return (
        <div className="min-h-screen bg-background">
            {/* Sidebar - Desktop */}
            <Sidebar />

            {/* Mobile Drawer */}
            <MobileDrawer
                isOpen={mobileMenuOpen}
                onClose={() => setMobileMenuOpen(false)}
            />

            {/* Main Content Area */}
            <div className="lg:pl-64">
                {/* Header */}
                <Header
                    onMenuClick={() => setMobileMenuOpen(true)}
                    onSearch={handleSearch}
                    onFilterClick={() => setFilterModalOpen(true)}
                />

                {/* Page Content */}
                <main className="p-4 lg:p-6 overflow-y-auto">
                    {children}
                </main>
            </div>

            {/* Filter Modal */}
            <FilterModal
                isOpen={filterModalOpen}
                onClose={() => setFilterModalOpen(false)}
                filters={filters}
                onApplyFilters={handleFilter}
            />
        </div>
    );
}

export default function DashboardLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    return (
        <ThemeProvider defaultTheme="dark">
            <SearchProvider>
                <DashboardLayoutInner>
                    {children}
                </DashboardLayoutInner>
            </SearchProvider>
        </ThemeProvider>
    );
}

