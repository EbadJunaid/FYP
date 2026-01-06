'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function IssuerOrganizationsPage() {
    return (
        <GenericDashboardPage
            title="Issuer Organizations"
            description="Certificate issuer organization analysis"
            pageType="issuer-organizations"
        />
    );
}
