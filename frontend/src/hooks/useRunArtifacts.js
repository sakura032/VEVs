import { useEffect, useState } from "react";

import {
  buildRunArtifacts,
  getRunIndexUrl,
  STRUCTURE_STAGES,
} from "../services/artifactRegistry";
import { adaptRunIndex } from "../services/adapters/visualizationBundleAdapter";
import { loadJson } from "../services/loaders/loadJson";
import { loadTrajectoryFrames } from "../services/loaders/loadTrajectoryFrames";

const EMPTY_TRAJECTORY = {
  available: false,
  reason: "No sampled trajectory frames available.",
  frames: [],
};

const INITIAL_STATE = {
  status: "idle",
  availableRuns: [],
  stageAvailability: {},
  preprocessReport: null,
  mdPdbfixerReport: null,
  routeSummary: null,
  trajectoryFrames: EMPTY_TRAJECTORY,
  error: null,
};

async function checkUrlExists(url) {
  const headResponse = await fetch(url, { method: "HEAD" });
  if (headResponse.ok) {
    return true;
  }
  if (headResponse.status === 405) {
    const getResponse = await fetch(url);
    return getResponse.ok;
  }
  return false;
}

export function useRunArtifacts(runId, refreshKey = 0) {
  const [state, setState] = useState(INITIAL_STATE);

  useEffect(() => {
    let cancelled = false;

    const loadAvailableRuns = async () => {
      try {
        const runIndexPayload = await loadJson(getRunIndexUrl());
        return adaptRunIndex(runIndexPayload);
      } catch {
        return [];
      }
    };

    const loadRunScopedArtifacts = async () => {
      if (!runId) {
        return {
          stageAvailability: {},
          preprocessReport: null,
          mdPdbfixerReport: null,
          routeSummary: null,
          trajectoryFrames: EMPTY_TRAJECTORY,
        };
      }
      const artifacts = buildRunArtifacts(runId);
      const stageChecks = STRUCTURE_STAGES.map(async (stage) => {
        try {
          const exists = await checkUrlExists(artifacts.stageUrls[stage.id]);
          return [stage.id, exists];
        } catch {
          return [stage.id, false];
        }
      });
      const stageAvailabilityEntries = await Promise.all(stageChecks);
      const stageAvailability = Object.fromEntries(stageAvailabilityEntries);

      const [preprocessResult, mdFixerResult, reportResult, trajectoryResult] =
        await Promise.allSettled([
          loadJson(artifacts.preprocessReportUrl),
          loadJson(artifacts.mdPdbfixerReportUrl),
          fetch(artifacts.routeSummaryUrl).then((response) =>
            response.ok ? response.text() : null,
          ),
          loadTrajectoryFrames(artifacts.sampledFramesUrl),
        ]);

      const trajectoryFrames =
        trajectoryResult.status === "fulfilled"
          ? trajectoryResult.value
          : EMPTY_TRAJECTORY;

      return {
        stageAvailability: {
          ...stageAvailability,
          trajectory:
            stageAvailability.trajectory &&
            Boolean(trajectoryFrames.available) &&
            trajectoryFrames.frames.length > 0,
        },
        preprocessReport:
          preprocessResult.status === "fulfilled"
            ? preprocessResult.value
            : null,
        mdPdbfixerReport:
          mdFixerResult.status === "fulfilled" ? mdFixerResult.value : null,
        routeSummary: reportResult.status === "fulfilled" ? reportResult.value : null,
        trajectoryFrames,
      };
    };

    setState((previousState) => ({
      ...previousState,
      status: "loading",
      error: null,
    }));

    Promise.all([loadAvailableRuns(), loadRunScopedArtifacts()])
      .then(([availableRuns, runScopedArtifacts]) => {
        if (cancelled) {
          return;
        }
        setState({
          status: "loaded",
          availableRuns,
          ...runScopedArtifacts,
          error: null,
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setState((previousState) => ({
          ...previousState,
          status: "error",
          error,
        }));
      });

    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  return state;
}
