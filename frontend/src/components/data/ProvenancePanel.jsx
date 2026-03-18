import SectionCard from "../common/SectionCard";
import EmptyState from "../common/EmptyState";

function summarizePreprocess(report) {
  if (!report) {
    return "preprocess_report.json missing.";
  }
  const receptorMissing = report.receptor?.num_missing_atoms_residues ?? "N/A";
  const ligandMissing = report.ligand?.num_missing_atoms_residues ?? "N/A";
  const keepWater = report.keep_water;
  return `receptor_missing_atoms=${receptorMissing}, ligand_missing_atoms=${ligandMissing}, keep_water=${keepWater}`;
}

function summarizeMdFixer(report) {
  if (!report) {
    return "md_pdbfixer_report.json missing.";
  }
  const missing = report.missing_atoms_residues ?? "N/A";
  const nonstandard = report.nonstandard_residue_count ?? "N/A";
  return `missing_atoms_residues=${missing}, nonstandard_residue_count=${nonstandard}`;
}

export default function ProvenancePanel({
  manifest,
  preprocessReport,
  mdPdbfixerReport,
  embedded = false,
}) {
  const content = (
    <>
      {!manifest ? <EmptyState message="run_manifest.json missing." /> : null}
      {manifest ? (
        <dl className="kv-list">
          <div className="kv-item">
            <dt>backend</dt>
            <dd className="mono-text">{manifest.backend}</dd>
          </div>
          <div className="kv-item">
            <dt>analysis_mode</dt>
            <dd className="mono-text">{manifest.analysis_mode}</dd>
          </div>
          <div className="kv-item">
            <dt>scientific_validity</dt>
            <dd className="mono-text">{manifest.scientific_validity}</dd>
          </div>
          <div className="kv-item">
            <dt>preprocess summary</dt>
            <dd className="mono-text">{summarizePreprocess(preprocessReport)}</dd>
          </div>
          <div className="kv-item">
            <dt>md_pdbfixer summary</dt>
            <dd className="mono-text">{summarizeMdFixer(mdPdbfixerReport)}</dd>
          </div>
        </dl>
      ) : null}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <SectionCard
      title="Provenance & Boundary"
      subtitle="Boundary-first disclosure for backend and validity semantics"
    >
      {content}
    </SectionCard>
  );
}
