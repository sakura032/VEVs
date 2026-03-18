import EmptyState from "../common/EmptyState";
import LoadingState from "../common/LoadingState";

const VIEWBOX_WIDTH = 900;
const VIEWBOX_HEIGHT = 320;
const PADDING = 32;

function normalizeSeries(points) {
  const xMin = Math.min(...points.map((point) => point.time_ps));
  const xMax = Math.max(...points.map((point) => point.time_ps));
  const yMin = Math.min(...points.map((point) => point.rmsd_angstrom));
  const yMax = Math.max(...points.map((point) => point.rmsd_angstrom));
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;
  return points.map((point) => ({
    ...point,
    x:
      PADDING +
      ((point.time_ps - xMin) / xSpan) * (VIEWBOX_WIDTH - PADDING * 2),
    y:
      VIEWBOX_HEIGHT -
      PADDING -
      ((point.rmsd_angstrom - yMin) / ySpan) * (VIEWBOX_HEIGHT - PADDING * 2),
  }));
}

export default function RmsdChart({ rmsdState, onPointSelect }) {
  if (rmsdState.status === "loading") {
    return <LoadingState message="Loading RMSD..." />;
  }
  if (rmsdState.status === "error") {
    return <EmptyState message="RMSD file missing or unreadable." />;
  }
  if (rmsdState.status !== "loaded" || rmsdState.points.length === 0) {
    return <EmptyState message="No RMSD points available." />;
  }

  const points = normalizeSeries(rmsdState.points);
  const polylinePoints = points.map((point) => `${point.x},${point.y}`).join(" ");
  return (
    <div className="analytics-series-view">
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
            stroke="var(--accent-blue)"
            strokeWidth="2"
            points={polylinePoints}
          />
          {points.map((point) => (
            <circle
              key={`rmsd-${point.frame}`}
              cx={point.x}
              cy={point.y}
              r="3.5"
              fill="var(--accent-cyan)"
              onClick={() => onPointSelect?.(point)}
            >
              <title>
                frame={point.frame}, time_ps={point.time_ps.toFixed(3)},
                rmsd={point.rmsd_angstrom.toFixed(4)}
              </title>
            </circle>
          ))}
        </svg>
      </div>
      <p className="line-chart__meta">
        RMSD sourced from <span className="mono-text">analysis/binding/rmsd.csv</span>.
      </p>
    </div>
  );
}
