'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function CAsVsDomainsPage() {
    return (
        <GenericDashboardPage
            title="CAs vs Domains"
            description="Certificate authority to domain mapping analysis"
            pageType="cas-vs-domains"
        />
    );
}
