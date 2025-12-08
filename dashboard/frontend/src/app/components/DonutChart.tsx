"use client";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from 'chart.js';
import React, { useRef } from "react";
import { useRouter } from "next/navigation";

ChartJS.register(ArcElement, Tooltip, Legend);

interface DonutChartProps {
  data: number[];
  labels: string[];
  colors?: string[];                      // Optional: colors for segments, auto-repeat if fewer than labels
  hrefs?: (string | undefined)[];         // Optional: route for each segment
  legendPosition?: "bottom" | "top" | "left" | "right";
  width?: number | string;
  height?: number | string;
  options?: any;                          // Optional: further Chart.js options
}

const DEFAULT_COLORS = [
  "#3d60b0ff", "#e8a200ff", "#EF476F", "#55c2e0", "#64c678", "#b376f7", "#fbbe5b", "#fa658c"
];

export default function DonutChart({
  data,
  labels,
  colors,
  hrefs,
  legendPosition = "bottom",
  width = "100%",
  height = 320,
  options = {},
}: DonutChartProps) {
  const chartRef = useRef<any>(null);
  const router = useRouter();

  // Compute colors array to match data length, repeating if necessary
  const computedColors =
    (colors && colors.length > 0)
      ? Array(data.length)
          .fill(null)
          .map((_, i) => colors[i % colors.length])
      : Array(data.length)
          .fill(null)
          .map((_, i) => DEFAULT_COLORS[i % DEFAULT_COLORS.length]);

  // Click handler for navigating per segment
  const handleSegmentClick = (index: number) => {
    if (!hrefs) return;
    const href = hrefs[index];
    if (href === undefined) return;
    if (!href) alert("🚧 Feature in progress...");
    else router.push(href);
  };

  // Chart.js options with merge/override support
  const mergedOptions = {
    plugins: {
      legend: {
        display: true,
        position: legendPosition,
        labels: {
          color: "#222222", // dark for visibility
          padding: 18,
          boxWidth: 20,
        }
      },
      tooltip: {
        callbacks: {
          label: (context: any) => {
            const label = context.label || "";
            const value = context.parsed ?? "";
            return `${label}: ${value}`;
          }
        }
      }
    },
    onClick: (evt: any) => {
      if (!chartRef.current) return;
      const points = chartRef.current.getElementsAtEventForMode(
        evt,
        'nearest',
        { intersect: true },
        false
      );
      if (points.length) {
        const { index } = points[0];
        handleSegmentClick(index);
      }
    },
    ...options,
  };

  const chartData = {
    labels: labels || [],
    datasets: [
      {
        data: data || [],
        backgroundColor: computedColors,
        borderWidth: 2,
      },
    ],
  };

  return (
    <div
      className="flex flex-col items-center justify-center"
      style={{ width, height }}
    >
      <Doughnut ref={chartRef} data={chartData} options={mergedOptions} />
    </div>
  );
}

