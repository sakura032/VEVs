import Badge from "../../../shared/components/common/Badge";

export default function VesicleExplorerHeader({
  selectedDataset,
  structure,
  renderPayload,
  representationMode,
  formatCount,
}) {
  return (
    <header className="top-header">
      <div>
        <h1 className="top-header__title">Whole Vesicle Explorer</h1>
        <p className="top-header__subtitle">
          Vesicle-scale GRO viewer for assembled coarse-grained datasets synced into the frontend
          workspace.
        </p>
      </div>
      <div className="top-header__badges">
        <Badge
          label="dataset"
          value={selectedDataset?.dataset_id ?? "loading"}
          variant="info"
        />
        <Badge
          label="beads"
          value={structure ? formatCount(structure.atomCount) : "loading"}
          variant="success"
        />
        <Badge
          label={representationMode === "overview" ? "markers" : "visible"}
          value={renderPayload ? formatCount(renderPayload.count) : "N/A"}
          variant="warning"
        />
      </div>
    </header>
  );
}
