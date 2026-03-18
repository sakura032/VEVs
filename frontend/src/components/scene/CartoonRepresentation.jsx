import { Line } from "@react-three/drei";
import { useLayoutEffect, useMemo, useRef } from "react";
import { Color, Object3D } from "three";

import {
  buildElementColorMap,
  buildRoleColorMap,
  clampValue,
  getElementColor,
  shouldIncludeAtomByFilter,
} from "./sceneRoles";

function residueOrder(residueId) {
  const parsed = Number.parseInt(residueId, 10);
  return Number.isNaN(parsed) ? 0 : parsed;
}

function buildTraceGroups(displayAtoms) {
  const chains = new Map();
  displayAtoms.forEach((atom) => {
    if (atom.atomName !== "CA") {
      return;
    }
    const chainId = atom.chainId || "_";
    if (!chains.has(chainId)) {
      chains.set(chainId, []);
    }
    chains.get(chainId).push(atom);
  });
  return Array.from(chains.entries())
    .map(([chainId, atoms]) => ({
      chainId,
      atoms: atoms.sort((left, right) => residueOrder(left.residueId) - residueOrder(right.residueId)),
    }))
    .filter((entry) => entry.atoms.length >= 2);
}

function buildFocusAtoms(displayAtoms) {
  const preferred = displayAtoms.filter(
    (atom) =>
      atom.atomName === "CA" ||
      atom.role === "ligand" ||
      atom.role === "unresolved",
  );
  if (preferred.length <= 3000) {
    return preferred;
  }
  const step = Math.ceil(preferred.length / 3000);
  return preferred.filter((_, index) => index % step === 0);
}

export default function CartoonRepresentation({
  structure,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
  tubeLineWidth,
  focusSphereRadius,
  focusSphereSegments,
}) {
  const roleColorMap = useMemo(() => buildRoleColorMap(), []);
  const elementColorMap = useMemo(() => buildElementColorMap(), []);
  const focusMeshRef = useRef(null);
  const helperObjectRef = useRef(new Object3D());
  const tempColorRef = useRef(new Color());

  const displayAtoms = useMemo(
    () =>
      structure.atoms.filter((atom) =>
        shouldIncludeAtomByFilter(atom, visibilityFilter),
      ),
    [structure.atoms, visibilityFilter],
  );
  const traceGroups = useMemo(() => buildTraceGroups(displayAtoms), [displayAtoms]);
  const focusAtoms = useMemo(() => buildFocusAtoms(displayAtoms), [displayAtoms]);

  useLayoutEffect(() => {
    const mesh = focusMeshRef.current;
    if (!mesh) {
      return;
    }
    mesh.count = focusAtoms.length;
    const helper = helperObjectRef.current;
    const color = tempColorRef.current;
    for (let index = 0; index < focusAtoms.length; index += 1) {
      const atom = focusAtoms[index];
      helper.position.set(atom.x, atom.y, atom.z);
      helper.rotation.set(0, 0, 0);
      helper.scale.set(1, 1, 1);
      helper.updateMatrix();
      mesh.setMatrixAt(index, helper.matrix);
      const roleColor = roleColorMap[atom.role] ?? roleColorMap.receptor;
      const elementColor = getElementColor(atom.element, elementColorMap);
      color.copy(roleColor).lerp(elementColor, 0.22);
      mesh.setColorAt(index, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true;
    }
  }, [elementColorMap, focusAtoms, roleColorMap]);

  const selectedAtom = useMemo(
    () => displayAtoms.find((atom) => atom.atomIndex === selectedAtomIndex) ?? null,
    [displayAtoms, selectedAtomIndex],
  );
  const selectedRadius = clampValue(focusSphereRadius * 1.85, 0.22, 1.2);

  return (
    <>
      {traceGroups.map((entry) => {
        const primaryRole = entry.atoms[0]?.role ?? "receptor";
        const traceColor = roleColorMap[primaryRole] ?? roleColorMap.receptor;
        return (
          <Line
            key={`chain-${entry.chainId}`}
            points={entry.atoms.map((atom) => [atom.x, atom.y, atom.z])}
            color={traceColor}
            lineWidth={tubeLineWidth}
          />
        );
      })}

      <instancedMesh
        ref={focusMeshRef}
        args={[null, null, focusAtoms.length]}
        onClick={(event) => {
          if (event.instanceId === undefined || event.instanceId === null) {
            return;
          }
          const atom = focusAtoms[event.instanceId];
          if (atom) {
            onAtomSelect(atom);
          }
        }}
      >
        <sphereGeometry args={[focusSphereRadius, focusSphereSegments, focusSphereSegments]} />
        <meshStandardMaterial roughness={0.5} metalness={0.02} />
      </instancedMesh>

      {selectedAtom ? (
        <mesh position={[selectedAtom.x, selectedAtom.y, selectedAtom.z]}>
          <sphereGeometry args={[selectedRadius, 18, 18]} />
          <meshStandardMaterial
            color={roleColorMap.unresolved}
            transparent
            opacity={0.32}
            emissive={roleColorMap.unresolved}
            emissiveIntensity={0.35}
          />
        </mesh>
      ) : null}
    </>
  );
}

