'use client';

import React, { useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { DashboardProvider, useDashboard } from '@/context/DashboardContext';
import Sidebar from '@/components/layout/Sidebar';
import Header from '@/components/layout/Header';
import MobileDrawer from '@/components/layout/MobileDrawer';
import FilterModal from '@/components/FilterModal';
import DownloadModal from '@/components/DownloadModal';
import { NotificationItem } from '@/services/apiClient';

// Dashboard Cards
import GlobalHealthCard from '@/components/dashboard/GlobalHealthCard';
import MetricCard from '@/components/dashboard/MetricCard';
import EncryptionStrengthCard from '@/components/dashboard/EncryptionStrengthCard';
import FutureRiskCard from '@/components/dashboard/FutureRiskCard';
import CALeaderboardCard from '@/components/dashboard/CALeaderboardCard';
import GeographicDistributionCard from '@/components/dashboard/GeographicDistributionCard';
import ValidityTrendCard from '@/components/dashboard/ValidityTrendCard';
import RecentScansCard from '@/components/dashboard/RecentScansCard';

// Icons
import { CertificateIcon, ClockIcon, AlertIcon } from '@/components/icons/Icons';

function DashboardContent() {
  const router = useRouter();
  const tableRef = useRef<HTMLDivElement>(null);
  const {
    state,
    paginatedScans,
    totalPages,
    pagination,
    tableTitle,
    activeFilter,
    handleSearch,
    handleFilter,
    handleCardClick,
    setPage
  } = useDashboard();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [downloadModalOpen, setDownloadModalOpen] = useState(false);

  const { metrics, encryptionStrength, futureRisk, caLeaderboard, geographicDistribution, validityTrend, filters } = state;

  // Scroll to table after card click
  const scrollToTable = () => {
    setTimeout(() => {
      tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 100);
  };

  // Handle card click with scroll
  const handleCardClickWithScroll = (cardType: string, data?: unknown) => {
    handleCardClick(cardType, data);
    scrollToTable();
  };

  // Handle View Full Report button
  const handleViewFullReport = () => {
    router.push('/dashboard/trends');
  };

  // Handle download scans - opens modal
  const handleDownloadScans = () => {
    setDownloadModalOpen(true);
  };

  // Handle notification click - filter table based on notification type
  const handleNotificationClick = (notification: NotificationItem) => {
    switch (notification.category) {
      case 'expiring':
        handleCardClickWithScroll('expiringSoon');
        break;
      case 'security':
        handleCardClickWithScroll('vulnerabilities');
        break;
      case 'expired':
        // Could add expired filter if needed
        handleCardClickWithScroll('expiringSoon');
        break;
      default:
        break;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar - Desktop */}
      <Sidebar activeItem="overview" />

      {/* Mobile Drawer */}
      <MobileDrawer
        isOpen={mobileMenuOpen}
        onClose={() => setMobileMenuOpen(false)}
        activeItem="overview"
      />

      {/* Main Content Area */}
      <div className="lg:pl-64">
        {/* Header */}
        <Header
          onMenuClick={() => setMobileMenuOpen(true)}
          onSearch={handleSearch}
          onFilterClick={() => setFilterModalOpen(true)}
          onNotificationClick={handleNotificationClick}
        />

        {/* Main Content */}
        <main className="p-4 lg:p-6 overflow-y-auto">
          {/* Top Row - Global Health & Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 lg:gap-6 mb-6">
            {/* Global Health Card */}
            {metrics && (
              <GlobalHealthCard
                score={metrics.globalHealth.score}
                maxScore={metrics.globalHealth.maxScore}
                status={metrics.globalHealth.status}
                lastUpdated={metrics.globalHealth.lastUpdated}
                onClick={() => handleCardClickWithScroll('globalHealth')}
              />
            )}

            {/* Active Certificates */}
            {metrics && (
              <MetricCard
                icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                iconBgColor="bg-primary-blue/15"
                value={
                  <span>
                    {metrics.activeCertificates.count.toLocaleString()}
                    <span className="text-sm text-text-muted font-normal ml-1">
                      out of {metrics.activeCertificates.total.toLocaleString()}
                    </span>
                  </span>
                }
                label="Active Certificates"
                onClick={() => handleCardClickWithScroll('activeCertificates')}
                detailsLink="/dashboard/active-vs-expired"
                infoTooltip="Count of currently valid SSL certificates that have not expired"
              />
            )}

            {/* Expiring Soon */}
            {metrics && (
              <MetricCard
                icon={<ClockIcon className="w-6 h-6 text-accent-yellow" />}
                iconBgColor="bg-accent-yellow/15"
                value={metrics.expiringSoon.count}
                label={`Expiring Soon (< ${metrics.expiringSoon.daysThreshold}d)`}
                badge={metrics.expiringSoon.actionNeeded ? { text: 'Action Needed', variant: 'warning' } : undefined}
                onClick={() => handleCardClickWithScroll('expiringSoon')}
                detailsLink="/dashboard/active-vs-expired"
                infoTooltip="Certificates expiring within the next 30 days that need attention"
              />
            )}

            {/* Critical Vulnerabilities */}
            {metrics && (
              <MetricCard
                icon={<AlertIcon className="w-6 h-6 text-accent-red" />}
                iconBgColor="bg-accent-red/15"
                value={metrics.criticalVulnerabilities.count}
                label="Critical Vulnerabilities"
                onClick={() => handleCardClickWithScroll('vulnerabilities')}
                detailsLink="/dashboard/vulnerabilities"
                infoTooltip="Certificates with security issues detected by ZLint analysis"
              />
            )}
          </div>

          {/* Second Row - Encryption Strength & Future Risk - MATCHED HEIGHTS */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6 mb-6">
            {/* Encryption Strength Distribution - Takes 2 columns */}
            <div className="lg:col-span-2 h-full">
              <div className="h-full min-h-[400px]">
                <EncryptionStrengthCard
                  data={encryptionStrength}
                  onBarClick={(item) => handleCardClickWithScroll('encryptionBar', item)}
                  onViewDetails={handleViewFullReport}
                />
              </div>
            </div>

            {/* Future Risk Predictor */}
            {futureRisk && (
              <div className="h-full min-h-[400px]">
                <FutureRiskCard
                  data={futureRisk}
                />
              </div>
            )}
          </div>

          {/* Deep Analysis Grid Header */}
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-text-primary">Deep Analysis Grid</h2>
            <button
              onClick={handleViewFullReport}
              className="text-sm text-primary-blue hover:text-primary-purple font-medium transition-colors"
            >
              View Full Report
            </button>
          </div>

          {/* Third Row - CA Leaderboard, Geographic Distribution, Validity Trend */}
          {/* Validity Trend takes full width on smaller screens */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 lg:gap-6 mb-6">
            {/* CA Leaderboard */}
            <CALeaderboardCard
              data={caLeaderboard}
              onItemClick={(item) => handleCardClickWithScroll('caLeaderboard', item)}
            />

            {/* Geographic Distribution */}
            <GeographicDistributionCard
              data={geographicDistribution}
              onItemClick={(item) => handleCardClickWithScroll('geographic', item)}
            />

            {/* Validity Trend - Full width on md and below */}
            <div className="md:col-span-2 xl:col-span-1">
              <ValidityTrendCard
                data={validityTrend}
                onDataPointClick={(dataPoint) => handleCardClickWithScroll('validityTrend', dataPoint)}
              />
            </div>
          </div>

          {/* Recent Scans Table with Pagination */}
          <div ref={tableRef}>
            <RecentScansCard
              data={paginatedScans}
              title={tableTitle}
              onRowClick={(entry) => console.log('Scan row clicked:', entry)}
              onFilterClick={() => setFilterModalOpen(true)}
              onDownloadClick={handleDownloadScans}
              currentPage={pagination.currentPage}
              totalPages={totalPages}
              onPageChange={setPage}
            />
          </div>
        </main>
      </div>

      {/* Filter Modal */}
      <FilterModal
        isOpen={filterModalOpen}
        onClose={() => setFilterModalOpen(false)}
        filters={filters}
        onApplyFilters={handleFilter}
      />

      {/* Download Modal */}
      <DownloadModal
        isOpen={downloadModalOpen}
        onClose={() => setDownloadModalOpen(false)}
        currentPageData={paginatedScans}
        activeFilter={activeFilter}
        totalCount={pagination.totalItems}
      />
    </div>
  );
}

export default function Home() {
  return (
    <DashboardProvider>
      <DashboardContent />
    </DashboardProvider>
  );
}