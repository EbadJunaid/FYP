'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import Papa from 'papaparse';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as ReTooltip,
    ResponsiveContainer, Legend, ReferenceLine, Cell,
} from 'recharts';
import Card from '@/components/Card';
import MetricCard from '@/components/dashboard/MetricCard';
import { TrendUpIcon, ShieldIcon, CertificateIcon, CheckCircleIcon } from '@/components/icons/Icons';

// ── Types ───────────────────────────────────────────────────────────────

interface CASnapshot {
    ca: string;
    rank: number;
    score: number;
    lintHygiene: number;
    cryptoHealth: number;
    operations: number;
    policy: number;
    riskContext: number;
    certificates: number;
}

interface MonthData {
    label: string;
    entries: CASnapshot[];
    entryMap: Map<string, CASnapshot>;
}

interface AnalysisResult {
    allCAs: string[];
    firstMonth: MonthData;
    lastMonth: MonthData;
    rankingMovements: { ca: string; oldRank: number; newRank: number; change: number; oldScore: number; newScore: number; scoreChange: number }[];
    scoreTrendData: { month: string; [ca: string]: string | number }[];
    subScoreData: { category: string; [month: string]: string | number }[];
    newCAs: { ca: string; firstMonth: string; rank: number; score: number }[];
    disappearedCAs: { ca: string; lastMonth: string; rank: number; score: number }[];
    summary: { totalCAs: number; monthsCompared: number; improved: number; declined: number; unchanged: number; topMover: string; topMoverChange: number };
}

// ── Constants ───────────────────────────────────────────────────────────

const EXPECTED_COLUMNS = ['Rank', 'CA', 'Score', 'Lint Hygiene', 'Crypto Health', 'Operations', 'Policy', 'Risk Context', 'Certificates'];

const CHART_COLORS = [
    '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
    '#06b6d4', '#ec4899', '#f97316', '#14b8a6', '#6366f1',
    '#84cc16', '#e11d48', '#0ea5e9', '#a855f7', '#22c55e',
    '#eab308', '#dc2626', '#7c3aed', '#0891b2', '#d946ef',
];

const SUB_SCORE_KEYS = ['lintHygiene', 'cryptoHealth', 'operations', 'policy', 'riskContext'] as const;
const SUB_SCORE_LABELS: Record<string, string> = {
    lintHygiene: 'Lint Hygiene',
    cryptoHealth: 'Crypto Health',
    operations: 'Operations',
    policy: 'Policy',
    riskContext: 'Risk Context',
};

// ── Helpers ─────────────────────────────────────────────────────────────

function parseRank(raw: unknown): number {
    const match = String(raw).match(/#?(\d+)/);
    return match ? parseInt(match[1], 10) : 0;
}

function toNum(v: unknown): number {
    const n = parseFloat(String(v).replace(/,/g, ''));
    return isNaN(n) ? 0 : n;
}

function truncateCA(name: string, max = 24): string {
    return name.length > max ? name.slice(0, max - 1) + '…' : name;
}

function validateCSV(rows: Record<string, unknown>[]): string[] {
    const errors: string[] = [];
    if (rows.length === 0) { errors.push('File has no data rows'); return errors; }
    const headers = Object.keys(rows[0]);
    const missing = EXPECTED_COLUMNS.filter((c) => !headers.includes(c));
    if (missing.length) { errors.push(`Missing columns: ${missing.join(', ')}`); return errors; }
    for (let i = 0; i < Math.min(rows.length, 5); i++) {
        const r = rows[i];
        if (isNaN(toNum(r['Score']))) { errors.push(`Row ${i + 1}: Score is not a number`); break; }
    }
    return errors;
}

function parseCSVFile(file: File): Promise<{ data: CASnapshot[]; errors: string[] }> {
    return new Promise((resolve) => {
        Papa.parse(file, {
            header: true,
            skipEmptyLines: true,
            complete: (results) => {
                const raw = results.data as Record<string, unknown>[];
                const errors = validateCSV(raw);
                if (errors.length) { resolve({ data: [], errors }); return; }
                const data: CASnapshot[] = raw.map((r) => ({
                    ca: String(r['CA'] || '').trim(),
                    rank: parseRank(r['Rank']),
                    score: toNum(r['Score']),
                    lintHygiene: toNum(r['Lint Hygiene']),
                    cryptoHealth: toNum(r['Crypto Health']),
                    operations: toNum(r['Operations']),
                    policy: toNum(r['Policy']),
                    riskContext: toNum(r['Risk Context']),
                    certificates: Math.round(toNum(r['Certificates'])),
                })).filter((d) => d.ca);
                resolve({ data, errors: [] });
            },
            error: () => resolve({ data: [], errors: ['Failed to parse CSV file'] }),
        });
    });
}

function computeAnalysis(months: MonthData[]): AnalysisResult {
    const allCASets = months.map((m) => new Set(m.entries.map((e) => e.ca)));
    const allCAUnion = new Set<string>();
    allCASets.forEach((s) => s.forEach((ca) => allCAUnion.add(ca)));
    const allCAs = Array.from(allCAUnion);

    const first = months[0];
    const last = months[months.length - 1];

    const movementMap = new Map<string, { oldRank: number; newRank: number; oldScore: number; newScore: number }>();
    for (const ca of allCAs) {
        const old = first.entryMap.get(ca);
        const cur = last.entryMap.get(ca);
        movementMap.set(ca, {
            oldRank: old?.rank ?? 9999,
            newRank: cur?.rank ?? 9999,
            oldScore: old?.score ?? 0,
            newScore: cur?.score ?? 0,
        });
    }

    const rankingMovements = allCAs.map((ca) => {
        const m = movementMap.get(ca)!;
        return {
            ca,
            oldRank: m.oldRank,
            newRank: m.newRank,
            change: m.oldRank - m.newRank,
            oldScore: m.oldScore,
            newScore: m.newScore,
            scoreChange: Math.round((m.newScore - m.oldScore) * 100) / 100,
        };
    }).filter((r) => r.oldRank < 9999 && r.newRank < 9999);

    const scoreTrendData = months.map((m) => {
        const point: { month: string; [ca: string]: string | number } = { month: m.label };
        for (const ca of allCAs) {
            const entry = m.entryMap.get(ca);
            if (entry) point[ca] = entry.score;
        }
        return point;
    });

    const subScoreData = SUB_SCORE_KEYS.map((key) => {
        const point: { category: string; [month: string]: string | number } = { category: SUB_SCORE_LABELS[key] };
        for (const m of months) {
            const vals = m.entries.map((e) => e[key]);
            point[m.label] = vals.length ? Math.round((vals.reduce((a, b) => a + b, 0) / vals.length) * 100) / 100 : 0;
        }
        return point;
    });

    const firstCASet = allCASets[0];
    const lastCASet = allCASets[allCASets.length - 1];
    const newCAs = allCAs.filter((ca) => !firstCASet.has(ca)).map((ca) => {
        const e = last.entryMap.get(ca);
        return { ca, firstMonth: last.label, rank: e?.rank ?? 0, score: e?.score ?? 0 };
    });
    const disappearedCAs = allCAs.filter((ca) => !lastCASet.has(ca)).map((ca) => {
        const e = first.entryMap.get(ca);
        return { ca, lastMonth: first.label, rank: e?.rank ?? 0, score: e?.score ?? 0 };
    });

    let improved = 0, declined = 0, unchanged = 0;
    for (const r of rankingMovements) {
        if (r.change > 0) improved++;
        else if (r.change < 0) declined++;
        else unchanged++;
    }
    const sorted = [...rankingMovements].sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
    const topMover = sorted[0];

    return {
        allCAs,
        firstMonth: first,
        lastMonth: last,
        rankingMovements,
        scoreTrendData,
        subScoreData,
        newCAs,
        disappearedCAs,
        summary: {
            totalCAs: allCAs.length,
            monthsCompared: months.length,
            improved,
            declined,
            unchanged,
            topMover: topMover?.ca || 'N/A',
            topMoverChange: topMover?.change || 0,
        },
    };
}

// ── Custom Tooltip ──────────────────────────────────────────────────────

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ name: string; value: number; color: string }>; label?: string }) {
    if (!active || !payload?.length) return null;
    return (
        <div className="bg-[#1f2937] border border-[#374151] rounded-lg px-3 py-2 shadow-lg text-xs">
            <p className="text-text-primary font-medium mb-1">{label}</p>
            {payload.map((p, i) => (
                <p key={i} style={{ color: p.color }} className="flex justify-between gap-4">
                    <span className="text-text-secondary">{p.name}:</span>
                    <span className="font-medium">{typeof p.value === 'number' ? p.value.toFixed(2) : p.value}</span>
                </p>
            ))}
        </div>
    );
}

// ── Upload Phase ────────────────────────────────────────────────────────

interface UploadCardState {
    label: string;
    file: File | null;
    data: CASnapshot[];
    errors: string[];
    loading: boolean;
}

function UploadPhase({ onAnalyze }: { onAnalyze: (months: MonthData[]) => void }) {
    const [monthCount, setMonthCount] = useState(2);
    const [cards, setCards] = useState<UploadCardState[]>(() =>
        Array.from({ length: 12 }, (_, i) => ({ label: `Month ${i + 1}`, file: null, data: [], errors: [], loading: false }))
    );
    const [globalErrors, setGlobalErrors] = useState<string[]>([]);
    const fileRefs = useRef<(HTMLInputElement | null)[]>([]);

    useEffect(() => {
        setCards((prev) => {
            const next = [...prev];
            while (next.length < 12) next.push({ label: `Month ${next.length + 1}`, file: null, data: [], errors: [], loading: false });
            return next;
        });
    }, []);

    const updateCard = useCallback((idx: number, patch: Partial<UploadCardState>) => {
        setCards((prev) => prev.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
    }, []);

    const handleFile = useCallback(async (idx: number, file: File) => {
        if (!file.name.endsWith('.csv')) {
            updateCard(idx, { errors: ['Please upload a .csv file'], file: null, data: [] });
            return;
        }
        if (file.size > 10 * 1024 * 1024) {
            updateCard(idx, { errors: ['File too large (max 10MB)'], file: null, data: [] });
            return;
        }
        updateCard(idx, { file, loading: true, errors: [], data: [] });
        const { data, errors } = await parseCSVFile(file);
        updateCard(idx, { data, errors, loading: false });
    }, [updateCard]);

    const handleDrop = useCallback((idx: number, e: React.DragEvent) => {
        e.preventDefault();
        e.stopPropagation();
        const file = e.dataTransfer.files?.[0];
        if (file) handleFile(idx, file);
    }, [handleFile]);

    const handleAnalyze = useCallback(() => {
        const errs: string[] = [];
        const months: MonthData[] = [];
        for (let i = 0; i < monthCount; i++) {
            const c = cards[i];
            if (!c.data.length) { errs.push(`Month ${i + 1}: No valid data uploaded`); continue; }
            months.push({
                label: c.label || `Month ${i + 1}`,
                entries: c.data,
                entryMap: new Map(c.data.map((e) => [e.ca, e])),
            });
        }
        if (months.length < 2) { errs.push('At least 2 valid months are required'); }
        if (errs.length) { setGlobalErrors(errs); return; }
        setGlobalErrors([]);
        onAnalyze(months);
    }, [monthCount, cards, onAnalyze]);

    const active = cards.slice(0, monthCount);
    const allReady = active.every((c) => c.data.length > 0);
    const totalRows = active.reduce((s, c) => s + c.data.length, 0);

    return (
        <div className="space-y-6">
            <div>
                <h1 className="text-2xl font-bold text-text-primary">CA Ranking Trends</h1>
                <p className="text-text-muted mt-1">Compare Certificate Authority rankings across months</p>
            </div>

            <Card title="Select Number of Months">
                <div className="flex flex-wrap gap-2">
                    {[2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12].map((n) => (
                        <button
                            key={n}
                            onClick={() => setMonthCount(n)}
                            className={`w-10 h-10 rounded-lg text-sm font-medium transition-all ${
                                monthCount === n
                                    ? 'bg-primary-blue text-white shadow-md'
                                    : 'bg-background text-text-secondary hover:bg-card-border'
                            }`}
                        >
                            {n}
                        </button>
                    ))}
                </div>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
                {active.map((card, idx) => (
                    <div
                        key={idx}
                        className={`bg-card-bg border rounded-2xl p-5 transition-all ${
                            card.errors.length ? 'border-accent-red' : card.data.length ? 'border-accent-green/50' : 'border-card-border'
                        }`}
                    >
                        <div className="flex items-center justify-between mb-3">
                            <span className="text-xs font-medium text-text-muted uppercase tracking-wider">Month {idx + 1}</span>
                            {card.data.length > 0 && (
                                <span className="text-xs text-accent-green flex items-center gap-1">
                                    <CheckCircleIcon className="w-3.5 h-3.5" /> {card.data.length} CAs
                                </span>
                            )}
                        </div>
                        <input
                            type="text"
                            value={card.label}
                            onChange={(e) => updateCard(idx, { label: e.target.value })}
                            placeholder="e.g. January 2026"
                            className="w-full px-3 py-2 mb-3 bg-background border border-card-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-blue"
                        />
                        <div
                            onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                            onDrop={(e) => handleDrop(idx, e)}
                            onClick={() => fileRefs.current[idx]?.click()}
                            className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all ${
                                card.loading
                                    ? 'border-primary-blue/30 bg-primary-blue/5'
                                    : card.data.length
                                    ? 'border-accent-green/30 bg-accent-green/5'
                                    : 'border-card-border hover:border-primary-blue/50 hover:bg-primary-blue/5'
                            }`}
                        >
                            <input
                                ref={(el) => { fileRefs.current[idx] = el; }}
                                type="file"
                                accept=".csv"
                                className="hidden"
                                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(idx, f); e.target.value = ''; }}
                            />
                            {card.loading ? (
                                <div className="flex flex-col items-center gap-2">
                                    <div className="w-6 h-6 border-2 border-primary-blue border-t-transparent rounded-full animate-spin" />
                                    <span className="text-xs text-text-muted">Parsing...</span>
                                </div>
                            ) : card.data.length > 0 ? (
                                <div className="flex flex-col items-center gap-1">
                                    <span className="text-sm text-text-primary font-medium">{card.file?.name}</span>
                                    <span className="text-xs text-text-muted">Click or drop to replace</span>
                                </div>
                            ) : (
                                <div className="flex flex-col items-center gap-1">
                                    <svg className="w-8 h-8 text-text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" /></svg>
                                    <span className="text-xs text-text-muted">Drop CSV here or click to browse</span>
                                </div>
                            )}
                        </div>
                        {card.errors.length > 0 && (
                            <div className="mt-2 space-y-1">
                                {card.errors.map((err, ei) => (
                                    <p key={ei} className="text-xs text-accent-red">{err}</p>
                                ))}
                            </div>
                        )}
                    </div>
                ))}
            </div>

            {globalErrors.length > 0 && (
                <div className="bg-accent-red/10 border border-accent-red/30 rounded-xl p-4">
                    {globalErrors.map((err, i) => (
                        <p key={i} className="text-sm text-accent-red">{err}</p>
                    ))}
                </div>
            )}

            <div className="flex items-center justify-between">
                <p className="text-sm text-text-muted">
                    {allReady ? `${monthCount} months ready — ${totalRows.toLocaleString()} total CA entries` : 'Upload a CSV for each month to continue'}
                </p>
                <button
                    onClick={handleAnalyze}
                    disabled={!allReady}
                    className="px-6 py-2.5 bg-primary-blue text-white rounded-xl text-sm font-medium transition-all hover:bg-primary-blue/90 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                    Analyze Trends
                </button>
            </div>
        </div>
    );
}

// ── Analysis Dashboard ──────────────────────────────────────────────────

function AnalysisDashboard({ months, onReset }: { months: MonthData[]; onReset: () => void }) {
    const analysis = useMemo(() => computeAnalysis(months), [months]);
    const [scoreCAFilter, setScoreCAFilter] = useState('');
    const [selectedScoreCAs, setSelectedScoreCAs] = useState<Set<string>>(() => new Set(analysis.allCAs.slice(0, 10)));
    const [subScoreCA, setSubScoreCA] = useState(analysis.summary.topMover);
    const totalCAs = analysis.allCAs.length;
    const [rankLimit, setRankLimit] = useState<number | 'all'>(10);
    const [rankInput, setRankInput] = useState('10');
    const [rankWarning, setRankWarning] = useState('');
    const [scoreLimit, setScoreLimit] = useState<number | 'all'>(10);
    const [scoreInput, setScoreInput] = useState('10');
    const [scoreWarning, setScoreWarning] = useState('');
    const [tableSearch, setTableSearch] = useState('');
    const [tablePage, setTablePage] = useState(1);
    const [sortCol, setSortCol] = useState<string>('rankChange');
    const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc');
    const tablePageSize = 25;

    useEffect(() => { setTablePage(1); }, [tableSearch]);

    const toggleScoreCA = useCallback((ca: string) => {
        setSelectedScoreCAs((prev) => {
            const next = new Set(prev);
            if (next.has(ca)) next.delete(ca); else next.add(ca);
            return next;
        });
    }, []);

    const clearSelectedScoreCAs = useCallback(() => {
        setSelectedScoreCAs(new Set());
    }, []);

    const applyRankLimit = useCallback(() => {
        const val = rankInput.trim();
        if (val === '' || val.toLowerCase() === 'all') { setRankLimit('all'); setRankInput('All'); setRankWarning(''); return; }
        const n = parseInt(val, 10);
        if (isNaN(n) || n < 2) { setRankLimit(2); setRankInput('2'); setRankWarning(''); return; }
        if (n > totalCAs) {
            setRankLimit(totalCAs);
            setRankInput(String(totalCAs));
            setRankWarning(`Only ${totalCAs} CAs available — showing all`);
        } else {
            setRankLimit(n);
            setRankInput(String(n));
            setRankWarning('');
        }
    }, [rankInput, totalCAs]);

    const applyScoreLimit = useCallback(() => {
        const val = scoreInput.trim();
        if (val === '' || val.toLowerCase() === 'all') { setScoreLimit('all'); setScoreInput('All'); setScoreWarning(''); return; }
        const n = parseInt(val, 10);
        if (isNaN(n) || n < 2) { setScoreLimit(2); setScoreInput('2'); setScoreWarning(''); return; }
        if (n > totalCAs) {
            setScoreLimit(totalCAs);
            setScoreInput(String(totalCAs));
            setScoreWarning(`Only ${totalCAs} CAs available — showing all`);
        } else {
            setScoreLimit(n);
            setScoreInput(String(n));
            setScoreWarning('');
        }
    }, [scoreInput, totalCAs]);

    const filteredScoreCAs = useMemo(() => {
        const pool = scoreCAFilter
            ? analysis.allCAs.filter((ca) => ca.toLowerCase().includes(scoreCAFilter.toLowerCase()))
            : analysis.allCAs;
        return pool;
    }, [analysis.allCAs, scoreCAFilter]);

    const displayedScoreCAs = useMemo(() => {
        if (scoreLimit === 'all') return filteredScoreCAs;
        return filteredScoreCAs.slice(0, scoreLimit);
    }, [filteredScoreCAs, scoreLimit]);

    const displayedRankMovements = useMemo(() => {
        const sorted = [...analysis.rankingMovements].sort((a, b) => Math.abs(b.change) - Math.abs(a.change));
        if (rankLimit === 'all') return sorted;
        return sorted.slice(0, rankLimit);
    }, [analysis.rankingMovements, rankLimit]);

    const topMovements = useMemo(() => {
        return [...analysis.rankingMovements].sort((a, b) => Math.abs(b.change) - Math.abs(a.change)).slice(0, 20);
    }, [analysis.rankingMovements]);

    const scoreTrendForChart = useMemo(() => {
        const cas = scoreLimit === 'all' ? analysis.allCAs : analysis.allCAs.slice(0, scoreLimit);
        const activeCAs = selectedScoreCAs.size > 0 ? cas.filter((ca) => selectedScoreCAs.has(ca)) : cas.slice(0, 10);
        return analysis.scoreTrendData.map((point) => {
            const filtered: Record<string, string | number> = { month: point.month };
            for (const ca of activeCAs) {
                if (ca in point) filtered[ca] = point[ca];
            }
            return filtered;
        });
    }, [analysis.scoreTrendData, analysis.allCAs, selectedScoreCAs, scoreLimit]);

    const subScoreForChart = useMemo(() => {
        const ca = analysis.firstMonth.entryMap.get(subScoreCA) || analysis.lastMonth.entryMap.get(subScoreCA);
        if (!ca) return analysis.subScoreData;
        return SUB_SCORE_KEYS.map((key) => {
            const point: { category: string; [month: string]: string | number } = { category: SUB_SCORE_LABELS[key] };
            for (const m of months) {
                const entry = m.entryMap.get(subScoreCA);
                point[m.label] = entry ? entry[key] : 0;
            }
            return point;
        });
    }, [analysis.subScoreData, subScoreCA, months, analysis.firstMonth, analysis.lastMonth]);

    const tableData = useMemo(() => {
        let rows = analysis.rankingMovements.map((r) => ({ ...r }));
        if (tableSearch) {
            const q = tableSearch.toLowerCase();
            rows = rows.filter((r) => r.ca.toLowerCase().includes(q));
        }
        rows.sort((a, b) => {
            let va: number, vb: number;
            switch (sortCol) {
                case 'ca': return sortDir === 'asc' ? a.ca.localeCompare(b.ca) : b.ca.localeCompare(a.ca);
                case 'rankChange': va = a.change; vb = b.change; break;
                case 'scoreChange': va = a.scoreChange; vb = b.scoreChange; break;
                case 'oldRank': va = a.oldRank; vb = b.oldRank; break;
                case 'newRank': va = a.newRank; vb = b.newRank; break;
                case 'oldScore': va = a.oldScore; vb = b.oldScore; break;
                case 'newScore': va = a.newScore; vb = b.newScore; break;
                default: va = a.change; vb = b.change;
            }
            return sortDir === 'asc' ? va - vb : vb - va;
        });
        return rows;
    }, [analysis.rankingMovements, tableSearch, sortCol, sortDir]);

    const tableTotalPages = Math.max(1, Math.ceil(tableData.length / tablePageSize));
    const pagedTableData = tableData.slice((tablePage - 1) * tablePageSize, tablePage * tablePageSize);

    const handleSort = useCallback((col: string) => {
        setSortCol((prev) => {
            if (prev === col) { setSortDir((d) => d === 'asc' ? 'desc' : 'asc'); return col; }
            setSortDir('desc');
            return col;
        });
    }, []);

    const SortIcon = ({ col }: { col: string }) => {
        if (sortCol !== col) return <span className="text-text-muted ml-1">↕</span>;
        return <span className="text-primary-blue ml-1">{sortDir === 'asc' ? '↑' : '↓'}</span>;
    };

    const monthLabels = months.map((m) => m.label);
    const lastLabel = monthLabels[monthLabels.length - 1];
    const firstLabel = monthLabels[0];

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-text-primary">CA Ranking Trends</h1>
                    <p className="text-text-muted mt-1">
                        Comparing {analysis.summary.monthsCompared} months — {firstLabel} → {lastLabel}
                    </p>
                </div>
                <button
                    onClick={onReset}
                    className="px-4 py-2 text-sm text-text-secondary border border-card-border rounded-xl hover:bg-background transition-colors"
                >
                    ← New Analysis
                </button>
            </div>

            {/* Summary Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
                <MetricCard
                    icon={<CertificateIcon className="w-6 h-6 text-primary-blue" />}
                    iconBgColor="bg-primary-blue/15"
                    value={analysis.summary.totalCAs.toLocaleString()}
                    label="Unique CAs Tracked"
                />
                <MetricCard
                    icon={<CheckCircleIcon className="w-6 h-6 text-primary-purple" />}
                    iconBgColor="bg-primary-purple/15"
                    value={`${analysis.summary.monthsCompared}`}
                    label="Months Compared"
                />
                <MetricCard
                    icon={<TrendUpIcon className="w-6 h-6 text-accent-green" />}
                    iconBgColor="bg-accent-green/15"
                    value={`${analysis.summary.improved} / ${analysis.summary.declined}`}
                    label="CAs Improved / Declined"
                />
                <MetricCard
                    icon={<ShieldIcon className="w-6 h-6 text-accent-yellow" />}
                    iconBgColor="bg-accent-yellow/15"
                    value={`${analysis.summary.topMoverChange > 0 ? '+' : ''}${analysis.summary.topMoverChange}`}
                    label={`Top Mover: ${truncateCA(analysis.summary.topMover, 20)}`}
                />
            </div>

            {/* Ranking Movement Chart */}
            <Card
                title="Ranking Movements"
                subtitle={`Biggest rank changes (${firstLabel} → ${lastLabel})`}
                headerAction={
                    <div className="flex items-center gap-1.5">
                        <span className="text-xs text-text-muted hidden sm:inline">Show</span>
                        <input
                            type="text"
                            value={rankInput}
                            onChange={(e) => setRankInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') applyRankLimit(); }}
                            onBlur={applyRankLimit}
                            placeholder="All"
                            className="w-16 px-2 py-1 text-xs bg-background border border-card-border rounded-lg text-text-primary text-center focus:outline-none focus:border-primary-blue"
                        />
                        <span className="text-xs text-text-muted hidden sm:inline">/ {totalCAs}</span>
                        <button onClick={applyRankLimit} className="px-2.5 py-1 text-xs rounded-lg transition-colors bg-primary-blue text-white">Apply</button>
                        <button onClick={() => { setRankLimit('all'); setRankInput('All'); setRankWarning(''); }} className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${rankLimit === 'all' ? 'bg-primary-blue text-white' : 'text-text-muted hover:text-text-primary'}`}>All</button>
                    </div>
                }
            >
                {rankWarning && <p className="text-xs text-accent-yellow mb-2">{rankWarning}</p>}
                <ResponsiveContainer width="100%" height={Math.min(800, Math.max(400, displayedRankMovements.length * 30 + 60))} minHeight={400}>
                    <BarChart layout="vertical" data={displayedRankMovements} margin={{ top: 5, right: 30, left: 10, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis type="number" stroke="#9ca3af" fontSize={12} label={{ value: 'Rank Change', position: 'insideBottom', offset: -5, fill: '#9ca3af', fontSize: 11 }} />
                        <YAxis type="category" dataKey="ca" stroke="#9ca3af" fontSize={11} width={160} tickFormatter={(v) => truncateCA(v, 20)} />
                        <ReTooltip content={<ChartTooltip />} />
                        <ReferenceLine x={0} stroke="#4b5563" strokeWidth={1} />
                        <Bar dataKey="change" radius={[0, 4, 4, 0]} name="Rank Change">
                            {displayedRankMovements.map((entry, i) => (
                                <Cell key={i} fill={entry.change > 0 ? '#10b981' : '#ef4444'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </Card>

            {/* Score Trend Line Chart */}
            <Card
                title="Score Trends Over Time"
                subtitle="Track CA scores across months"
                headerAction={
                    <div className="flex items-center gap-1.5">
                        <span className="text-xs text-text-muted hidden sm:inline">Show</span>
                        <input
                            type="text"
                            value={scoreInput}
                            onChange={(e) => setScoreInput(e.target.value)}
                            onKeyDown={(e) => { if (e.key === 'Enter') applyScoreLimit(); }}
                            onBlur={applyScoreLimit}
                            placeholder="All"
                            className="w-16 px-2 py-1 text-xs bg-background border border-card-border rounded-lg text-text-primary text-center focus:outline-none focus:border-primary-blue"
                        />
                        <span className="text-xs text-text-muted hidden sm:inline">/ {totalCAs}</span>
                        <button onClick={applyScoreLimit} className="px-2.5 py-1 text-xs rounded-lg transition-colors bg-primary-blue text-white">Apply</button>
                        <button onClick={() => { setScoreLimit('all'); setScoreInput('All'); setScoreWarning(''); }} className={`px-2.5 py-1 text-xs rounded-lg transition-colors ${scoreLimit === 'all' ? 'bg-primary-blue text-white' : 'text-text-muted hover:text-text-primary'}`}>All</button>
                    </div>
                }
            >
                {scoreWarning && <p className="text-xs text-accent-yellow mb-2">{scoreWarning}</p>}
                <div className="mb-3">
                    <div className="flex items-center gap-2 mb-2">
                        <input
                            type="text"
                            value={scoreCAFilter}
                            onChange={(e) => setScoreCAFilter(e.target.value)}
                            placeholder="Search CAs to add..."
                            className="w-full max-w-sm px-3 py-1.5 bg-background border border-card-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-blue"
                        />
                        {selectedScoreCAs.size > 0 && (
                            <button onClick={clearSelectedScoreCAs} className="px-2.5 py-1 text-xs rounded-lg transition-colors border border-card-border text-text-muted hover:text-accent-red hover:border-accent-red/50 whitespace-nowrap">
                                Remove All
                            </button>
                        )}
                    </div>
                    <div className="flex flex-wrap gap-1 mt-2 max-h-24 overflow-y-auto">
                        {displayedScoreCAs.map((ca) => (
                            <button
                                key={ca}
                                onClick={() => toggleScoreCA(ca)}
                                className={`px-2 py-0.5 text-xs rounded-full transition-colors ${
                                    selectedScoreCAs.has(ca) ? 'bg-primary-blue text-white' : 'bg-background text-text-muted border border-card-border hover:text-text-primary'
                                }`}
                            >
                                {truncateCA(ca, 16)}
                            </button>
                        ))}
                    </div>
                </div>
                <ResponsiveContainer width="100%" height={400}>
                    <LineChart data={scoreTrendForChart} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="month" stroke="#9ca3af" fontSize={12} />
                        <YAxis stroke="#9ca3af" fontSize={12} domain={[0, 100]} />
                        <ReTooltip content={<ChartTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                        {Array.from(selectedScoreCAs).filter((ca) => scoreLimit === 'all' || analysis.allCAs.indexOf(ca) < scoreLimit).slice(0, 20).map((ca, i) => (
                            <Line
                                key={ca}
                                type="monotone"
                                dataKey={ca}
                                name={truncateCA(ca, 20)}
                                stroke={CHART_COLORS[i % CHART_COLORS.length]}
                                strokeWidth={2}
                                dot={{ r: 3 }}
                                activeDot={{ r: 5 }}
                                connectNulls
                            />
                        ))}
                    </LineChart>
                </ResponsiveContainer>
            </Card>

            {/* Sub-Score Breakdown */}
            <Card title="Sub-Score Breakdown" subtitle="Average sub-scores across all CAs per month">
                <ResponsiveContainer width="100%" height={350}>
                    <BarChart data={subScoreForChart} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                        <XAxis dataKey="category" stroke="#9ca3af" fontSize={12} />
                        <YAxis stroke="#9ca3af" fontSize={12} domain={[0, 100]} />
                        <ReTooltip content={<ChartTooltip />} />
                        <Legend wrapperStyle={{ fontSize: 11, paddingTop: 10 }} />
                        {monthLabels.map((label, i) => (
                            <Bar key={label} dataKey={label} fill={CHART_COLORS[i % CHART_COLORS.length]} radius={[4, 4, 0, 0]} />
                        ))}
                    </BarChart>
                </ResponsiveContainer>
            </Card>

            {/* New & Disappeared CAs */}
            {(analysis.newCAs.length > 0 || analysis.disappearedCAs.length > 0) && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {analysis.newCAs.length > 0 && (
                        <Card title={`New CAs (${analysis.newCAs.length})`} subtitle="CAs appearing in later months">
                            <div className="max-h-60 overflow-y-auto space-y-1">
                                {analysis.newCAs.slice(0, 50).map((ca) => (
                                    <div key={ca.ca} className="flex items-center justify-between py-1 px-2 rounded-lg hover:bg-background text-sm">
                                        <span className="text-text-primary truncate">{truncateCA(ca.ca, 30)}</span>
                                        <span className="text-xs text-text-muted shrink-0 ml-2">Rank #{ca.rank}</span>
                                    </div>
                                ))}
                                {analysis.newCAs.length > 50 && <p className="text-xs text-text-muted text-center py-1">+ {analysis.newCAs.length - 50} more</p>}
                            </div>
                        </Card>
                    )}
                    {analysis.disappearedCAs.length > 0 && (
                        <Card title={`Disappeared CAs (${analysis.disappearedCAs.length})`} subtitle="CAs no longer present in the latest month">
                            <div className="max-h-60 overflow-y-auto space-y-1">
                                {analysis.disappearedCAs.slice(0, 50).map((ca) => (
                                    <div key={ca.ca} className="flex items-center justify-between py-1 px-2 rounded-lg hover:bg-background text-sm">
                                        <span className="text-text-primary truncate">{truncateCA(ca.ca, 30)}</span>
                                        <span className="text-xs text-text-muted shrink-0 ml-2">Was #{ca.rank}</span>
                                    </div>
                                ))}
                                {analysis.disappearedCAs.length > 50 && <p className="text-xs text-text-muted text-center py-1">+ {analysis.disappearedCAs.length - 50} more</p>}
                            </div>
                        </Card>
                    )}
                </div>
            )}

            {/* Full Comparison Table */}
            <Card
                title="Full Comparison Table"
                subtitle={`${tableData.length} CAs — click column headers to sort`}
                headerAction={
                    <input
                        type="text"
                        value={tableSearch}
                        onChange={(e) => setTableSearch(e.target.value)}
                        placeholder="Search CA..."
                        className="w-48 px-3 py-1.5 bg-background border border-card-border rounded-lg text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-primary-blue"
                    />
                }
            >
                <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-card-border">
                                <th className="text-left py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('ca')}>
                                    CA <SortIcon col="ca" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('oldRank')}>
                                    {firstLabel} Rank <SortIcon col="oldRank" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('newRank')}>
                                    {lastLabel} Rank <SortIcon col="newRank" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('rankChange')}>
                                    Rank Δ <SortIcon col="rankChange" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('oldScore')}>
                                    {firstLabel} Score <SortIcon col="oldScore" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('newScore')}>
                                    {lastLabel} Score <SortIcon col="newScore" />
                                </th>
                                <th className="text-center py-2 px-3 text-xs font-medium text-text-muted cursor-pointer hover:text-text-primary" onClick={() => handleSort('scoreChange')}>
                                    Score Δ <SortIcon col="scoreChange" />
                                </th>
                            </tr>
                        </thead>
                        <tbody>
                            {pagedTableData.map((row) => (
                                <tr key={row.ca} className={`border-b border-card-border/50 hover:bg-background transition-colors ${Math.abs(row.change) >= 5 ? 'bg-primary-blue/5' : ''}`}>
                                    <td className="py-2 px-3 text-text-primary font-medium truncate max-w-[200px]" title={row.ca}>{truncateCA(row.ca, 28)}</td>
                                    <td className="py-2 px-3 text-center text-text-secondary">#{row.oldRank}</td>
                                    <td className="py-2 px-3 text-center text-text-secondary">#{row.newRank}</td>
                                    <td className="py-2 px-3 text-center">
                                        <span className={`inline-flex items-center gap-0.5 text-xs font-medium px-1.5 py-0.5 rounded-full ${
                                            row.change > 0 ? 'bg-accent-green/15 text-accent-green' : row.change < 0 ? 'bg-accent-red/15 text-accent-red' : 'bg-background text-text-muted'
                                        }`}>
                                            {row.change > 0 ? '↑' : row.change < 0 ? '↓' : '—'} {Math.abs(row.change)}
                                        </span>
                                    </td>
                                    <td className="py-2 px-3 text-center text-text-secondary">{row.oldScore.toFixed(2)}</td>
                                    <td className="py-2 px-3 text-center text-text-secondary">{row.newScore.toFixed(2)}</td>
                                    <td className="py-2 px-3 text-center">
                                        <span className={`text-xs font-medium ${row.scoreChange > 0 ? 'text-accent-green' : row.scoreChange < 0 ? 'text-accent-red' : 'text-text-muted'}`}>
                                            {row.scoreChange > 0 ? '+' : ''}{row.scoreChange.toFixed(2)}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
                {tableTotalPages > 1 && (
                    <div className="flex items-center justify-between mt-4 pt-3 border-t border-card-border">
                        <p className="text-xs text-text-muted">
                            Showing {(tablePage - 1) * tablePageSize + 1}–{Math.min(tablePage * tablePageSize, tableData.length)} of {tableData.length}
                        </p>
                        <div className="flex gap-1">
                            <button
                                onClick={() => setTablePage((p) => Math.max(1, p - 1))}
                                disabled={tablePage === 1}
                                className="px-3 py-1 text-xs rounded-lg border border-card-border text-text-secondary hover:bg-background disabled:opacity-40"
                            >
                                Prev
                            </button>
                            <span className="px-3 py-1 text-xs text-text-muted">
                                {tablePage} / {tableTotalPages}
                            </span>
                            <button
                                onClick={() => setTablePage((p) => Math.min(tableTotalPages, p + 1))}
                                disabled={tablePage === tableTotalPages}
                                className="px-3 py-1 text-xs rounded-lg border border-card-border text-text-secondary hover:bg-background disabled:opacity-40"
                            >
                                Next
                            </button>
                        </div>
                    </div>
                )}
            </Card>
        </div>
    );
}

// ── Page ────────────────────────────────────────────────────────────────

export default function CARankingTrendsPage() {
    const [months, setMonths] = useState<MonthData[] | null>(null);
    return months ? (
        <AnalysisDashboard months={months} onReset={() => setMonths(null)} />
    ) : (
        <UploadPhase onAnalyze={setMonths} />
    );
}
