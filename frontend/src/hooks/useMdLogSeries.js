import { useEffect, useMemo, useState } from "react";

import { buildRunArtifacts } from "../services/artifactRegistry";
import { loadCsv } from "../services/loaders/loadCsv";

const INITIAL_STATE = {
  status: "idle",
  rows: [],
  availableMetrics: [],
  error: null,
};

const CANDIDATE_METRICS = [
  "Temperature_K",
  "Potential_Energy_kJ_mole",
  "Density_g_mL",
  "Box_Volume_nm^3",
];

function adaptRows(rows) {
  return rows
    .map((row) => ({
      step: Number(row.Step ?? row.step),
      time_ps: Number(row.Time_ps ?? row.time_ps),
      Temperature_K: Number(row.Temperature_K),
      Potential_Energy_kJ_mole: Number(row.Potential_Energy_kJ_mole),
      Density_g_mL: Number(row.Density_g_mL),
      "Box_Volume_nm^3": Number(row["Box_Volume_nm^3"]),
    }))
    .filter((row) => Number.isFinite(row.step) && Number.isFinite(row.time_ps));
}

function resolveAvailableMetrics(rows) {
  if (rows.length === 0) {
    return [];
  }
  return CANDIDATE_METRICS.filter((metric) =>
    rows.some((row) => Number.isFinite(row[metric])),
  );
}

export function useMdLogSeries(runId) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    if (!runId) {
      setState(INITIAL_STATE);
      return undefined;
    }
    let cancelled = false;
    setState({ status: "loading", rows: [], availableMetrics: [], error: null });
    const artifacts = buildRunArtifacts(runId);
    loadCsv(artifacts.mdLogUrl)
      .then((rows) => {
        if (cancelled) {
          return;
        }
        const normalizedRows = adaptRows(rows);
        setState({
          status: "loaded",
          rows: normalizedRows,
          availableMetrics: resolveAvailableMetrics(normalizedRows),
          error: null,
        });
      })
      .catch((error) => {
        if (!cancelled) {
          setState({ status: "error", rows: [], availableMetrics: [], error });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [runId]);

  const defaultMetric = useMemo(
    () => state.availableMetrics[0] ?? null,
    [state.availableMetrics],
  );

  return {
    ...state,
    defaultMetric,
  };
}
