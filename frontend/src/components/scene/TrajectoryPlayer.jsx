import { resolveFramePdbUrl } from "../../services/adapters/visualizationBundleAdapter";

export function getActiveTrajectoryFrame(runId, trajectoryFrames, selectedFrameIndex) {
  if (!trajectoryFrames?.available || !Array.isArray(trajectoryFrames.frames)) {
    return null;
  }
  const frame = trajectoryFrames.frames.find(
    (entry) => Number(entry.frame_index) === Number(selectedFrameIndex),
  );
  if (!frame) {
    return null;
  }
  const pdbUrl = resolveFramePdbUrl(runId, frame);
  if (!pdbUrl) {
    return null;
  }
  return {
    ...frame,
    pdbUrl,
  };
}

export default function TrajectoryPlayer({
  trajectoryFrames,
  selectedFrameIndex,
  onFrameIndexChange,
}) {
  if (!trajectoryFrames?.available) {
    return (
      <div className="empty-state">
        trajectory disabled:{" "}
        {trajectoryFrames?.reason || "No sampled_frames.json bundle available."}
      </div>
    );
  }

  const frameIndices = trajectoryFrames.frames.map((frame) => frame.frame_index);
  const firstFrame = frameIndices[0];
  const lastFrame = frameIndices[frameIndices.length - 1];
  const nextFrame = Math.min(lastFrame, Number(selectedFrameIndex) + 1);
  const previousFrame = Math.max(firstFrame, Number(selectedFrameIndex) - 1);

  return (
    <div className="control-row">
      <button
        type="button"
        className="control-button"
        onClick={() => onFrameIndexChange(previousFrame)}
      >
        prev
      </button>
      <span className="mono-text">
        frame {selectedFrameIndex} / {lastFrame}
      </span>
      <button
        type="button"
        className="control-button"
        onClick={() => onFrameIndexChange(nextFrame)}
      >
        next
      </button>
    </div>
  );
}
