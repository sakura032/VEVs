import SectionCard from "../../../shared/components/common/SectionCard";
import { VESICLE_INDEX_URL } from "../constants/catalog";

export default function VesicleExplorerSidebar({
  datasets,
  selectedDataset,
  selectedDatasetId,
  setSelectedDatasetId,
  structure,
  representationMode,
  setRepresentationMode,
  displayMode,
  setDisplayMode,
  onResetCamera,
  renderPayload,
  residueOptions,
  residueFilter,
  setResidueFilter,
  leafletFilter,
  setLeafletFilter,
  clipAxis,
  setClipAxis,
  clipSide,
  setClipSide,
  clipFraction,
  setClipFraction,
  clipBounds,
  clipThresholdLabel,
  formatCount,
}) {
  return (
    <div className="panel-stack">
      <SectionCard
        title="Source"
        subtitle="Datasets are registered in frontend/visualization/vesicle/index.json and loaded directly from the frontend visualization workspace."
      >
        <div className="panel-stack">
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-dataset-select">Dataset</label>
            <select
              id="vesicle-dataset-select"
              className="control-select"
              value={selectedDatasetId ?? ""}
              onChange={(event) => setSelectedDatasetId(event.target.value)}
              disabled={datasets.length === 0}
            >
              {datasets.map((dataset) => (
                <option key={dataset.dataset_id} value={dataset.dataset_id}>
                  {dataset.label ?? dataset.dataset_id}
                </option>
              ))}
            </select>
          </div>
          <div className="mono-text vesicle-source-path">
            {selectedDataset?.structure_url ?? VESICLE_INDEX_URL}
          </div>
          {selectedDataset?.updated_at ? (
            <div className="mono-text vesicle-meta-line">
              updated_at = {selectedDataset.updated_at}
            </div>
          ) : null}
          {structure?.box ? (
            <div className="mono-text vesicle-meta-line">
              box = {structure.box.x.toFixed(2)} x {structure.box.y.toFixed(2)} x{" "}
              {structure.box.z.toFixed(2)} nm
            </div>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        title="Display"
        subtitle="Use overview for a clean shell-level read, then switch to all beads for local inspection."
      >
        <div className="panel-stack">
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-representation-mode">Representation</label>
            <select
              id="vesicle-representation-mode"
              className="control-select"
              value={representationMode}
              onChange={(event) => setRepresentationMode(event.target.value)}
            >
              <option value="overview">overview shell</option>
              <option value="all-beads">all beads</option>
            </select>
          </div>
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-display-mode">Mode</label>
            <select
              id="vesicle-display-mode"
              className="control-select"
              value={displayMode}
              onChange={(event) => setDisplayMode(event.target.value)}
            >
              <option value="points">points</option>
              <option value="spheres">local spheres</option>
            </select>
          </div>
          <button type="button" className="control-button" onClick={onResetCamera}>
            reset camera
          </button>
          {renderPayload?.note ? (
            <p className="vesicle-helper-note">{renderPayload.note}</p>
          ) : null}
        </div>
      </SectionCard>

      <SectionCard
        title="Filters"
        subtitle="Narrow by residue or leaflet before switching to local spheres."
      >
        <div className="panel-stack">
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-residue-filter">Residue</label>
            <select
              id="vesicle-residue-filter"
              className="control-select"
              value={residueFilter}
              onChange={(event) => setResidueFilter(event.target.value)}
            >
              {residueOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-leaflet-filter">Leaflet</label>
            <select
              id="vesicle-leaflet-filter"
              className="control-select"
              value={leafletFilter}
              onChange={(event) => setLeafletFilter(event.target.value)}
            >
              <option value="all">all</option>
              <option value="outer">outer leaflet</option>
              <option value="inner">inner leaflet</option>
              <option value="protein">proteins</option>
            </select>
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Clip"
        subtitle="Plane slicing happens in data space so you can inspect the interior without camera clipping artifacts."
      >
        <div className="panel-stack">
          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-clip-axis">Axis</label>
            <select
              id="vesicle-clip-axis"
              className="control-select"
              value={clipAxis}
              onChange={(event) => setClipAxis(event.target.value)}
            >
              <option value="none">disabled</option>
              <option value="x">x</option>
              <option value="y">y</option>
              <option value="z">z</option>
            </select>
          </div>

          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-clip-side">Side</label>
            <select
              id="vesicle-clip-side"
              className="control-select"
              value={clipSide}
              onChange={(event) => setClipSide(event.target.value)}
              disabled={clipAxis === "none"}
            >
              <option value="positive">positive half-space</option>
              <option value="negative">negative half-space</option>
            </select>
          </div>

          <div className="control-row control-row--stacked">
            <label htmlFor="vesicle-clip-slider">Threshold ({clipThresholdLabel})</label>
            <input
              id="vesicle-clip-slider"
              className="vesicle-slider"
              type="range"
              min="0"
              max="100"
              step="1"
              value={Math.round(clipFraction * 100)}
              onChange={(event) =>
                setClipFraction(Number.parseInt(event.target.value, 10) / 100)
              }
              disabled={clipAxis === "none" || !clipBounds}
            />
          </div>
        </div>
      </SectionCard>

      <SectionCard
        title="Composition"
        subtitle="Molecule-level counts parsed directly from the GRO residue stream."
      >
        {structure ? (
          <ul className="vesicle-stats-list">
            {structure.residueCatalog.map((entry) => (
              <li key={entry.name} className="vesicle-stats-item">
                <span className="mono-text">{entry.name}</span>
                <span>
                  {formatCount(entry.moleculeCount)} molecules / {formatCount(entry.beadCount)} beads
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="vesicle-helper-note">Load a dataset to inspect its composition summary.</p>
        )}
      </SectionCard>

      <SectionCard
        title="Leaflet Summary"
        subtitle="Leaflet classes are assigned per lipid molecule using the molecule-center radius relative to the global vesicle center."
      >
        {structure ? (
          <ul className="vesicle-stats-list">
            <li className="vesicle-stats-item">
              <span>outer</span>
              <span>{formatCount(structure.leafletCounts.molecules.outer)} molecules</span>
            </li>
            <li className="vesicle-stats-item">
              <span>inner</span>
              <span>{formatCount(structure.leafletCounts.molecules.inner)} molecules</span>
            </li>
            <li className="vesicle-stats-item">
              <span>protein</span>
              <span>{formatCount(structure.leafletCounts.molecules.protein)} molecules</span>
            </li>
          </ul>
        ) : (
          <p className="vesicle-helper-note">
            Leaflet classification becomes available after a dataset is loaded.
          </p>
        )}
      </SectionCard>
    </div>
  );
}
