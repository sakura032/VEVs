import { useEffect, useState } from "react";

import { buildRunArtifacts } from "../services/artifactRegistry";
import { adaptPoseRows } from "../services/adapters/visualizationBundleAdapter";
import { loadCsv } from "../services/loaders/loadCsv";

const INITIAL_STATE = {
  status: "idle",
  rows: [],
  error: null,
};

export function usePoseTable(runId) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return undefined;
    }
    let cancelled = false;
    setState({ status: "loading", rows: [], error: null });
    const artifacts = buildRunArtifacts(runId);
    loadCsv(artifacts.posesCsvUrl)
      .then((rows) => {
        if (!cancelled) {
          setState({ status: "loaded", rows: adaptPoseRows(rows), error: null });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "error", rows: [], error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return state;
}
