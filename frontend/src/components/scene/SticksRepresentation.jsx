import { useLayoutEffect, useMemo, useRef } from "react";
import { Color, Object3D, Quaternion, Vector3 } from "three";

import {
  blendColor,
  buildElementColorMap,
  buildRoleColorMap,
  clampValue,
  getElementColor,
  shouldIncludeAtomByFilter,
} from "./sceneRoles";

const COVALENT_RADIUS = {
  H: 0.31,
  C: 0.76,
  N: 0.71,
  O: 0.66,
  F: 0.57,
  P: 1.07,
  S: 1.05,
  CL: 1.02,
  BR: 1.2,
  I: 1.39,
};

function resolveCovalentRadius(element) {
  return COVALENT_RADIUS[element] ?? COVALENT_RADIUS.C;
}

function buildBondPairsFromConect(displayAtoms, structureBonds) {
  if (!Array.isArray(structureBonds) || structureBonds.length === 0) {
    return [];
  }
  const displaySet = new Set(displayAtoms.map((atom) => atom.atomIndex));
  return structureBonds.filter(
    (pair) =>
      Array.isArray(pair) &&
      pair.length === 2 &&
      displaySet.has(pair[0]) &&
      displaySet.has(pair[1]),
  );
}

function buildAutoBondPairs(displayAtoms, maxPairs) {
  if (displayAtoms.length < 2) {
    return [];
  }
  const cellSize = 2.2;
  const cells = new Map();
  const offsets = [-1, 0, 1];
  const pairs = [];
  const pairSet = new Set();

  function keyForCell(x, y, z) {
    return `${x}|${y}|${z}`;
  }

  function cellIndex(value) {
    return Math.floor(value / cellSize);
  }

  displayAtoms.forEach((atom, index) => {
    const cx = cellIndex(atom.x);
    const cy = cellIndex(atom.y);
    const cz = cellIndex(atom.z);
    const key = keyForCell(cx, cy, cz);
    if (!cells.has(key)) {
      cells.set(key, []);
    }
    cells.get(key).push(index);
  });

  for (let leftIndex = 0; leftIndex < displayAtoms.length; leftIndex += 1) {
    const leftAtom = displayAtoms[leftIndex];
    const cx = cellIndex(leftAtom.x);
    const cy = cellIndex(leftAtom.y);
    const cz = cellIndex(leftAtom.z);
    for (let ox = 0; ox < offsets.length; ox += 1) {
      for (let oy = 0; oy < offsets.length; oy += 1) {
        for (let oz = 0; oz < offsets.length; oz += 1) {
          const key = keyForCell(cx + offsets[ox], cy + offsets[oy], cz + offsets[oz]);
          const neighbors = cells.get(key);
          if (!neighbors) {
            continue;
          }
          for (let idx = 0; idx < neighbors.length; idx += 1) {
            const rightIndex = neighbors[idx];
            if (rightIndex <= leftIndex) {
              continue;
            }
            const rightAtom = displayAtoms[rightIndex];
            const dx = leftAtom.x - rightAtom.x;
            const dy = leftAtom.y - rightAtom.y;
            const dz = leftAtom.z - rightAtom.z;
            const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);
            const threshold = clampValue(
              resolveCovalentRadius(leftAtom.element) +
                resolveCovalentRadius(rightAtom.element) +
                0.45,
              0.9,
              2.15,
            );
            if (distance <= threshold) {
              const minIndex = Math.min(leftAtom.atomIndex, rightAtom.atomIndex);
              const maxIndex = Math.max(leftAtom.atomIndex, rightAtom.atomIndex);
              const pairKey = `${minIndex}:${maxIndex}`;
              if (pairSet.has(pairKey)) {
                continue;
              }
              pairSet.add(pairKey);
              pairs.push([leftAtom.atomIndex, rightAtom.atomIndex]);
              if (pairs.length >= maxPairs) {
                return pairs;
              }
            }
          }
        }
      }
    }
  }
  return pairs;
}

function resolveAtomRadius(atom, baseAtomRadius) {
  const scale =
    atom.element === "H"
      ? 0.62
      : atom.element === "C"
        ? 1
        : atom.element === "O" || atom.element === "N"
          ? 0.9
          : 1.06;
  return clampValue(baseAtomRadius * scale, baseAtomRadius * 0.58, baseAtomRadius * 1.35);
}

export default function SticksRepresentation({
  structure,
  visibilityFilter,
  selectedAtomIndex,
  onAtomSelect,
  baseAtomRadius,
  bondRadius,
  sphereSegments,
  cylinderSegments,
  allowAutoBond,
  maxAutoBonds,
}) {
  const roleColorMap = useMemo(() => buildRoleColorMap(), []);
  const elementColorMap = useMemo(() => buildElementColorMap(), []);
  const atomMeshRef = useRef(null);
  const bondMeshRef = useRef(null);
  const helperObjectRef = useRef(new Object3D());
  const tempColorRef = useRef(new Color());
  const bondDirectionRef = useRef(new Vector3());
  const bondQuaternionRef = useRef(new Quaternion());
  const worldYRef = useRef(new Vector3(0, 1, 0));
  const bondMidRef = useRef(new Vector3());

  const displayAtoms = useMemo(
    () =>
      structure.atoms.filter((atom) =>
        shouldIncludeAtomByFilter(atom, visibilityFilter),
      ),
    [structure.atoms, visibilityFilter],
  );

  const atomLookup = useMemo(() => {
    const lookup = new Map();
    displayAtoms.forEach((atom) => lookup.set(atom.atomIndex, atom));
    return lookup;
  }, [displayAtoms]);

  const bondPairs = useMemo(() => {
    const fromConect = buildBondPairsFromConect(displayAtoms, structure.bonds);
    if (fromConect.length > 0) {
      return fromConect;
    }
    if (!allowAutoBond) {
      return [];
    }
    return buildAutoBondPairs(displayAtoms, maxAutoBonds);
  }, [allowAutoBond, displayAtoms, maxAutoBonds, structure.bonds]);

  useLayoutEffect(() => {
    const atomMesh = atomMeshRef.current;
    if (!atomMesh) {
      return;
    }
    atomMesh.count = displayAtoms.length;
    const helper = helperObjectRef.current;
    const color = tempColorRef.current;
    for (let index = 0; index < displayAtoms.length; index += 1) {
      const atom = displayAtoms[index];
      const radius = resolveAtomRadius(atom, baseAtomRadius);
      helper.position.set(atom.x, atom.y, atom.z);
      helper.rotation.set(0, 0, 0);
      helper.scale.set(radius, radius, radius);
      helper.updateMatrix();
      atomMesh.setMatrixAt(index, helper.matrix);

      const roleColor = roleColorMap[atom.role] ?? roleColorMap.receptor;
      const elementColor = getElementColor(atom.element, elementColorMap);
      color.copy(blendColor(roleColor, elementColor, 0.4));
      atomMesh.setColorAt(index, color);
    }
    atomMesh.instanceMatrix.needsUpdate = true;
    if (atomMesh.instanceColor) {
      atomMesh.instanceColor.needsUpdate = true;
    }
  }, [baseAtomRadius, displayAtoms, elementColorMap, roleColorMap]);

  useLayoutEffect(() => {
    const bondMesh = bondMeshRef.current;
    if (!bondMesh) {
      return;
    }
    bondMesh.count = bondPairs.length;
    const helper = helperObjectRef.current;
    const color = tempColorRef.current;
    const direction = bondDirectionRef.current;
    const quaternion = bondQuaternionRef.current;
    const worldY = worldYRef.current;
    const midpoint = bondMidRef.current;

    for (let index = 0; index < bondPairs.length; index += 1) {
      const [leftAtomIndex, rightAtomIndex] = bondPairs[index];
      const leftAtom = atomLookup.get(leftAtomIndex);
      const rightAtom = atomLookup.get(rightAtomIndex);
      if (!leftAtom || !rightAtom) {
        continue;
      }
      midpoint.set(
        (leftAtom.x + rightAtom.x) * 0.5,
        (leftAtom.y + rightAtom.y) * 0.5,
        (leftAtom.z + rightAtom.z) * 0.5,
      );
      direction.set(
        rightAtom.x - leftAtom.x,
        rightAtom.y - leftAtom.y,
        rightAtom.z - leftAtom.z,
      );
      const distance = direction.length();
      if (distance < 1e-6) {
        continue;
      }
      direction.normalize();
      quaternion.setFromUnitVectors(worldY, direction);

      helper.position.copy(midpoint);
      helper.quaternion.copy(quaternion);
      helper.scale.set(bondRadius, distance, bondRadius);
      helper.updateMatrix();
      bondMesh.setMatrixAt(index, helper.matrix);

      const leftColor = roleColorMap[leftAtom.role] ?? roleColorMap.receptor;
      const rightColor = roleColorMap[rightAtom.role] ?? roleColorMap.receptor;
      color.copy(leftColor).lerp(rightColor, 0.5);
      bondMesh.setColorAt(index, color);
    }
    bondMesh.instanceMatrix.needsUpdate = true;
    if (bondMesh.instanceColor) {
      bondMesh.instanceColor.needsUpdate = true;
    }
  }, [atomLookup, bondPairs, bondRadius, roleColorMap]);

  const selectedAtom = useMemo(
    () => displayAtoms.find((atom) => atom.atomIndex === selectedAtomIndex) ?? null,
    [displayAtoms, selectedAtomIndex],
  );
  const selectedRadius = selectedAtom
    ? resolveAtomRadius(selectedAtom, baseAtomRadius) * 1.35
    : null;

  return (
    <>
      <instancedMesh
        ref={bondMeshRef}
        args={[null, null, bondPairs.length]}
      >
        <cylinderGeometry args={[1, 1, 1, cylinderSegments]} />
        <meshStandardMaterial roughness={0.56} metalness={0.04} />
      </instancedMesh>

      <instancedMesh
        ref={atomMeshRef}
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
        <meshStandardMaterial roughness={0.36} metalness={0.08} />
      </instancedMesh>

      {selectedAtom ? (
        <mesh position={[selectedAtom.x, selectedAtom.y, selectedAtom.z]}>
          <sphereGeometry args={[selectedRadius, 20, 20]} />
          <meshStandardMaterial
            color={roleColorMap.unresolved}
            transparent
            opacity={0.35}
            emissive={roleColorMap.unresolved}
            emissiveIntensity={0.34}
          />
        </mesh>
      ) : null}
    </>
  );
}

