"use client";
import Card from "../../components/Card";
import DonutChart from "../../components/DonutChart";
import { getDonutChartProps } from "./helper/format_donut_props";
import { getSummaryCards } from "./helper/format_summary_cards";
import { useEffect, useState } from "react";
import { useFilters } from "../../components/FilterProvider";
import { getOverviewData } from "../../controller/dataFetcher";
import LoadingSpinner from "../../components/LoadingSpinner";

export default function OverviewPage() {
  const { filters } = useFilters();
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getOverviewData(filters)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => {
        setData(null);
        setLoading(false);
      });
  }, [filters]);

  if (loading)
    return (
      <div className="h-full flex items-center justify-center text-gray-500 font-bold text-xl">
        <LoadingSpinner />
      </div>
    );

  if (!data)
    return (
      <div className="text-red-500 font-bold text-xl">
        Failed to fetch overview data.
      </div>
    );

  const { summary } = data;

  const donutStatusProps = getDonutChartProps({
    data: [
      summary.active_certificates,
      summary.expiring_soon,
      summary.expired_certificates,
    ],
    labels: ["Active Certificates", "Expiring Soon", "Expired Certificates"],
  });

  const types = summary.signature_algorithm_counts || {};
  const donutTypeProps = getDonutChartProps({
    data: Object.values(types),
    labels: Object.keys(types),
  });

  return (
    <div className="h-full w-full flex justify-between flex-col py-4 gap-4">

      {/* SUMMARY CARDS (FULLY RESPONSIVE GRID) */}
      <div className="
        w-full px-2
        grid gap-4
        grid-cols-1
        sm:grid-cols-1
        md:grid-cols-2
        lg:grid-cols-3
      ">
        {getSummaryCards(summary)}
      </div>

      {/* DONUT CHART CARDS (RESPONSIVE) */}
      <div className="
        w-full px-2
        grid gap-6
        grid-cols-1
        sm:grid-cols-1
        md:grid-cols-1
        lg:grid-cols-2
      ">
        <Card
          title="Certificate Status Distribution"
          value={<DonutChart {...donutStatusProps} />}
          className="h-full flex flex-col items-center justify-center"
        />

        <Card
          title="Certificate Type Distribution"
          value={<DonutChart {...donutTypeProps} />}
          className="h-full flex flex-col items-center justify-center"
        />
      </div>

    </div>
  );
}
