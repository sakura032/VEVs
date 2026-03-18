import CartoonRepresentation from "./CartoonRepresentation";
import SpheresRepresentation from "./SpheresRepresentation";
import SticksRepresentation from "./SticksRepresentation";

export default function MolecularRepresentation({
  structure,
  effectiveDisplayMode,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
  renderProfile,
}) {
  if (effectiveDisplayMode === "cartoon") {
    return (
      <CartoonRepresentation
        structure={structure}
        visibilityFilter={visibilityFilter}
        selectedAtomIndex={selectedAtomIndex}
        onAtomSelect={onAtomSelect}
        tubeLineWidth={renderProfile.cartoonLineWidth}
        focusSphereRadius={renderProfile.cartoonFocusSphereRadius}
        focusSphereSegments={renderProfile.sphereSegments}
      />
    );
  }
  if (effectiveDisplayMode === "sticks") {
    return (
      <SticksRepresentation
        structure={structure}
        visibilityFilter={visibilityFilter}
        selectedAtomIndex={selectedAtomIndex}
        onAtomSelect={onAtomSelect}
        baseAtomRadius={renderProfile.stickAtomRadius}
        bondRadius={renderProfile.stickBondRadius}
        sphereSegments={renderProfile.sphereSegments}
        cylinderSegments={renderProfile.cylinderSegments}
        allowAutoBond={renderProfile.allowAutoBond}
        maxAutoBonds={renderProfile.maxAutoBonds}
      />
    );
  }
  return (
    <SpheresRepresentation
      structure={structure}
      visibilityFilter={visibilityFilter}
      selectedAtomIndex={selectedAtomIndex}
      onAtomSelect={onAtomSelect}
      baseRadius={renderProfile.sphereBaseRadius}
      sphereSegments={renderProfile.sphereSegments}
      toneWeight={0.42}
    />
  );
}

