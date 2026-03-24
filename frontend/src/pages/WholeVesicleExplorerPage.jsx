import { useEffect, useMemo, useState } from "react";
import { Color } from "three";

import Badge from "../components/common/Badge";
import EmptyState from "../components/common/EmptyState";
import LoadingState from "../components/common/LoadingState";
import SectionCard from "../components/common/SectionCard";
import VesicleExplorerCanvas from "../components/scene/VesicleExplorerCanvas";
import { loadJson } from "../services/loaders/loadJson";
import {
  loadGro,
  VESICLE_KIND_CODES,
  VESICLE_LEAFLET_CODES,
} from "../services/loaders/loadGro";

const VESICLE_INDEX_URL = "/visualization/vesicle/index.json";
const SPHERE_RENDER_LIMIT = 32000;
const RESIDUE_COLOR_HEX = {
  CD9: "#4dd0e1",
  CD81: "#7ccf63",
  CD63: "#f4b266",
  CHOL: "#f2d35c",
  POPC: "#d29cf2",
  DPSM: "#ff7ab6",
  POPE: "#66a8ff",
  POPS: "#ff6d6d",
  POP2: "#6bd5ff",
  UNK: "#b8c2cc",
};

function clampValue(value, minValue, maxValue) {
  return Math.max(minValue, Math.min(maxValue, value));
}

function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function computeDiagonal(bounds) {
  if (!bounds) {
    return 1;
  }
  const dx = bounds.maxX - bounds.minX;
  const dy = bounds.maxY - bounds.minY;
  const dz = bounds.maxZ - bounds.minZ;
  const diagonal = Math.sqrt(dx * dx + dy * dy + dz * dz);
  return Number.isFinite(diagonal) && diagonal > 0 ? diagonal : 1;
}

function buildResidueColorMap(structure) {
  const colorMap = new Map();
  structure.residueNames.forEach((residueName, residueCode) => {
    colorMap.set(residueCode, new Color(RESIDUE_COLOR_HEX[residueName] ?? RESIDUE_COLOR_HEX.UNK));
  });
  return colorMap;
}

function buildResidueFilterOptions(structure) {
  if (!structure) {
    return [];
  }
  return [
    { value: "all", label: "all residues" },
    { value: "proteins", label: "proteins only" },
    { value: "lipids", label: "lipids only" },
    ...structure.residueCatalog.map((entry) => ({
      value: entry.name,
      label: `${entry.name} (${formatCount(entry.moleculeCount)} molecules)`,
    })),
  ];
}

function resolveClipThreshold(bounds, clipAxis, clipFraction) {
  if (clipAxis === "none") {
    return null;
  }
  const axisMeta =
    clipAxis === "x"
      ? { minKey: "minX", maxKey: "maxX" }
      : clipAxis === "y"
        ? { minKey: "minY", maxKey: "maxY" }
        : { minKey: "minZ", maxKey: "maxZ" };
  const axisMin = bounds[axisMeta.minKey];
  const axisMax = bounds[axisMeta.maxKey];
  return axisMin + (axisMax - axisMin) * clipFraction;
}

function sortDatasetsByUpdatedAt(datasets) {
  return [...datasets].sort((left, right) =>
    String(right.updated_at ?? "").localeCompare(String(left.updated_at ?? "")),
  );
}

function normalizeDatasetCatalog(payload) {
  const datasets = Array.isArray(payload?.datasets) ? payload.datasets : [];
  return sortDatasetsByUpdatedAt(
    datasets.filter(
      (entry) =>
        entry &&
        typeof entry.dataset_id === "string" &&
        typeof entry.structure_url === "string" &&
        typeof entry.topology_url === "string",
    ),
  );
}

function buildFilteredRenderPayload(
  structure,
  {
    residueFilter,
    leafletFilter,
    displayMode,
    representationMode,
    clipAxis,
    clipSide,
    clipFraction,
  },
) {
  if (!structure) {
    return null;
  }

  const axisIndex =
    clipAxis === "x" ? 0 : clipAxis === "y" ? 1 : clipAxis === "z" ? 2 : -1;
  const baseBounds =
    representationMode === "overview"
      ? (structure.vesicleBounds ?? structure.bounds)
      : structure.bounds;
  const clipThreshold = resolveClipThreshold(baseBounds, clipAxis, clipFraction);
  const residueColorMap = buildResidueColorMap(structure);

  const includeEntry = ({ kindCode, leafletCode, residueName, coordinate }) => {
    if (residueFilter === "proteins" && kindCode !== VESICLE_KIND_CODES.protein) {
      return false;
    }
    if (residueFilter === "lipids" && kindCode !== VESICLE_KIND_CODES.lipid) {
      return false;
    }
    if (
      residueFilter !== "all" &&
      residueFilter !== "proteins" &&
      residueFilter !== "lipids" &&
      residueName !== residueFilter
    ) {
      return false;
    }

    if (leafletFilter === "outer" && leafletCode !== VESICLE_LEAFLET_CODES.outer) {
      return false;
    }
    if (leafletFilter === "inner" && leafletCode !== VESICLE_LEAFLET_CODES.inner) {
      return false;
    }
    if (leafletFilter === "protein" && leafletCode !== VESICLE_LEAFLET_CODES.protein) {
      return false;
    }

    if (axisIndex !== -1 && clipThreshold !== null) {
      if (clipSide === "positive" && coordinate < clipThreshold) {
        return false;
      }
      if (clipSide === "negative" && coordinate > clipThreshold) {
        return false;
      }
    }

    return true;
  };

  const forEachRenderablePoint = (visitor) => {
    if (representationMode === "overview") {
      for (let atomIndex = 0; atomIndex < structure.atomCount; atomIndex += 1) {
        const kindCode = structure.kindCodes[atomIndex];
        if (kindCode !== VESICLE_KIND_CODES.protein) {
          continue;
        }
        const residueCode = structure.residueCodes[atomIndex];
        const residueName = structure.residueNames[residueCode];
        const leafletCode = structure.leafletCodes[atomIndex];
        const offset = atomIndex * 3;
        const x = structure.positions[offset];
        const y = structure.positions[offset + 1];
        const z = structure.positions[offset + 2];
        if (
          !includeEntry({
            kindCode,
            leafletCode,
            residueName,
            coordinate: axisIndex === -1 ? 0 : structure.positions[offset + axisIndex],
          })
        ) {
          continue;
        }
        visitor({ x, y, z, residueCode });
      }

      for (let moleculeIndex = 0; moleculeIndex < structure.moleculeCount; moleculeIndex += 1) {
        const kindCode = structure.moleculeKindCodes[moleculeIndex];
        if (kindCode !== VESICLE_KIND_CODES.lipid) {
          continue;
        }
        const residueCode = structure.moleculeResidueCodes[moleculeIndex];
        const residueName = structure.residueNames[residueCode];
        const leafletCode = structure.moleculeLeafletCodes[moleculeIndex];
        const offset = moleculeIndex * 3;
        const x = structure.moleculePositions[offset];
        const y = structure.moleculePositions[offset + 1];
        const z = structure.moleculePositions[offset + 2];
        if (
          !includeEntry({
            kindCode,
            leafletCode,
            residueName,
            coordinate: axisIndex === -1 ? 0 : structure.moleculePositions[offset + axisIndex],
          })
        ) {
          continue;
        }
        visitor({ x, y, z, residueCode });
      }
      return;
    }

    for (let atomIndex = 0; atomIndex < structure.atomCount; atomIndex += 1) {
      const kindCode = structure.kindCodes[atomIndex];
      const leafletCode = structure.leafletCodes[atomIndex];
      const residueCode = structure.residueCodes[atomIndex];
      const residueName = structure.residueNames[residueCode];
      const offset = atomIndex * 3;
      const x = structure.positions[offset];
      const y = structure.positions[offset + 1];
      const z = structure.positions[offset + 2];
      if (
        !includeEntry({
          kindCode,
          leafletCode,
          residueName,
          coordinate: axisIndex === -1 ? 0 : structure.positions[offset + axisIndex],
        })
      ) {
        continue;
      }
      visitor({ x, y, z, residueCode });
    }
  };

  let includedCount = 0;
  let sumX = 0;
  let sumY = 0;
  let sumZ = 0;
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  forEachRenderablePoint(({ x, y, z }) => {
    includedCount += 1;
    sumX += x;
    sumY += y;
    sumZ += z;
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
    minZ = Math.min(minZ, z);
    maxZ = Math.max(maxZ, z);
  });

  if (includedCount === 0) {
    return {
      count: 0,
      positions: new Float32Array(0),
      colors: new Float32Array(0),
      center: null,
      bounds: null,
      effectiveDisplayMode: "points",
      pointSize: 0.2,
      sphereRadius: 0.12,
      note: "Current filters remove every bead.",
      clipThreshold,
    };
  }

  const positions = new Float32Array(includedCount * 3);
  const colors = new Float32Array(includedCount * 3);
  let writeIndex = 0;

  forEachRenderablePoint(({ x, y, z, residueCode }) => {
    const targetOffset = writeIndex * 3;
    positions[targetOffset] = x;
    positions[targetOffset + 1] = y;
    positions[targetOffset + 2] = z;

    const color = residueColorMap.get(residueCode);
    colors[targetOffset] = color.r;
    colors[targetOffset + 1] = color.g;
    colors[targetOffset + 2] = color.b;
    writeIndex += 1;
  });

  const bounds = { minX, maxX, minY, maxY, minZ, maxZ };
  const diagonal = computeDiagonal(bounds);
  const pointSize =
    representationMode === "overview"
      ? clampValue(diagonal / 320, 0.2, 0.58)
      : clampValue(diagonal / 420, 0.16, 0.42);
  const sphereRadius =
    representationMode === "overview"
      ? clampValue(diagonal / 520, 0.1, 0.26)
      : clampValue(diagonal / 620, 0.08, 0.22);

  let effectiveDisplayMode = displayMode;
  let note = null;
  if (displayMode === "spheres" && includedCount > SPHERE_RENDER_LIMIT) {
    effectiveDisplayMode = "points";
    note = `Filtered subset still has ${formatCount(includedCount)} markers, so rendering falls back to points. Narrow the filters or add clipping to enable local spheres.`;
  } else if (representationMode === "overview") {
    note =
      "Overview mode renders lipids as molecule-center markers and proteins as bead clouds so the closed vesicle shell remains legible at whole-system scale.";
  }

  return {
    count: includedCount,
    positions,
    colors,
    center: {
      x: sumX / includedCount,
      y: sumY / includedCount,
      z: sumZ / includedCount,
    },
    bounds,
    effectiveDisplayMode,
    pointSize,
    sphereRadius,
    note,
    clipThreshold,
  };
}

export default function WholeVesicleExplorerPage() {
  const [catalogState, setCatalogState] = useState({
    status: "loading",
    datasets: [],
    error: null,
  });
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [structureState, setStructureState] = useState({
    status: "idle",
    structure: null,
    error: null,
  });
  const [displayMode, setDisplayMode] = useState("points");
  const [representationMode, setRepresentationMode] = useState("overview");
  const [residueFilter, setResidueFilter] = useState("all");
  const [leafletFilter, setLeafletFilter] = useState("all");
  const [clipAxis, setClipAxis] = useState("none");
  const [clipSide, setClipSide] = useState("positive");
  const [clipFraction, setClipFraction] = useState(0.5);
  const [cameraResetToken, setCameraResetToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setCatalogState({ status: "loading", datasets: [], error: null });

    loadJson(VESICLE_INDEX_URL)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        const datasets = normalizeDatasetCatalog(payload);
        setCatalogState({ status: "loaded", datasets, error: null });
        setSelectedDatasetId((previous) => {
          if (previous && datasets.some((entry) => entry.dataset_id === previous)) {
            return previous;
          }
          return datasets[0]?.dataset_id ?? null;
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        if (error?.status === 404) {
          setCatalogState({ status: "loaded", datasets: [], error: null });
          setSelectedDatasetId(null);
          return;
        }
        setCatalogState({ status: "error", datasets: [], error });
        setSelectedDatasetId(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const datasets = catalogState.datasets;
  const selectedDataset = useMemo(
    () => datasets.find((entry) => entry.dataset_id === selectedDatasetId) ?? null,
    [datasets, selectedDatasetId],
  );

  useEffect(() => {
    if (!selectedDataset) {
      setStructureState({ status: "idle", structure: null, error: null });
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
  }, [selectedDatasetId, selectedDataset]);

  useEffect(() => {
    if (!selectedDataset) {
      return;
    }

    let cancelled = false;
    setStructureState({ status: "loading", structure: null, error: null });

    loadGro(selectedDataset.structure_url)
      .then((structure) => {
        if (cancelled) {
          return;
        }
        setStructureState({ status: "loaded", structure, error: null });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setStructureState({ status: "error", structure: null, error });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDataset]);

  const structure = structureState.structure;
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
      <EmptyState message={catalogState.error?.message || "Failed to load vesicle dataset catalog."} />
    ) : datasets.length === 0 ? (
      <EmptyState message="No vesicle dataset has been synced to frontend/visualization/vesicle/ yet." />
    ) : structureState.status === "loading" ? (
      <LoadingState message={`Loading ${selectedDataset?.dataset_id ?? "selected"} vesicle GRO...`} />
    ) : structureState.status === "error" ? (
      <EmptyState
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
      <header className="top-header">
        <div>
          <h1 className="top-header__title">Whole Vesicle Explorer</h1>
          <p className="top-header__subtitle">
            Multi-dataset GRO viewer for assembled exosome-scale coarse-grained vesicles.
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

      <main className="workspace-layout">
        <section className="workspace-area-left">
          <div className="panel-stack">
            <SectionCard
              title="Source"
              subtitle="Datasets are registered in frontend/visualization/vesicle/index.json and served through the Vite filesystem middleware."
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
              subtitle="Use overview for a clean whole-vesicle shell. Switch to all beads only when you need membrane thickness or local detail."
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
                <button
                  type="button"
                  className="control-button"
                  onClick={() => setCameraResetToken((token) => token + 1)}
                >
                  reset camera
                </button>
                {renderPayload?.note ? (
                  <p className="vesicle-helper-note">{renderPayload.note}</p>
                ) : null}
              </div>
            </SectionCard>

            <SectionCard
              title="Filters"
              subtitle="Apply residue and leaflet filters before switching to spheres."
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
              subtitle="Plane slicing is applied in data space so you can inspect the vesicle interior without camera clipping artifacts."
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
                  <label htmlFor="vesicle-clip-slider">
                    Threshold ({clipThresholdLabel})
                  </label>
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
                <p className="vesicle-helper-note">Leaflet classification becomes available after a dataset is loaded.</p>
              )}
            </SectionCard>
          </div>
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
