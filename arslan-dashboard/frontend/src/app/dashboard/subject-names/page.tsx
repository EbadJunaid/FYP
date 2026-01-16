'use client';

import GenericDashboardPage from '@/components/dashboard/GenericDashboardPage';

export default function SubjectNamesPage() {
    return (
        <GenericDashboardPage
            title="Subject Names"
            description="Certificate subject name analysis"
            pageType="subject-names"
        />
    );
}
