import MolecularRepresentation from "./MolecularRepresentation";

export default function StructureStageView({
  structure,
  effectiveDisplayMode,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
  renderProfile,
}) {
  return (
    <MolecularRepresentation
      structure={structure}
      effectiveDisplayMode={effectiveDisplayMode}
      visibilityFilter={visibilityFilter}
      selectedAtomIndex={selectedAtomIndex}
      onAtomSelect={onAtomSelect}
      renderProfile={renderProfile}
    />
  );
}
