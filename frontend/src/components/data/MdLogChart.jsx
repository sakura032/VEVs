import { useEffect, useMemo, useState } from "react";

import EmptyState from "../common/EmptyState";
import LoadingState from "../common/LoadingState";

const VIEWBOX_WIDTH = 900;
const VIEWBOX_HEIGHT = 320;
const PADDING = 32;

const METRIC_LABELS = {
  Temperature_K: "Temperature (K)",
  Potential_Energy_kJ_mole: "Potential Energy (kJ/mol)",
  Density_g_mL: "Density (g/mL)",
  "Box_Volume_nm^3": "Box Volume (nm^3)",
};

function mapSeries(rows, metricKey) {
  const validRows = rows.filter((row) => Number.isFinite(row[metricKey]));
  if (validRows.length === 0) {
    return [];
  }
  const xMin = Math.min(...validRows.map((row) => row.time_ps));
  const xMax = Math.max(...validRows.map((row) => row.time_ps));
  const yMin = Math.min(...validRows.map((row) => row[metricKey]));
  const yMax = Math.max(...validRows.map((row) => row[metricKey]));
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;
  return validRows.map((row) => ({
    ...row,
    value: row[metricKey],
    x:
      PADDING +
      ((row.time_ps - xMin) / xSpan) * (VIEWBOX_WIDTH - PADDING * 2),
    y:
      VIEWBOX_HEIGHT -
      PADDING -
      ((row[metricKey] - yMin) / ySpan) * (VIEWBOX_HEIGHT - PADDING * 2),
  }));
}

export default function MdLogChart({ mdLogState }) {
  const [metricKey, setMetricKey] = useState(null);

  useEffect(() => {
    setMetricKey(mdLogState.defaultMetric);
  }, [mdLogState.defaultMetric]);

  const chartPoints = useMemo(() => {
    if (!metricKey || mdLogState.rows.length === 0) {
      return [];
    }
    return mapSeries(mdLogState.rows, metricKey);
  }, [mdLogState.rows, metricKey]);

  if (mdLogState.status === "loading") {
    return <LoadingState message="Loading MD log..." />;
  }
  if (mdLogState.status === "error") {
    return <EmptyState message="md_log.csv missing or unreadable." />;
  }
  if (mdLogState.status !== "loaded" || mdLogState.rows.length === 0) {
    return <EmptyState message="No MD log series available." />;
  }
  if (!metricKey || chartPoints.length === 0) {
    return <EmptyState message="Selected MD metric has no numeric series." />;
  }

  const polylinePoints = chartPoints.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <div className="analytics-series-view">
      <div className="control-row">
        <label htmlFor="md-log-metric">Metric</label>
        <select
          id="md-log-metric"
          className="control-select"
          value={metricKey}
          onChange={(event) => setMetricKey(event.target.value)}
        >
          {mdLogState.availableMetrics.map((metric) => (
            <option key={metric} value={metric}>
              {METRIC_LABELS[metric] ?? metric}
            </option>
          ))}
        </select>
      </div>
      <div className="analytics-series-view__chart-shell">
        <svg
          className="line-chart"
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
        >
          <line
            x1={PADDING}
            y1={VIEWBOX_HEIGHT - PADDING}
            x2={VIEWBOX_WIDTH - PADDING}
            y2={VIEWBOX_HEIGHT - PADDING}
            stroke="var(--border-default)"
            strokeWidth="1"
          />
          <line
            x1={PADDING}
            y1={PADDING}
            x2={PADDING}
            y2={VIEWBOX_HEIGHT - PADDING}
            stroke="var(--border-default)"
            strokeWidth="1"
          />
          <polyline
            fill="none"
            stroke="var(--accent-selected)"
            strokeWidth="2"
            points={polylinePoints}
          />
          {chartPoints.map((point) => (
            <circle
              key={`md-log-${point.step}`}
              cx={point.x}
              cy={point.y}
              r="3"
              fill="var(--accent-cyan)"
            >
              <title>
                step={point.step}, time_ps={point.time_ps.toFixed(3)}, value=
                {point.value.toFixed(4)}
              </title>
            </circle>
          ))}
        </svg>
      </div>
      <p className="line-chart__meta">
        MD log sourced from <span className="mono-text">work/md/md_log.csv</span>.
      </p>
    </div>
  );
}
