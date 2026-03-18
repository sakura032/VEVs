import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";

import { toPoseFileUrl } from "../../services/artifactRegistry";
import { loadPdb } from "../../services/loaders/loadPdb";
import { getActiveTrajectoryFrame } from "./TrajectoryPlayer";
import StructureStageView from "./StructureStageView";
import PoseStructureView from "./PoseStructureView";
import SelectionOverlay from "./SelectionOverlay";
import EmptyState from "../common/EmptyState";
import LoadingState from "../common/LoadingState";
import { clampValue, cssColor, mergeStructureRoles } from "./sceneRoles";

function resolveSource({
  runId,
  selectedStage,
  selectedPoseId,
  selectedFrameIndex,
  stageUrls,
  trajectoryFrames,
}) {
  if (!runId || !selectedStage) {
    return null;
  }
  if (selectedStage === "trajectory") {
    const frame = getActiveTrajectoryFrame(runId, trajectoryFrames, selectedFrameIndex);
    if (!frame) {
      return {
        kind: "trajectory",
        url: null,
        label: "trajectory frame unavailable",
        reason:
          trajectoryFrames?.reason ||
          "sampled_frames.json exists but no resolvable pdb_file entry.",
      };
    }
    return {
      kind: "trajectory",
      url: frame.pdbUrl,
      label: `trajectory frame ${frame.frame_index}`,
      frame,
    };
  }
  if (selectedPoseId !== null && selectedPoseId !== undefined) {
    const poseUrl = toPoseFileUrl(runId, selectedPoseId);
    return {
      kind: "pose",
      url: poseUrl,
      label: `pose_${String(selectedPoseId).padStart(3, "0")}.pdb`,
    };
  }
  const stageUrl = stageUrls[selectedStage];
  return {
    kind: "stage",
    url: stageUrl,
    label: selectedStage,
  };
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

function resolvePerformancePlan(structure, requestedMode) {
  if (!structure) {
    return {
      tier: "full",
      effectiveMode: requestedMode,
      allowAutoBond: true,
      note: null,
    };
  }
  const atomCount = structure?.atomCount ?? 0;
  const hasConectBonds = Boolean(structure?.bonds?.length);
  if (atomCount <= 8000) {
    return {
      tier: "full",
      effectiveMode: requestedMode,
      allowAutoBond: true,
      note:
        requestedMode === "sticks" && !hasConectBonds
          ? "sticks mode uses auto bond inference because CONECT records are absent."
          : null,
    };
  }
  if (atomCount <= 20000) {
    let note = "Large structure: reduced geometry detail enabled for interactive rendering.";
    if (requestedMode === "sticks" && !hasConectBonds) {
      note += " Auto bond inference is disabled for this size tier.";
    }
    return {
      tier: "reduced",
      effectiveMode: requestedMode,
      allowAutoBond: false,
      note,
    };
  }
  return {
    tier: "huge",
    effectiveMode: "cartoon",
    allowAutoBond: false,
    note:
      "Structure exceeds 20k atoms; mode is forced to cartoon. Local sticks for selected regions are reserved for later.",
  };
}

function resolveRenderProfile(structure, performancePlan) {
  const diagonal = computeDiagonal(structure?.bounds);
  const baseRadius = clampValue(diagonal / 230, 0.18, 0.72);
  const reduced = performancePlan.tier !== "full";
  return {
    sphereBaseRadius: baseRadius,
    stickAtomRadius: clampValue(baseRadius * 0.7, 0.1, 0.42),
    stickBondRadius: clampValue(baseRadius * 0.24, 0.045, 0.18),
    cartoonLineWidth: reduced ? 1.4 : 1.8,
    cartoonFocusSphereRadius: clampValue(baseRadius * 0.42, 0.11, 0.3),
    sphereSegments: reduced ? 10 : 14,
    cylinderSegments: reduced ? 8 : 12,
    allowAutoBond: performancePlan.allowAutoBond,
    maxAutoBonds: reduced ? 22000 : 60000,
  };
}

function CameraResetController({
  resetToken,
  structureCenter,
  structureBounds,
  controlsRef,
}) {
  const { camera } = useThree();
  useEffect(() => {
    if (!structureCenter || !structureBounds || !controlsRef.current) {
      return;
    }
    const diagonal = computeDiagonal(structureBounds);
    const radius = Math.max(diagonal * 0.5, 1.5);
    const fovRadians = (camera.fov * Math.PI) / 180;
    const distance = (radius / Math.sin(fovRadians / 2)) * 1.25;

    camera.position.set(
      structureCenter.x + distance,
      structureCenter.y + distance * 0.65,
      structureCenter.z + distance,
    );
    controlsRef.current.target.set(
      structureCenter.x,
      structureCenter.y,
      structureCenter.z,
    );
    controlsRef.current.update();
  }, [camera, controlsRef, resetToken, structureBounds, structureCenter]);
  return null;
}

export default function MolecularCanvas({
  runId,
  selectedStage,
  selectedPoseId,
  selectedFrameIndex,
  displayMode,
  visibilityFilter,
  stageUrls,
  trajectoryFrames,
  cameraResetToken,
  selectedAtomIndex,
  onAtomSelect,
  onFrameIndexChange,
  rolePayload,
  onSceneContextChange,
}) {
  const sourceDescriptor = useMemo(
    () =>
      resolveSource({
        runId,
        selectedStage,
        selectedPoseId,
        selectedFrameIndex,
        stageUrls,
        trajectoryFrames,
      }),
    [
      runId,
      selectedStage,
      selectedPoseId,
      selectedFrameIndex,
      stageUrls,
      trajectoryFrames,
    ],
  );

  const structureCacheRef = useRef(new Map());
  const orbitControlsRef = useRef(null);

  const [structureState, setStructureState] = useState({
    status: "idle",
    structure: null,
    error: null,
  });

  useEffect(() => {
    if (!sourceDescriptor?.url) {
      setStructureState({
        status: sourceDescriptor?.reason ? "error" : "idle",
        structure: null,
        error: sourceDescriptor?.reason ? new Error(sourceDescriptor.reason) : null,
      });
      return undefined;
    }

    if (structureCacheRef.current.has(sourceDescriptor.url)) {
      setStructureState({
        status: "loaded",
        structure: structureCacheRef.current.get(sourceDescriptor.url),
        error: null,
      });
      return undefined;
    }

    let cancelled = false;
    setStructureState({ status: "loading", structure: null, error: null });
    loadPdb(sourceDescriptor.url)
      .then((structure) => {
        if (cancelled) {
          return;
        }
        structureCacheRef.current.set(sourceDescriptor.url, structure);
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
  }, [sourceDescriptor]);

  const mergedStructure = useMemo(
    () => mergeStructureRoles(structureState.structure, rolePayload),
    [rolePayload, structureState.structure],
  );

  const performancePlan = useMemo(
    () => resolvePerformancePlan(mergedStructure, displayMode),
    [displayMode, mergedStructure],
  );

  const renderProfile = useMemo(
    () => resolveRenderProfile(mergedStructure, performancePlan),
    [mergedStructure, performancePlan],
  );

  const selectedAtom = useMemo(
    () =>
      mergedStructure?.atoms.find((atom) => atom.atomIndex === selectedAtomIndex) ??
      null,
    [mergedStructure, selectedAtomIndex],
  );

  useEffect(() => {
    if (!onSceneContextChange) {
      return;
    }
    onSceneContextChange({
      effectiveDisplayMode: performancePlan.effectiveMode,
      requestedDisplayMode: displayMode,
      roleCounts: mergedStructure?.roleCounts ?? null,
      roleResolutionStatus: mergedStructure?.roleResolution?.status ?? "missing",
      roleResolutionNotes: mergedStructure?.roleResolution?.notes ?? [],
      performanceNote: performancePlan.note ?? null,
      atomCount: mergedStructure?.atomCount ?? 0,
    });
  }, [displayMode, mergedStructure, onSceneContextChange, performancePlan]);

  return (
    <div className="main-scene">
      <div className="main-scene__viewport">
        <SelectionOverlay
          stage={selectedStage ?? "N/A"}
          poseLabel={
            selectedPoseId === null || selectedPoseId === undefined
              ? "none"
              : String(selectedPoseId)
          }
          frameLabel={
            selectedStage === "trajectory" ? String(selectedFrameIndex) : "N/A"
          }
          sourceLabel={sourceDescriptor?.url ?? "N/A"}
          selectedAtom={selectedAtom}
          trajectoryFrames={trajectoryFrames}
          selectedFrameIndex={selectedFrameIndex}
          onFrameIndexChange={onFrameIndexChange}
          requestedDisplayMode={displayMode}
          effectiveDisplayMode={performancePlan.effectiveMode}
          roleCounts={mergedStructure?.roleCounts}
          roleResolutionStatus={mergedStructure?.roleResolution?.status}
          roleResolutionNotes={mergedStructure?.roleResolution?.notes}
          performanceNote={performancePlan.note}
        />

        {structureState.status === "loading" ? (
          <LoadingState message="Loading structure..." />
        ) : null}
        {structureState.status === "error" ? (
          <EmptyState
            message={
              structureState.error?.message ||
              "Structure source unavailable for current selection."
            }
          />
        ) : null}

        {structureState.status === "loaded" && mergedStructure ? (
          <Canvas
            className="scene-canvas"
            camera={{ position: [36, 28, 36], near: 0.1, far: 3200 }}
          >
            <color
              attach="background"
              args={[cssColor("--bg-scene", "#f1f4f9")]}
            />
            <ambientLight intensity={0.85} />
            <directionalLight position={[24, 36, 12]} intensity={1.05} />
            <gridHelper
              args={[
                160,
                32,
                cssColor("--border-default", "#d8e0ea"),
                cssColor("--bg-subtle", "#eef2f7"),
              ]}
            />

            {sourceDescriptor?.kind === "pose" ? (
              <PoseStructureView
                structure={mergedStructure}
                effectiveDisplayMode={performancePlan.effectiveMode}
                visibilityFilter={visibilityFilter}
                selectedAtomIndex={selectedAtomIndex}
                onAtomSelect={onAtomSelect}
                renderProfile={renderProfile}
              />
            ) : (
              <StructureStageView
                structure={mergedStructure}
                effectiveDisplayMode={performancePlan.effectiveMode}
                visibilityFilter={visibilityFilter}
                selectedAtomIndex={selectedAtomIndex}
                onAtomSelect={onAtomSelect}
                renderProfile={renderProfile}
              />
            )}

            <CameraResetController
              resetToken={`${cameraResetToken}-${sourceDescriptor?.label}`}
              structureCenter={mergedStructure.center}
              structureBounds={mergedStructure.bounds}
              controlsRef={orbitControlsRef}
            />
            <OrbitControls
              ref={orbitControlsRef}
              makeDefault
              enablePan
              enableZoom
              enableRotate
            />
          </Canvas>
        ) : null}
      </div>
    </div>
  );
}
