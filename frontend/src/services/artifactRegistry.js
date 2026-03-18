export const VISUALIZATION_ROOT = "/visualization";

export const STRUCTURE_STAGES = [
  {
    id: "receptor_clean",
    label: "receptor_clean",
    relativePath: "work/preprocessed/receptor_clean.pdb",
  },
  {
    id: "ligand_prepared",
    label: "ligand_prepared",
    relativePath: "work/preprocessed/ligand_prepared.pdb",
  },
  {
    id: "complex_initial",
    label: "complex_initial",
    relativePath: "work/assembled/complex_initial.pdb",
  },
  {
    id: "complex_fixed",
    label: "complex_fixed",
    relativePath: "work/md/complex_fixed.pdb",
  },
  {
    id: "solvated",
    label: "solvated",
    relativePath: "work/md/solvated.pdb",
  },
  {
    id: "minimized",
    label: "minimized",
    relativePath: "work/md/minimized.pdb",
  },
  {
    id: "equil_nvt_last",
    label: "equil_nvt_last",
    relativePath: "work/md/equil_nvt_last.pdb",
  },
  {
    id: "equil_npt_last",
    label: "equil_npt_last",
    relativePath: "work/md/equil_npt_last.pdb",
  },
  {
    id: "trajectory",
    label: "trajectory",
    relativePath: "sampled_frames.json",
    isTrajectory: true,
  },
];

export const RESERVED_FUTURE_MODULES = [
  "Membrane Mode",
  "Endpoint FE",
  "PMF / Umbrella",
  "Multi-run Comparison",
  "Whole Vesicle Explorer",
];

export const RESERVED_ANALYTICS_TABS = [
  "H-bond",
  "Contacts",
  "Interface Map",
  "Endpoint FE",
  "PMF",
];

function cleanRunId(runId) {
  return encodeURIComponent((runId ?? "").trim());
}

export function getRunRoot(runId) {
  return `${VISUALIZATION_ROOT}/${cleanRunId(runId)}`;
}

export function getRunIndexUrl() {
  return `${VISUALIZATION_ROOT}/index.json`;
}

export function getPoseFileName(poseId) {
  const index = Number.parseInt(poseId, 10);
  if (Number.isNaN(index)) {
    return null;
  }
  return `pose_${String(index).padStart(3, "0")}.pdb`;
}

export function toPoseFileUrl(runId, poseId) {
  const fileName = getPoseFileName(poseId);
  if (!fileName) {
    return null;
  }
  return `${getRunRoot(runId)}/outputs/docking/poses/${fileName}`;
}

export function buildRunArtifacts(runId) {
  const root = getRunRoot(runId);
  const stageUrls = STRUCTURE_STAGES.reduce((accumulator, stage) => {
    accumulator[stage.id] = `${root}/${stage.relativePath}`;
    return accumulator;
  }, {});
  return {
    root,
    stageUrls,
    posesCsvUrl: `${root}/outputs/docking/poses.csv`,
    metricsUrl: `${root}/outputs/analysis/binding/metrics.json`,
    rmsdUrl: `${root}/outputs/analysis/binding/rmsd.csv`,
    mdLogUrl: `${root}/work/md/md_log.csv`,
    runManifestUrl: `${root}/outputs/metadata/run_manifest.json`,
    preprocessReportUrl: `${root}/outputs/metadata/preprocess_report.json`,
    mdPdbfixerReportUrl: `${root}/outputs/metadata/md_pdbfixer_report.json`,
    routeSummaryUrl: `${root}/outputs/reports/route_a_summary.md`,
    sampledFramesUrl: `${root}/sampled_frames.json`,
    structureRolesUrl: `${root}/derived/structure_roles.json`,
  };
}
