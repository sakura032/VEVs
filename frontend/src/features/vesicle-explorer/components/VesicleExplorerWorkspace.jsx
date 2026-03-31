import { useEffect, useMemo, useState } from "react";

import EmptyState from "../../../shared/components/common/EmptyState";
import LoadingState from "../../../shared/components/common/LoadingState";
import { buildResidueFilterOptions, buildFilteredRenderPayload, formatCount } from "../utils/renderPayload";
import { useVesicleCatalog } from "../hooks/useVesicleCatalog";
import { useVesicleStructure } from "../hooks/useVesicleStructure";
import VesicleExplorerCanvas from "./VesicleExplorerCanvas";
import VesicleExplorerHeader from "./VesicleExplorerHeader";
import VesicleExplorerSidebar from "./VesicleExplorerSidebar";

export default function VesicleExplorerWorkspace() {
  const { catalogState, datasets, selectedDataset, selectedDatasetId, setSelectedDatasetId } =
    useVesicleCatalog();
  const structureState = useVesicleStructure(selectedDataset);
  const structure = structureState.structure;

  const [displayMode, setDisplayMode] = useState("points");
  const [representationMode, setRepresentationMode] = useState("overview");
  const [residueFilter, setResidueFilter] = useState("all");
  const [leafletFilter, setLeafletFilter] = useState("all");
  const [clipAxis, setClipAxis] = useState("none");
  const [clipSide, setClipSide] = useState("positive");
  const [clipFraction, setClipFraction] = useState(0.5);
  const [cameraResetToken, setCameraResetToken] = useState(0);

  useEffect(() => {
    if (!selectedDataset) {
      return;
    }
    setDisplayMode("points");
    setRepresentationMode("overview");
    setResidueFilter("all");
    setLeafletFilter("all");
    setClipAxis("none");
    setClipSide("positive");
    setClipFraction(0.5);
    setCameraResetToken((token) => token + 1);
  }, [selectedDataset]);

  const residueOptions = useMemo(() => buildResidueFilterOptions(structure), [structure]);
  const renderPayload = useMemo(
    () =>
      buildFilteredRenderPayload(structure, {
        residueFilter,
        leafletFilter,
        displayMode,
        representationMode,
        clipAxis,
        clipSide,
        clipFraction,
      }),
    [
      clipAxis,
      clipFraction,
      clipSide,
      displayMode,
      leafletFilter,
      representationMode,
      residueFilter,
      structure,
    ],
  );

  const clipBounds =
    representationMode === "overview"
      ? (structure?.vesicleBounds ?? structure?.bounds ?? null)
      : (structure?.bounds ?? null);
  const clipThresholdLabel =
    renderPayload?.clipThreshold !== null && renderPayload?.clipThreshold !== undefined
      ? renderPayload.clipThreshold.toFixed(2)
      : "disabled";

  const pageContent =
    catalogState.status === "loading" ? (
      <LoadingState message="Loading vesicle dataset catalog..." />
    ) : catalogState.status === "error" ? (
      <EmptyState
        title="Catalog unavailable"
        message={catalogState.error?.message || "Failed to load vesicle dataset catalog."}
      />
    ) : datasets.length === 0 ? (
      <EmptyState
        title="No synced datasets"
        message="No vesicle dataset has been synced to frontend/visualization/vesicle/ yet."
      />
    ) : structureState.status === "loading" ? (
      <LoadingState
        message={`Loading ${selectedDataset?.dataset_id ?? "selected"} vesicle GRO...`}
      />
    ) : structureState.status === "error" ? (
      <EmptyState
        title="Dataset unavailable"
        message={structureState.error?.message || "Failed to load selected vesicle GRO."}
      />
    ) : (
      <VesicleExplorerCanvas
        renderPayload={renderPayload}
        cameraResetToken={cameraResetToken}
      />
    );

  return (
    <div className="app-shell">
      <VesicleExplorerHeader
        selectedDataset={selectedDataset}
        structure={structure}
        renderPayload={renderPayload}
        representationMode={representationMode}
        formatCount={formatCount}
      />

      <main className="workspace-layout">
        <section className="workspace-area-left">
          <VesicleExplorerSidebar
            datasets={datasets}
            selectedDataset={selectedDataset}
            selectedDatasetId={selectedDatasetId}
            setSelectedDatasetId={setSelectedDatasetId}
            structure={structure}
            representationMode={representationMode}
            setRepresentationMode={setRepresentationMode}
            displayMode={displayMode}
            setDisplayMode={setDisplayMode}
            onResetCamera={() => setCameraResetToken((token) => token + 1)}
            renderPayload={renderPayload}
            residueOptions={residueOptions}
            residueFilter={residueFilter}
            setResidueFilter={setResidueFilter}
            leafletFilter={leafletFilter}
            setLeafletFilter={setLeafletFilter}
            clipAxis={clipAxis}
            setClipAxis={setClipAxis}
            clipSide={clipSide}
            setClipSide={setClipSide}
            clipFraction={clipFraction}
            setClipFraction={setClipFraction}
            clipBounds={clipBounds}
            clipThresholdLabel={clipThresholdLabel}
            formatCount={formatCount}
          />
        </section>

        <section className="workspace-area-center">
          <div className="center-area">
            <div className="center-view-content">{pageContent}</div>
          </div>
        </section>
      </main>
    </div>
  );
}
