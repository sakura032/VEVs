import { getRunRoot } from "../artifactRegistry";

export function adaptRunIndex(rawIndex) {
  if (!rawIndex || !Array.isArray(rawIndex.runs)) {
    return [];
  }
  return rawIndex.runs
    .map((entry) => {
      if (typeof entry === "string") {
        return { run_id: entry, updated_at: null };
      }
      if (entry && typeof entry.run_id === "string") {
        return {
          run_id: entry.run_id,
          updated_at:
            typeof entry.updated_at === "string" ? entry.updated_at : null,
        };
      }
      return null;
    })
    .filter(Boolean);
}

export function adaptPoseRows(rows) {
  return rows
    .map((row, index) => ({
      rowIndex: index,
      pose_id:
        row.pose_id ??
        row.poseid ??
        row.pose ??
        row.id ??
        row.pose_index ??
        null,
      score: row.score ?? null,
      rmsd: row.rmsd ?? row.rmsd_angstrom ?? null,
      backend: row.backend ?? null,
      scientific_validity: row.scientific_validity ?? null,
      score_semantics: row.score_semantics ?? null,
      pose_file: row.pose_file ?? row.pose_path ?? null,
      raw: row,
    }))
    .filter((row) => row.pose_id !== null);
}

export function resolveFramePdbUrl(runId, frame) {
  if (!frame || !frame.pdb_file) {
    return null;
  }
  if (frame.pdb_file.startsWith("/")) {
    return frame.pdb_file;
  }
  return `${getRunRoot(runId)}/${frame.pdb_file.replace(/^\.?\//, "")}`;
}
