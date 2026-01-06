'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function SANAnalyticsPage() {
    return (
        <GenericDashboardPage
            title="SAN Analytics"
            description="Subject Alternative Names (SAN) analysis and statistics"
            pageType="san-analytics"
        />
    );
}
