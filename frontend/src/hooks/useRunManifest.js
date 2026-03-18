import { useEffect, useState } from "react";

import { buildRunArtifacts } from "../services/artifactRegistry";
import { loadJson } from "../services/loaders/loadJson";

const INITIAL_STATE = {
  status: "idle",
  data: null,
  error: null,
};

export function useRunManifest(runId) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return undefined;
    }
    let cancelled = false;
    setState({ status: "loading", data: null, error: null });
    const artifacts = buildRunArtifacts(runId);
    loadJson(artifacts.runManifestUrl)
      .then((payload) => {
        if (!cancelled) {
          setState({ status: "loaded", data: payload, error: null });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "error", data: null, error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return state;
}
