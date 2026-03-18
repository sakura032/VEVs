import { useMemo } from "react";
import { Color } from "three";

function cssColor(variableName, fallback) {
  if (typeof window === "undefined") {
    return fallback;
  }
  const value = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue(variableName)
    .trim();
  return value || fallback;
}

function buildCategoryColorMap() {
  return {
    receptor: new Color(cssColor("--accent-receptor", "#4f6d8a")),
    ligand: new Color(cssColor("--accent-ligand", "#2a927a")),
    water: new Color(cssColor("--text-muted", "#738396")),
  };
}

function shouldIncludeAtom(atom, visibilityFilter) {
  if (visibilityFilter === "all") {
    return atom.category !== "water";
  }
  if (visibilityFilter === "receptor") {
    return atom.category === "receptor";
  }
  if (visibilityFilter === "ligand") {
    return atom.category === "ligand";
  }
  return atom.category !== "water";
}

function resolvePointSize(displayMode) {
  if (displayMode === "spheres") {
    return 0.22;
  }
  if (displayMode === "sticks") {
    return 0.16;
  }
  return 0.12;
}

export default function AtomPointCloud({
  structure,
  displayMode,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
}) {
  const categoryColorMap = useMemo(() => buildCategoryColorMap(), []);
  const displayAtoms = useMemo(
    () =>
      structure.atoms.filter((atom) => shouldIncludeAtom(atom, visibilityFilter)),
    [structure.atoms, visibilityFilter],
  );
  const geometryPayload = useMemo(() => {
    const positions = new Float32Array(displayAtoms.length * 3);
    const colors = new Float32Array(displayAtoms.length * 3);
    displayAtoms.forEach((atom, atomOffset) => {
      const color = categoryColorMap[atom.category] ?? categoryColorMap.receptor;
      const arrayIndex = atomOffset * 3;
      positions[arrayIndex] = atom.x;
      positions[arrayIndex + 1] = atom.y;
      positions[arrayIndex + 2] = atom.z;
      colors[arrayIndex] = color.r;
      colors[arrayIndex + 1] = color.g;
      colors[arrayIndex + 2] = color.b;
    });
    return { positions, colors };
  }, [displayAtoms, categoryColorMap]);

  const selectedAtom = useMemo(
    () => displayAtoms.find((atom) => atom.atomIndex === selectedAtomIndex) ?? null,
    [displayAtoms, selectedAtomIndex],
  );
  const pointSize = resolvePointSize(displayMode);

  return (
    <>
      <points
        onClick={(event) => {
          if (event.index === undefined || event.index === null) {
            return;
          }
          const atom = displayAtoms[event.index];
          if (atom) {
            onAtomSelect(atom);
          }
        }}
      >
        <bufferGeometry>
          <bufferAttribute
            attach="attributes-position"
            array={geometryPayload.positions}
            count={geometryPayload.positions.length / 3}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            array={geometryPayload.colors}
            count={geometryPayload.colors.length / 3}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial size={pointSize} sizeAttenuation vertexColors />
      </points>

      {selectedAtom ? (
        <mesh position={[selectedAtom.x, selectedAtom.y, selectedAtom.z]}>
          <sphereGeometry args={[pointSize * 0.9, 16, 16]} />
          <meshStandardMaterial color={cssColor("--accent-selected", "#2e8b57")} />
        </mesh>
      ) : null}
    </>
  );
}
