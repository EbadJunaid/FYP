'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function SharedPublicKeysPage() {
    return (
        <GenericDashboardPage
            title="Shared Public Keys"
            description="Analysis of shared public keys across certificates"
            pageType="shared-public-keys"
        />
    );
}
