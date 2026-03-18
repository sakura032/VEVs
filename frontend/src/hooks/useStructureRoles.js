import { useEffect, useState } from "react";

import { buildRunArtifacts } from "../services/artifactRegistry";
import { loadJson } from "../services/loaders/loadJson";

const VALID_STATUSES = new Set(["resolved", "ambiguous", "missing"]);
const VALID_ROLES = new Set(["receptor", "ligand", "water", "unresolved"]);

function buildMissingPayload(runId, reason) {
  return {
    run_id: runId ?? null,
    resolution_status: "missing",
    resolution_notes: [
      reason ||
        "structure_roles.json missing; fallback HETATM/HOH role inference is active.",
    ],
    source: {
      receptor_file: "work/preprocessed/receptor_clean.pdb",
      ligand_file: "work/preprocessed/ligand_prepared.pdb",
      method: "fallback_inference_only",
    },
    atom_roles: {},
  };
}

function normalizePayload(runId, payload) {
  if (!payload || typeof payload !== "object") {
    return buildMissingPayload(runId, "Invalid structure_roles payload.");
  }
  const run_id =
    typeof payload.run_id === "string" && payload.run_id.trim().length > 0
      ? payload.run_id
      : runId ?? null;
  const resolution_status = VALID_STATUSES.has(payload.resolution_status)
    ? payload.resolution_status
    : "missing";
  const resolution_notes = Array.isArray(payload.resolution_notes)
    ? payload.resolution_notes.filter((item) => typeof item === "string")
    : [];
  const source =
    payload.source && typeof payload.source === "object" ? payload.source : {};
  const atom_roles = {};
  if (payload.atom_roles && typeof payload.atom_roles === "object") {
    Object.entries(payload.atom_roles).forEach(([atomKey, role]) => {
      if (typeof atomKey !== "string") {
        return;
      }
      if (!VALID_ROLES.has(role)) {
        return;
      }
      atom_roles[atomKey] = role;
    });
  }
  return {
    run_id,
    resolution_status,
    resolution_notes:
      resolution_notes.length > 0
        ? resolution_notes
        : ["structure_roles payload did not include resolution notes."],
    source: {
      receptor_file:
        typeof source.receptor_file === "string"
          ? source.receptor_file
          : "work/preprocessed/receptor_clean.pdb",
      ligand_file:
        typeof source.ligand_file === "string"
          ? source.ligand_file
          : "work/preprocessed/ligand_prepared.pdb",
      method:
        typeof source.method === "string" ? source.method : "unknown_method",
    },
    atom_roles,
  };
}

const INITIAL_STATE = {
  status: "idle",
  data: buildMissingPayload(null, "Run not selected."),
  error: null,
};

export function useStructureRoles(runId) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!runId) {
      setState({
        status: "idle",
        data: buildMissingPayload(null, "Run not selected."),
        error: null,
      });
      return undefined;
    }
    let cancelled = false;
    setState({
      status: "loading",
      data: buildMissingPayload(runId, "Loading structure role mapping..."),
      error: null,
    });
    const artifacts = buildRunArtifacts(runId);
    loadJson(artifacts.structureRolesUrl)
      .then((payload) => {
        if (!cancelled) {
          setState({
            status: "loaded",
            data: normalizePayload(runId, payload),
            error: null,
          });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({
            status: "loaded",
            data: buildMissingPayload(
              runId,
              "structure_roles.json not found; fallback role inference is active.",
            ),
            error,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return state;
}

