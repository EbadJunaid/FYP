'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function ValidityAnalyticsPage() {
    return (
        <GenericDashboardPage
            title="Validity Analytics"
            description="Certificate validity period analysis and statistics"
            pageType="validity-analytics"
        />
    );
}
