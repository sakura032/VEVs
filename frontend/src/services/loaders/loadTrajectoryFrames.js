import { loadJson } from "./loadJson";

function normalizeFrames(rawPayload) {
  if (!rawPayload || typeof rawPayload !== "object") {
    return { available: false, reason: "Invalid sampled frame payload.", frames: [] };
  }
  const rawFrames = Array.isArray(rawPayload.frames) ? rawPayload.frames : [];
  const frames = rawFrames.map((frame, index) => ({
    frame_index:
      Number.isFinite(frame.frame_index) || Number.isInteger(frame.frame_index)
        ? Number(frame.frame_index)
        : index,
    time_ps: Number.isFinite(frame.time_ps) ? Number(frame.time_ps) : null,
    rmsd_angstrom: Number.isFinite(frame.rmsd_angstrom)
      ? Number(frame.rmsd_angstrom)
      : null,
    pdb_file:
      typeof frame.pdb_file === "string" && frame.pdb_file.length > 0
        ? frame.pdb_file
        : null,
  }));
  const available = Boolean(rawPayload.available) && frames.length > 0;
  return {
    available,
    reason: rawPayload.reason ?? null,
    frames,
  };
}

export async function loadTrajectoryFrames(url) {
  const payload = await loadJson(url);
  return normalizeFrames(payload);
}
