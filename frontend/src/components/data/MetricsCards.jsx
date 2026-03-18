import SectionCard from "../common/SectionCard";
import EmptyState from "../common/EmptyState";
import LoadingState from "../common/LoadingState";

const METRIC_KEYS = [
  ["n_frames", "n_frames"],
  ["rmsd_mean_angstrom", "RMSD mean (A)"],
  ["rmsd_max_angstrom", "RMSD max (A)"],
  ["rmsd_min_angstrom", "RMSD min (A)"],
  ["analysis_mode", "analysis_mode"],
  ["metrics_semantics", "metrics_semantics"],
];

function renderMetricValue(value) {
  if (Number.isFinite(Number(value))) {
    return Number(value).toFixed(4);
  }
  if (value === null || value === undefined || value === "") {
    return "N/A";
  }
  return String(value);
}

export default function MetricsCards({ metricsState, embedded = false }) {
  const content = (
    <>
      {metricsState.status === "loading" ? (
        <LoadingState message="Loading metrics..." />
      ) : null}
      {metricsState.status === "error" ? (
        <EmptyState message="Metrics file not available for this run." />
      ) : null}
      {metricsState.status === "loaded" && metricsState.data ? (
        <div className="metrics-grid">
          {METRIC_KEYS.map(([key, label]) => (
            <article className="metric-card" key={key}>
              <div className="metric-card__label">{label}</div>
              <div className="metric-card__value">
                {renderMetricValue(metricsState.data[key])}
              </div>
            </article>
          ))}
        </div>
      ) : null}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <SectionCard title="Metrics Cards" subtitle="analysis/binding/metrics.json">
      {content}
    </SectionCard>
  );
}
