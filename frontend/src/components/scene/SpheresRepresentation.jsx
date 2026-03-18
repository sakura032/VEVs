import { useLayoutEffect, useMemo, useRef } from "react";
import { Color, Object3D } from "three";

import {
  blendColor,
  buildElementColorMap,
  buildRoleColorMap,
  clampValue,
  getElementColor,
  shouldIncludeAtomByFilter,
} from "./sceneRoles";

const ELEMENT_RADIUS = {
  H: 1.2,
  C: 1.7,
  N: 1.55,
  O: 1.52,
  F: 1.47,
  P: 1.8,
  S: 1.8,
  CL: 1.75,
  BR: 1.85,
  I: 1.98,
  FE: 1.8,
  MG: 1.73,
  ZN: 1.39,
  CA: 1.94,
};

function resolveAtomRadius(atom, baseRadius) {
  const elementRadius = ELEMENT_RADIUS[atom.element] ?? ELEMENT_RADIUS.C;
  return clampValue((elementRadius / 1.7) * baseRadius, baseRadius * 0.55, baseRadius * 1.45);
}

export default function SpheresRepresentation({
  structure,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
  baseRadius,
  sphereSegments,
  toneWeight = 0.35,
}) {
  const roleColorMap = useMemo(() => buildRoleColorMap(), []);
  const elementColorMap = useMemo(() => buildElementColorMap(), []);
  const meshRef = useRef(null);
  const helperObjectRef = useRef(new Object3D());
  const tempColorRef = useRef(new Color());

  const displayAtoms = useMemo(
    () =>
      structure.atoms.filter((atom) =>
        shouldIncludeAtomByFilter(atom, visibilityFilter),
      ),
    [structure.atoms, visibilityFilter],
  );

  const radiusLookup = useMemo(() => {
    const lookup = new Map();
    displayAtoms.forEach((atom) => {
      lookup.set(atom.atomIndex, resolveAtomRadius(atom, baseRadius));
    });
    return lookup;
  }, [displayAtoms, baseRadius]);

  useLayoutEffect(() => {
    const mesh = meshRef.current;
    if (!mesh) {
      return;
    }
    mesh.count = displayAtoms.length;
    const helper = helperObjectRef.current;
    const color = tempColorRef.current;
    for (let index = 0; index < displayAtoms.length; index += 1) {
      const atom = displayAtoms[index];
      const radius = radiusLookup.get(atom.atomIndex) ?? baseRadius;
      helper.position.set(atom.x, atom.y, atom.z);
      helper.rotation.set(0, 0, 0);
      helper.scale.set(radius, radius, radius);
      helper.updateMatrix();
      mesh.setMatrixAt(index, helper.matrix);

      const roleColor = roleColorMap[atom.role] ?? roleColorMap.receptor;
      const elementColor = getElementColor(atom.element, elementColorMap);
      color.copy(blendColor(roleColor, elementColor, toneWeight));
      mesh.setColorAt(index, color);
    }
    mesh.instanceMatrix.needsUpdate = true;
    if (mesh.instanceColor) {
      mesh.instanceColor.needsUpdate = true;
    }
  }, [
    baseRadius,
    displayAtoms,
    elementColorMap,
    radiusLookup,
    roleColorMap,
    toneWeight,
  ]);

  const selectedAtom = useMemo(
    () => displayAtoms.find((atom) => atom.atomIndex === selectedAtomIndex) ?? null,
    [displayAtoms, selectedAtomIndex],
  );
  const selectedAtomRadius = selectedAtom
    ? (radiusLookup.get(selectedAtom.atomIndex) ?? baseRadius) * 1.45
    : null;

  return (
    <>
      <instancedMesh
        ref={meshRef}
        args={[null, null, displayAtoms.length]}
        onClick={(event) => {
          if (event.instanceId === undefined || event.instanceId === null) {
            return;
          }
          const atom = displayAtoms[event.instanceId];
          if (atom) {
            onAtomSelect(atom);
          }
        }}
      >
        <sphereGeometry args={[1, sphereSegments, sphereSegments]} />
        <meshStandardMaterial roughness={0.42} metalness={0.06} />
      </instancedMesh>

      {selectedAtom ? (
        <mesh position={[selectedAtom.x, selectedAtom.y, selectedAtom.z]}>
          <sphereGeometry args={[selectedAtomRadius, 20, 20]} />
          <meshStandardMaterial
            color={roleColorMap.unresolved}
            transparent
            opacity={0.35}
            emissive={roleColorMap.unresolved}
            emissiveIntensity={0.35}
          />
        </mesh>
      ) : null}
    </>
  );
}

