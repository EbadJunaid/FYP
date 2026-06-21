'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function CAsVsPublicKeysPage() {
    return (
        <GenericDashboardPage
            title="CAs vs Public Keys"
            description="Certificate authority to public key mapping analysis"
            pageType="cas-vs-public-keys"
        />
    );
}
