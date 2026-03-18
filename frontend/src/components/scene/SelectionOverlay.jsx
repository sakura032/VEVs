import TrajectoryPlayer from "./TrajectoryPlayer";

export default function SelectionOverlay({
  stage,
  poseLabel,
  frameLabel,
  sourceLabel,
  selectedAtom,
  trajectoryFrames,
  selectedFrameIndex,
  onFrameIndexChange,
  requestedDisplayMode,
  effectiveDisplayMode,
  roleCounts,
  roleResolutionStatus,
  roleResolutionNotes,
  performanceNote,
}) {
  const roleCountText = roleCounts
    ? `receptor=${roleCounts.receptor ?? 0}, ligand=${roleCounts.ligand ?? 0}, water=${roleCounts.water ?? 0}, unresolved=${roleCounts.unresolved ?? 0}`
    : "N/A";

  return (
    <div className="scene-overlay">
      {roleResolutionStatus === "ambiguous" ? (
        <div className="scene-overlay__warning">
          Current data cannot reliably separate receptor and ligand; this view is
          for workflow validation only, not physical evidence.
        </div>
      ) : null}
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">current stage</span>
        <span className="mono-text">{stage}</span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">current pose</span>
        <span className="mono-text">{poseLabel}</span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">current frame</span>
        <span className="mono-text">{frameLabel}</span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">file source</span>
        <span className="mono-text">{sourceLabel}</span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">render mode</span>
        <span className="mono-text">
          {effectiveDisplayMode}
          {requestedDisplayMode !== effectiveDisplayMode
            ? ` (requested: ${requestedDisplayMode})`
            : ""}
        </span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">role counts</span>
        <span className="mono-text">{roleCountText}</span>
      </div>
      <div className="scene-overlay__row">
        <span className="scene-overlay__label">role resolution</span>
        <span className="mono-text">{roleResolutionStatus || "missing"}</span>
      </div>
      {Array.isArray(roleResolutionNotes) && roleResolutionNotes.length > 0 ? (
        <div className="scene-overlay__legend-note">{roleResolutionNotes[0]}</div>
      ) : null}
      {performanceNote ? (
        <div className="scene-overlay__legend-note">{performanceNote}</div>
      ) : null}
      <div className="scene-overlay__legend">
        <div className="scene-overlay__legend-title">legend</div>
        <div className="scene-overlay__legend-grid">
          <span className="scene-overlay__swatch scene-overlay__swatch--receptor" />
          <span>receptor</span>
          <span className="scene-overlay__swatch scene-overlay__swatch--ligand" />
          <span>ligand</span>
          <span className="scene-overlay__swatch scene-overlay__swatch--water" />
          <span>water</span>
          <span className="scene-overlay__swatch scene-overlay__swatch--unresolved" />
          <span>unresolved</span>
        </div>
        <div className="scene-overlay__legend-note">
          mode shape: cartoon=chain trace, sticks=atom+bond cylinders, spheres=vdw
          spheres
        </div>
      </div>
      {selectedAtom ? (
        <div className="scene-overlay__selection">
          <div className="scene-overlay__row">
            <span className="scene-overlay__label">selection</span>
            <span className="mono-text">
              {selectedAtom.atomName}-{selectedAtom.residue}
              {selectedAtom.residueId}
            </span>
          </div>
          <div className="scene-overlay__row">
            <span className="scene-overlay__label">serial</span>
            <span className="mono-text">{selectedAtom.serial}</span>
          </div>
          <div className="scene-overlay__row">
            <span className="scene-overlay__label">chain</span>
            <span className="mono-text">{selectedAtom.chainId || "_"}</span>
          </div>
          <div className="scene-overlay__row">
            <span className="scene-overlay__label">role</span>
            <span className="mono-text">
              {selectedAtom.role} ({selectedAtom.roleConfidence})
            </span>
          </div>
        </div>
      ) : null}
      {stage === "trajectory" ? (
        <TrajectoryPlayer
          trajectoryFrames={trajectoryFrames}
          selectedFrameIndex={selectedFrameIndex}
          onFrameIndexChange={onFrameIndexChange}
        />
      ) : null}
    </div>
  );
}

