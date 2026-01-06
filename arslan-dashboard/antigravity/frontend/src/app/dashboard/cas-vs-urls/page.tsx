'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function CAsVsURLsPage() {
    return (
        <GenericDashboardPage
            title="CAs vs URLs"
            description="Certificate authority to URL mapping analysis"
            pageType="cas-vs-urls"
        />
    );
}
