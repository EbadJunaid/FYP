"use client";
import React, { useRef } from "react";
import { Line } from "react-chartjs-2";
import {
  Chart as ChartJS,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from "chart.js";
import { useRouter } from "next/navigation";

ChartJS.register(
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler
);

interface MultiLineChartProps {
  labels: string[];
  issued: number[];
  active: number[];
  expired: number[];
  soon: number[];
  hrefs?: (string | undefined)[]; // same logic as DonutChart
}

const seriesColors = [
  "#404755ff", // Issued
  "#2b31deff", // Active
  "#EF476F",   // Expired
  "#FFD166",   // Expiring Soon
];

export default function MultiLineChart({
  labels,
  issued,
  active,
  expired,
  soon,
  hrefs,
}: MultiLineChartProps) {
  const router = useRouter();
  const chartRef = useRef<any>(null);

  const handlePointClick = (index: number) => {
    if (!hrefs) return;              // no hrefs → do nothing
    const href = hrefs[index];
    if (href === undefined) return;  // undefined → do nothing
    if (!href) alert("🚧 Feature in progress..."); // empty string → show alert
    else router.push(href);          // navigate
  };

  const datasets = [
    {
      label: "Issued",
      data: issued,
      borderColor: seriesColors[0],
      backgroundColor: `${seriesColors[0]}66`,
      tension: 0.3,
      fill: false,
      pointRadius: 6,      // 👈 slightly larger point
      pointHoverRadius: 8,  // 👈 bigger on hover
      pointHitRadius: 15,  
    },
    {
      label: "Active",
      data: active,
      borderColor: seriesColors[1],
      backgroundColor: `${seriesColors[1]}66`,
      tension: 0.3,
      fill: false,
      pointRadius: 6,      // 👈 slightly larger point
      pointHoverRadius: 8,  // 👈 bigger on hover
      pointHitRadius: 15,
    },
    {
      label: "Expired",
      data: expired,
      borderColor: seriesColors[2],
      backgroundColor: `${seriesColors[2]}66`,
      tension: 0.3,
      fill: false,
      pointRadius: 6,      // 👈 slightly larger point
      pointHoverRadius: 8,  // 👈 bigger on hover
      pointHitRadius: 15,
    },
    {
      label: "Expiring Soon",
      data: soon,
      borderColor: seriesColors[3],
      backgroundColor: `${seriesColors[3]}66`,
      tension: 0.3,
      fill: false,
      pointRadius: 6,      // 👈 slightly larger point
      pointHoverRadius: 8,  // 👈 bigger on hover
      pointHitRadius: 15,
    },
  ];

  const options = {
    responsive: true,
    plugins: {
      legend: { position: "bottom" as const },
      tooltip: { mode: "index" as const, intersect: false },
    },
    scales: {
    y: {
      beginAtZero: true,
      ticks: {
        stepSize: 500,
        autoSkip: false,
        maxTicksLimit: 10,  // ✅ controls vertical spacing (adjust as you like)
      },
    },
  },
    onClick: (event: any) => {
      const chart = chartRef.current;
      if (!chart) return;
      const points = chart.getElementsAtEventForMode(
        event,
        "nearest",
        { intersect: false },
        false
      );
      if (!points.length) return;

      const { index } = points[0]; // same as DonutChart logic
      handlePointClick(index);
    },
  };

  const data = { labels, datasets };

  return (
    <div className="w-full h-[320px] py-20">
      <Line ref={chartRef} data={data} options={options}/>
    </div>
  );
}
