export const getDonutChartProps = ({
  data = [],
  labels = [],
  colors = [
    "#3d60b0ff", "#e8a200ff", "#EF476F", "#55c2e0", "#64c678", "#b376f7", "#fbbe5b", "#fa658c"
  ],
  hrefs = []
}) => {
  // Ensure colors and hrefs match label count
  const chartColors = Array(labels.length)
    .fill(null)
    .map((_, i) => colors[i % colors.length]);
  const chartHrefs = hrefs.length === labels.length
    ? hrefs 
    : Array(labels.length).fill("");

  return {
    data,
    labels,
    colors: chartColors,
    hrefs: chartHrefs
  };
};