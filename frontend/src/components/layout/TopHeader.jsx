import Badge from "../common/Badge";

function resolveValidityVariant(validity) {
  if (!validity) {
    return "warning";
  }
  if (String(validity).includes("placeholder")) {
    return "warning";
  }
  return "success";
}

export default function TopHeader({ runId, manifest }) {
  return (
    <header className="top-header">
      <div>
        <h1 className="top-header__title">VEVs Route A Structure Explorer</h1>
        <p className="top-header__subtitle">
          Receptor-Ligand Complex Visualization
        </p>
      </div>
      <div className="top-header__badges">
        <Badge label="run_id" value={runId || "Not loaded"} variant="info" />
        <Badge
          label="backend"
          value={manifest?.backend || "unknown"}
          variant={manifest?.backend === "placeholder" ? "warning" : "success"}
        />
        <Badge
          label="scientific_validity"
          value={manifest?.scientific_validity || "unknown"}
          variant={resolveValidityVariant(manifest?.scientific_validity)}
        />
        <Badge
          label="analysis_mode"
          value={manifest?.analysis_mode || "unknown"}
          variant="info"
        />
        <Badge
          label="multi-run"
          value="Reserved"
          variant="reserved"
        />
      </div>
    </header>
  );
}
