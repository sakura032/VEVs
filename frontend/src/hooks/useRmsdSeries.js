import { useEffect, useState } from "react";

import { buildRunArtifacts } from "../services/artifactRegistry";
import { loadCsv } from "../services/loaders/loadCsv";

const INITIAL_STATE = {
  status: "idle",
  points: [],
  error: null,
};

function adaptRmsdRows(rows) {
  return rows
    .map((row) => ({
      frame: Number(row.frame),
      time_ps: Number(row.time_ps),
      rmsd_angstrom: Number(row.rmsd_angstrom),
    }))
    .filter(
      (row) =>
        Number.isFinite(row.frame) &&
        Number.isFinite(row.time_ps) &&
        Number.isFinite(row.rmsd_angstrom),
    );
}

export function useRmsdSeries(runId) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return undefined;
    }
    let cancelled = false;
    setState({ status: "loading", points: [], error: null });
    const artifacts = buildRunArtifacts(runId);
    loadCsv(artifacts.rmsdUrl)
      .then((rows) => {
        if (!cancelled) {
          setState({
            status: "loaded",
            points: adaptRmsdRows(rows),
            error: null,
          });
        }
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "error", points: [], error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  return state;
}
