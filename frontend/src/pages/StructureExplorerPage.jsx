import { useEffect, useMemo, useState } from "react";

import TopHeader from "../components/layout/TopHeader";
import LeftControlPanel from "../components/layout/LeftControlPanel";
import RightInsightPanel from "../components/layout/RightInsightPanel";
import BottomAnalyticsPanel from "../components/layout/BottomAnalyticsPanel";
import MolecularCanvas from "../components/scene/MolecularCanvas";
import { useRunArtifacts } from "../hooks/useRunArtifacts";
import { useRunManifest } from "../hooks/useRunManifest";
import { usePoseTable } from "../hooks/usePoseTable";
import { useMetrics } from "../hooks/useMetrics";
import { useRmsdSeries } from "../hooks/useRmsdSeries";
import { useMdLogSeries } from "../hooks/useMdLogSeries";
import { useStructureRoles } from "../hooks/useStructureRoles";
import {
  buildRunArtifacts,
  STRUCTURE_STAGES,
} from "../services/artifactRegistry";

const DEFAULT_STAGE = "complex_initial";

function formatRoleCounts(roleCounts) {
  if (!roleCounts) {
    return "N/A";
  }
  return `receptor=${roleCounts.receptor ?? 0}, ligand=${roleCounts.ligand ?? 0}, water=${roleCounts.water ?? 0}, unresolved=${roleCounts.unresolved ?? 0}`;
}

function resolveFirstAvailableStage(stageAvailability) {
  const preferred = STRUCTURE_STAGES.find((stage) => stage.id === DEFAULT_STAGE);
  if (preferred && stageAvailability?.[preferred.id]) {
    return preferred.id;
  }
  const firstAvailable = STRUCTURE_STAGES.find(
    (stage) => stage.id !== "trajectory" && stageAvailability?.[stage.id],
  );
  return firstAvailable ? firstAvailable.id : DEFAULT_STAGE;
}

export default function StructureExplorerPage() {
  const [selectedRunId, setSelectedRunId] = useState("");
  const [pendingRunId, setPendingRunId] = useState("");
  const [runListRefreshKey, setRunListRefreshKey] = useState(0);
  const [selectedStage, setSelectedStage] = useState(DEFAULT_STAGE);
  const [selectedPoseId, setSelectedPoseId] = useState(null);
  const [selectedFrameIndex, setSelectedFrameIndex] = useState(0);
  const [displayMode, setDisplayMode] = useState("cartoon");
  const [visibilityFilter, setVisibilityFilter] = useState("all");
  const [selectedAtomIndex, setSelectedAtomIndex] = useState(null);
  const [cameraResetToken, setCameraResetToken] = useState(0);
  const [centerViewMode, setCenterViewMode] = useState("structure");
  const [isInsightPanelVisible, setInsightPanelVisible] = useState(false);
  const [sceneContext, setSceneContext] = useState({
    effectiveDisplayMode: "cartoon",
    requestedDisplayMode: "cartoon",
    roleCounts: null,
    roleResolutionStatus: "missing",
    roleResolutionNotes: [],
    performanceNote: null,
    atomCount: 0,
  });

  const runArtifactsState = useRunArtifacts(selectedRunId, runListRefreshKey);
  const manifestState = useRunManifest(selectedRunId);
  const poseState = usePoseTable(selectedRunId);
  const metricsState = useMetrics(selectedRunId);
  const rmsdState = useRmsdSeries(selectedRunId);
  const mdLogState = useMdLogSeries(selectedRunId);
  const structureRolesState = useStructureRoles(selectedRunId);

  const runArtifactUrls = useMemo(
    () => (selectedRunId ? buildRunArtifacts(selectedRunId) : null),
    [selectedRunId],
  );

  useEffect(() => {
    if (selectedRunId) {
      return;
    }
    const firstRun = runArtifactsState.availableRuns[0]?.run_id;
    if (firstRun) {
      setSelectedRunId(firstRun);
      setPendingRunId(firstRun);
    }
  }, [runArtifactsState.availableRuns, selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    setPendingRunId(selectedRunId);
  }, [selectedRunId]);

  useEffect(() => {
    if (!selectedRunId) {
      return;
    }
    if (!runArtifactsState.stageAvailability) {
      return;
    }
    if (runArtifactsState.stageAvailability[selectedStage]) {
      return;
    }
    setSelectedStage(resolveFirstAvailableStage(runArtifactsState.stageAvailability));
  }, [runArtifactsState.stageAvailability, selectedRunId, selectedStage]);

  useEffect(() => {
    setSceneContext({
      effectiveDisplayMode: displayMode,
      requestedDisplayMode: displayMode,
      roleCounts: null,
      roleResolutionStatus: structureRolesState.data?.resolution_status || "missing",
      roleResolutionNotes: structureRolesState.data?.resolution_notes || [],
      performanceNote: null,
      atomCount: 0,
    });
  }, [displayMode, selectedRunId, structureRolesState.data]);

  const currentObject = useMemo(() => {
    const stageLabel = selectedStage || "N/A";
    const poseLabel =
      selectedPoseId === null || selectedPoseId === undefined
        ? "none"
        : `pose_${String(selectedPoseId).padStart(3, "0")}`;
    const frameLabel =
      selectedStage === "trajectory" ? String(selectedFrameIndex) : "N/A";

    let sourceLabel = "N/A";
    if (runArtifactUrls) {
      if (selectedPoseId !== null && selectedPoseId !== undefined) {
        sourceLabel =
          runArtifactUrls.root +
          `/outputs/docking/poses/pose_${String(selectedPoseId).padStart(3, "0")}.pdb`;
      } else {
        sourceLabel = runArtifactUrls.stageUrls[selectedStage] ?? "N/A";
      }
    }
    return {
      stage: stageLabel,
      poseLabel,
      frameLabel,
      sourceLabel,
      renderModeLabel:
        sceneContext.effectiveDisplayMode ||
        sceneContext.requestedDisplayMode ||
        displayMode,
      roleCountsLabel: formatRoleCounts(sceneContext.roleCounts),
      roleResolutionStatus: sceneContext.roleResolutionStatus || "missing",
      roleResolutionNote:
        sceneContext.roleResolutionNotes?.[0] || "No role resolution note.",
      atomCountLabel: sceneContext.atomCount ? String(sceneContext.atomCount) : "N/A",
      performanceNote: sceneContext.performanceNote || "None",
      quickNotes:
        sceneContext.roleResolutionStatus === "ambiguous"
          ? "Role mapping ambiguous: receptor/ligand overlap detected; interpret as workflow visualization only."
          : manifestState.data?.scientific_validity === "placeholder_not_physical"
          ? "Placeholder backend: do not interpret this view as publication-grade conclusion."
          : "Run loaded with explicit provenance badges.",
    };
  }, [
    selectedStage,
    selectedPoseId,
    selectedFrameIndex,
    runArtifactUrls,
    manifestState.data,
    sceneContext,
    displayMode,
  ]);

  return (
    <div className="app-shell">
      <TopHeader runId={selectedRunId} manifest={manifestState.data} />

      <main className="workspace-layout">
        <section className="workspace-area-left">
          <LeftControlPanel
            availableRunIds={runArtifactsState.availableRuns}
            pendingRunId={pendingRunId}
            onPendingRunIdChange={setPendingRunId}
            onLoadRun={(runId) => {
              const cleanRunId = (runId ?? "").trim();
              if (!cleanRunId) {
                return;
              }
              setSelectedRunId(cleanRunId);
              setSelectedStage(DEFAULT_STAGE);
              setSelectedPoseId(null);
              setSelectedFrameIndex(0);
              setSelectedAtomIndex(null);
            }}
            onRefreshRuns={() =>
              setRunListRefreshKey((currentKey) => currentKey + 1)
            }
            selectedStage={selectedStage}
            onStageSelect={(stageId) => {
              setSelectedStage(stageId);
              if (stageId !== "trajectory") {
                setSelectedPoseId(null);
              }
              setSelectedAtomIndex(null);
            }}
            stageAvailability={runArtifactsState.stageAvailability}
            displayMode={displayMode}
            onDisplayModeChange={setDisplayMode}
            visibilityFilter={visibilityFilter}
            onVisibilityFilterChange={setVisibilityFilter}
            onResetCamera={() => setCameraResetToken((token) => token + 1)}
          />
        </section>

        <section className="workspace-area-center">
          <div className="center-area">
            <div className="center-view-toolbar">
              <div className="center-view-toolbar-actions">
                <button
                  type="button"
                  className="control-button center-view-toggle"
                  onClick={() =>
                    setCenterViewMode((previousMode) =>
                      previousMode === "structure" ? "analytics" : "structure",
                    )
                  }
                >
                  {centerViewMode === "structure"
                    ? "Switch to Analytics Panel"
                    : "Switch to 3D View"}
                </button>
                <button
                  type="button"
                  className="control-button center-view-toggle"
                  onClick={() => setInsightPanelVisible((isVisible) => !isVisible)}
                >
                  {isInsightPanelVisible
                    ? "Hide Insight Panel"
                    : "Show Insight Panel"}
                </button>
              </div>
            </div>

            <div
              className={`center-view-content center-view-content--${centerViewMode}`}
            >
              {centerViewMode === "structure" ? (
                <MolecularCanvas
                  runId={selectedRunId}
                  selectedStage={selectedStage}
                  selectedPoseId={selectedPoseId}
                  selectedFrameIndex={selectedFrameIndex}
                  displayMode={displayMode}
                  visibilityFilter={visibilityFilter}
                  stageUrls={runArtifactUrls?.stageUrls ?? {}}
                  trajectoryFrames={runArtifactsState.trajectoryFrames}
                  cameraResetToken={cameraResetToken}
                  selectedAtomIndex={selectedAtomIndex}
                  onAtomSelect={(atom) => setSelectedAtomIndex(atom.atomIndex)}
                  onFrameIndexChange={setSelectedFrameIndex}
                  rolePayload={structureRolesState.data}
                  onSceneContextChange={setSceneContext}
                />
              ) : (
                <BottomAnalyticsPanel
                  rmsdState={rmsdState}
                  mdLogState={mdLogState}
                  onRmsdPointSelect={(point) => {
                    if (!runArtifactsState.trajectoryFrames?.available) {
                      return;
                    }
                    setSelectedFrameIndex(Number(point.frame));
                    setSelectedStage("trajectory");
                    setSelectedPoseId(null);
                    setSelectedAtomIndex(null);
                    setCenterViewMode("structure");
                  }}
                />
              )}
            </div>
          </div>
        </section>

        <section
          className={`workspace-area-right ${
            isInsightPanelVisible ? "is-open" : "is-closed"
          }`}
        >
          <div className="workspace-area-right__toolbar">
            <button
              type="button"
              className="control-button center-view-toggle"
              onClick={() => setInsightPanelVisible(false)}
              aria-label="Close insight panel"
            >
              Close Insight Panel
            </button>
          </div>
          <RightInsightPanel
            currentObject={currentObject}
            poseState={poseState}
            selectedPoseId={selectedPoseId}
            onPoseSelect={(poseId) => {
              setSelectedPoseId(Number(poseId));
              setSelectedStage("complex_initial");
              setSelectedAtomIndex(null);
            }}
            metricsState={metricsState}
            manifest={manifestState.data}
            preprocessReport={runArtifactsState.preprocessReport}
            mdPdbfixerReport={runArtifactsState.mdPdbfixerReport}
            routeSummary={runArtifactsState.routeSummary}
          />
        </section>
      </main>
    </div>
  );
}
