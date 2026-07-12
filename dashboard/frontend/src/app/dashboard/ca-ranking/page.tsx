'use client';

import React, { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import useSWR from 'swr';
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Cell,
} from 'recharts';
import Card from '@/components/Card';
import DataTable from '@/components/DataTable';
import MetricCard from '@/components/dashboard/MetricCard';
import SmallSearchInput from '@/components/SmallSearchInput';
import { CertificateIcon, CheckCircleIcon, InfoIcon, ShieldIcon, TrendUpIcon } from '@/components/icons/Icons';
import apiClient, { CARankingEntry, CARankingResponse } from '@/services/apiClient';
import { fetchCertificates } from '@/controllers/pageController';
import { ScanEntry } from '@/types/dashboard';
import { useDatabaseKey } from '@/hooks/useDatabaseKey';
import { useSearch } from '@/context/SearchContext';

const STORAGE_KEY = 'ca-ranking-page-state';
const rankingFetcher = () => apiClient.getCARanking(5000, 'ca');
const normalizeRankingSearch = (value: string) => value.toLowerCase().replace(/[^a-z0-9]+/g, '');

const componentTooltips = {
    score: 'Final trust score. Higher is better.',
    coreHygiene: 'ZLint hygiene: fewer non-critical lint issues and fewer critical lint errors means a higher score.',
    cryptoHealth: 'Cryptographic health: key algorithm, key size, validity length, and public-key reuse behavior.',
    operationalStability: 'Operational stability: issuer consistency and certificate issuance timing behavior.',
    policyCompliance: 'Policy and compliance: extended key usage, policy OIDs, validation level, and name constraints.',
    riskFactors: 'Risk context score: issuer country risk signal plus revocation and AIA availability. Higher means lower contextual risk.',
    certificates: 'Number of certificates issued by this CA in the selected scope.',
};

function HeaderWithInfo({ label, tooltip }: { label: string; tooltip: string }) {
    return (
        <span className="inline-flex items-center gap-1">
            {label}
            <span className="group relative inline-flex">
                <InfoIcon className="w-3.5 h-3.5 text-text-muted cursor-help" />
                <span className="pointer-events-none absolute left-1/2 top-5 z-20 hidden w-64 -translate-x-1/2 rounded-md border border-card-border bg-card-bg p-2 text-xs font-normal text-text-secondary shadow-lg group-hover:block">
                    {tooltip}
                </span>
            </span>
        </span>
    );
}

export default function CARankingPage() {
    const router = useRouter();
    const tableRef = useRef<HTMLDivElement>(null);
    const dbKey = useDatabaseKey('ca-ranking');
    const { searchQuery, setSearchQuery } = useSearch();
    const [selectedCA, setSelectedCA] = useState<CARankingEntry | null>(null);
    const [restoredCAName, setRestoredCAName] = useState<string | null>(null);
    const [currentPage, setCurrentPage] = useState(1);
    const [rankingPage, setRankingPage] = useState(1);
    const [rankingSearch, setRankingSearch] = useState('');
    const rankingSearchRef = useRef<HTMLInputElement>(null);

    const { data: ranking, isLoading: isRankingLoading } = useSWR<CARankingResponse>(
        `ca-ranking-page|${dbKey}`,
        rankingFetcher,
        { revalidateOnFocus: false, dedupingInterval: 600000 }
    );

    useEffect(() => {
        return () => {
            setSearchQuery('');
        };
    }, [setSearchQuery]);

    useEffect(() => {
        const timer = window.setTimeout(() => {
        try {
            const saved = sessionStorage.getItem(STORAGE_KEY);
            if (saved) {
                const parsed = JSON.parse(saved);
                setCurrentPage(parsed.currentPage || 1);
                setRestoredCAName(parsed.selectedCAName || null);
                if (parsed.scrollY) {
                    setTimeout(() => window.scrollTo(0, parsed.scrollY), 100);
                }
                sessionStorage.removeItem(STORAGE_KEY);
            }
        } catch (error) {
            console.error('Error restoring CA ranking state:', error);
        }
        }, 0);
        return () => window.clearTimeout(timer);
    }, []);

    useEffect(() => {
        const onKey = (event: KeyboardEvent) => {
            if ((event.ctrlKey || event.metaKey) && event.shiftKey && event.key.toLowerCase() === 'c') {
                event.preventDefault();
                rankingSearchRef.current?.focus();
            }
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, []);

    const activeCA = selectedCA
        || ranking?.items?.find((entry) => entry.name === restoredCAName)
        || ranking?.items?.[0]
        || null;

    const swrKey = activeCA
        ? `ca-ranking-certs|${activeCA.name}|${currentPage}|${searchQuery || ''}|${dbKey}`
        : null;

    const certificatesFetcher = useCallback(async () => {
        return fetchCertificates({
            page: currentPage,
            pageSize: 10,
            issuer: searchQuery ? undefined : activeCA?.name,
            search: searchQuery || undefined,
        });
    }, [activeCA?.name, currentPage, searchQuery]);

    const { data: certsData, isLoading: isCertsLoading } = useSWR(
        swrKey,
        certificatesFetcher,
        { revalidateOnFocus: false, dedupingInterval: 60000, keepPreviousData: true }
    );

    const tableData = certsData?.certificates || [];
    const totalPages = certsData?.pagination?.totalPages || 1;

    useEffect(() => {
        if (searchQuery) {
            const timer = window.setTimeout(() => {
                setCurrentPage(1);
                tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }, 100);
            return () => window.clearTimeout(timer);
        }
    }, [searchQuery]);

    const handleSelectCA = useCallback((entry: CARankingEntry) => {
        setSelectedCA(entry);
        setCurrentPage(1);
        setTimeout(() => tableRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100);
    }, []);

    const handleRowClick = useCallback((entry: ScanEntry) => {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
            selectedCAName: activeCA?.name,
            currentPage,
            scrollY: window.scrollY,
        }));
        router.push(`/certificate/${entry.id}`);
    }, [activeCA?.name, currentPage, router]);

    const metricData = useMemo(() => {
        const items = ranking?.items || [];
        const top = items[0];
        const scoredCertificates = items.reduce((total, item) => total + (item.scoreSampleCount || 0), 0);
        return {
            topName: ranking?.summary?.topName || top?.name || 'N/A',
            topScore: ranking?.summary?.topScore || top?.score || 0,
            rankedCount: ranking?.summary?.rankedCount || items.length,
            averageScore: ranking?.summary?.averageScore || 0,
            scoredCertificates,
        };
    }, [ranking]);
    const chartItems = (ranking?.items || []).slice(0, 20);
    const rankingPageSize = 10;
    const normalizedRankingSearch = normalizeRankingSearch(rankingSearch);
    const rankingItems = useMemo(() => {
        const items = ranking?.items || [];
        if (!normalizedRankingSearch) return items;
        return items.filter((entry) => normalizeRankingSearch(entry.name || '').includes(normalizedRankingSearch));
    }, [normalizedRankingSearch, ranking?.items]);
    const rankingTotalPages = Math.max(1, Math.ceil(rankingItems.length / rankingPageSize));
    const pagedRankingItems = rankingItems.slice(
        (rankingPage - 1) * rankingPageSize,
        rankingPage * rankingPageSize
    );

    useEffect(() => {
        const timer = window.setTimeout(() => setRankingPage(1), 0);
        return () => window.clearTimeout(timer);
    }, [rankingSearch]);

    if (isRankingLoading && !ranking) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="text-text-muted">Loading CA Ranking...</div>
            </div>
        );
    }

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">CA Ranking</h1>
                <p className="text-text-muted mt-1">Certificate Authority trust ranking for the selected scope</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<TrendUpIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={metricData.topScore}
                    label={`Top: ${metricData.topName}`}
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={metricData.averageScore}
                    label="Average Score"
                />
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={metricData.rankedCount.toLocaleString()}
                    label="Ranked CAs"
                />
                <MetricCard
                    icon={<CheckCircleIcon className="w-6 h-6 text-primary-cyan" />}
                    iconBgColor="bg-primary-cyan/15"
                    value={metricData.scoredCertificates.toLocaleString()}
                    label="Scored Certificates"
                />
            </div>

            <Card
                title="CA Trust Score"
                subtitle="Top 20 CAs by notebook trust score. Click a bar to show certificates issued by that CA."
                infoTooltip="Uses the exact notebook formula: final score is the mean of core hygiene, crypto health, operational stability, policy compliance, and risk factors."
            >
                <div className="h-[560px]">
                    <ResponsiveContainer width="100%" height="100%" minHeight={560} minWidth={0}>
                        <BarChart
                            layout="vertical"
                            data={chartItems}
                            margin={{ top: 8, right: 40, left: 16, bottom: 8 }}
                        >
                            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                            <XAxis type="number" domain={[0, 100]} stroke="#9ca3af" fontSize={12} />
                            <YAxis
                                type="category"
                                dataKey="name"
                                width={180}
                                stroke="#9ca3af"
                                fontSize={11}
                                tick={{ fill: '#9ca3af' }}
                                tickFormatter={(value) => value.length > 24 ? `${value.slice(0, 22)}...` : value}
                            />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                                itemStyle={{ color: '#ffffff' }}
                                labelStyle={{ color: '#ffffff' }}
                                formatter={(value, name) => [
                                    name === 'score' ? `${Number(value).toFixed(2)} / 100` : Number(value).toLocaleString(),
                                    name === 'score' ? 'Trust Score' : String(name)
                                ]}
                            />
                            <Bar
                                dataKey="score"
                                radius={[0, 4, 4, 0]}
                                cursor="pointer"
                                onClick={(data) => {
                                    const entry = data?.payload as CARankingEntry | undefined;
                                    if (entry) handleSelectCA(entry);
                                }}
                            >
                                {chartItems.map((entry) => (
                                    <Cell key={entry.id} fill={entry.color} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </Card>

            <Card
                title="Ranking Details"
                subtitle={`Component scores for ranked CAs${rankingSearch ? ` matching "${rankingSearch}"` : ''}`}
                headerAction={
                    <SmallSearchInput
                        ref={rankingSearchRef}
                        value={rankingSearch}
                        onChange={(event) => setRankingSearch(event.target.value)}
                        placeholder="Search CA"
                        shortcutKey="C"
                    />
                }
            >
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="text-left text-text-muted">
                                <th className="py-2 pr-3">Rank</th>
                                <th className="py-2 pr-3">CA</th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Score" tooltip={componentTooltips.score} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Lint Hygiene" tooltip={componentTooltips.coreHygiene} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Crypto Health" tooltip={componentTooltips.cryptoHealth} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Operations" tooltip={componentTooltips.operationalStability} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Policy" tooltip={componentTooltips.policyCompliance} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Risk Context" tooltip={componentTooltips.riskFactors} /></th>
                                <th className="py-2 pr-3"><HeaderWithInfo label="Certificates" tooltip={componentTooltips.certificates} /></th>
                            </tr>
                        </thead>
                        <tbody>
                            {pagedRankingItems.map((entry) => (
                                <tr
                                    key={entry.id}
                                    onClick={() => handleSelectCA(entry)}
                                    className="border-t border-card-border cursor-pointer hover:bg-background/40 transition-colors"
                                >
                                    <td className="py-2 pr-3 text-text-muted">#{entry.rank}</td>
                                    <td className="py-2 pr-3 text-text-primary font-medium">{entry.name}</td>
                                    <td className="py-2 pr-3 text-primary-blue font-semibold">{entry.score}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.coreHygiene}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.cryptoHealth}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.operationalStability}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.policyCompliance}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.riskFactors}</td>
                                    <td className="py-2 pr-3 text-text-secondary">{entry.count.toLocaleString()}</td>
                                </tr>
                            ))}
                            {pagedRankingItems.length === 0 && (
                                <tr>
                                    <td colSpan={9} className="py-8 text-center text-text-muted">
                                        No CA found for this search.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
                <div className="mt-4 flex items-center justify-between border-t border-card-border pt-4">
                    <span className="text-xs text-text-muted">
                        Showing {rankingItems.length ? (rankingPage - 1) * rankingPageSize + 1 : 0}-{Math.min(rankingPage * rankingPageSize, rankingItems.length)} of {rankingItems.length}
                    </span>
                    <div className="flex gap-2">
                        <button
                            onClick={() => setRankingPage((page) => Math.max(1, page - 1))}
                            disabled={rankingPage <= 1}
                            className="rounded-lg border border-card-border px-3 py-1.5 text-xs text-text-secondary disabled:opacity-40"
                        >
                            Previous 10
                        </button>
                        <button
                            onClick={() => setRankingPage((page) => Math.min(rankingTotalPages, page + 1))}
                            disabled={rankingPage >= rankingTotalPages}
                            className="rounded-lg border border-card-border px-3 py-1.5 text-xs text-text-secondary disabled:opacity-40"
                        >
                            Next 10
                        </button>
                    </div>
                </div>
            </Card>

            <div ref={tableRef}>
                <Card
                    title={activeCA ? `Certificates by ${activeCA.name}` : 'Certificates'}
                    subtitle="Click a row to open complete certificate details"
                >
                    <div className={`transition-opacity duration-200 ${isCertsLoading ? 'opacity-50' : 'opacity-100'}`}>
                        <DataTable
                            data={tableData}
                            currentPage={currentPage}
                            totalPages={totalPages}
                            onPageChange={setCurrentPage}
                            onRowClick={handleRowClick}
                        />
                    </div>
                </Card>
            </div>
        </div>
    );
}
