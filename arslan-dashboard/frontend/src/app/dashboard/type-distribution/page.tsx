'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function TypeDistributionPage() {
    return (
        <GenericDashboardPage
            title="Type Distribution"
            description="Certificate type distribution (DV, OV, EV)"
            pageType="type-distribution"
        />
    );
}
