import { Color } from "three";

import {
  VESICLE_KIND_CODES,
  VESICLE_LEAFLET_CODES,
} from "../../../lib/loaders/loadGro";
import { RESIDUE_COLOR_HEX, SPHERE_RENDER_LIMIT } from "../constants/catalog";

export function formatCount(value) {
  return new Intl.NumberFormat("en-US").format(value ?? 0);
}

function clampValue(value, minValue, maxValue) {
  return Math.max(minValue, Math.min(maxValue, value));
}

function computeDiagonal(bounds) {
  if (!bounds) {
    return 1;
  }
  const dx = bounds.maxX - bounds.minX;
  const dy = bounds.maxY - bounds.minY;
  const dz = bounds.maxZ - bounds.minZ;
  const diagonal = Math.sqrt(dx * dx + dy * dy + dz * dz);
  return Number.isFinite(diagonal) && diagonal > 0 ? diagonal : 1;
}

function buildResidueColorMap(structure) {
  const colorMap = new Map();
  structure.residueNames.forEach((residueName, residueCode) => {
    colorMap.set(residueCode, new Color(RESIDUE_COLOR_HEX[residueName] ?? RESIDUE_COLOR_HEX.UNK));
  });
  return colorMap;
}

export function buildResidueFilterOptions(structure) {
  if (!structure) {
    return [];
  }
  return [
    { value: "all", label: "all residues" },
    { value: "proteins", label: "proteins only" },
    { value: "lipids", label: "lipids only" },
    ...structure.residueCatalog.map((entry) => ({
      value: entry.name,
      label: `${entry.name} (${formatCount(entry.moleculeCount)} molecules)`,
    })),
  ];
}

function resolveClipThreshold(bounds, clipAxis, clipFraction) {
  if (clipAxis === "none") {
    return null;
  }
  const axisMeta =
    clipAxis === "x"
      ? { minKey: "minX", maxKey: "maxX" }
      : clipAxis === "y"
        ? { minKey: "minY", maxKey: "maxY" }
        : { minKey: "minZ", maxKey: "maxZ" };
  const axisMin = bounds[axisMeta.minKey];
  const axisMax = bounds[axisMeta.maxKey];
  return axisMin + (axisMax - axisMin) * clipFraction;
}

export function buildFilteredRenderPayload(
  structure,
  {
    residueFilter,
    leafletFilter,
    displayMode,
    representationMode,
    clipAxis,
    clipSide,
    clipFraction,
  },
) {
  if (!structure) {
    return null;
  }

  const axisIndex =
    clipAxis === "x" ? 0 : clipAxis === "y" ? 1 : clipAxis === "z" ? 2 : -1;
  const baseBounds =
    representationMode === "overview"
      ? (structure.vesicleBounds ?? structure.bounds)
      : structure.bounds;
  const clipThreshold = resolveClipThreshold(baseBounds, clipAxis, clipFraction);
  const residueColorMap = buildResidueColorMap(structure);

  const includeEntry = ({ kindCode, leafletCode, residueName, coordinate }) => {
    if (residueFilter === "proteins" && kindCode !== VESICLE_KIND_CODES.protein) {
      return false;
    }
    if (residueFilter === "lipids" && kindCode !== VESICLE_KIND_CODES.lipid) {
      return false;
    }
    if (
      residueFilter !== "all" &&
      residueFilter !== "proteins" &&
      residueFilter !== "lipids" &&
      residueName !== residueFilter
    ) {
      return false;
    }

    if (leafletFilter === "outer" && leafletCode !== VESICLE_LEAFLET_CODES.outer) {
      return false;
    }
    if (leafletFilter === "inner" && leafletCode !== VESICLE_LEAFLET_CODES.inner) {
      return false;
    }
    if (leafletFilter === "protein" && leafletCode !== VESICLE_LEAFLET_CODES.protein) {
      return false;
    }

    if (axisIndex !== -1 && clipThreshold !== null) {
      if (clipSide === "positive" && coordinate < clipThreshold) {
        return false;
      }
      if (clipSide === "negative" && coordinate > clipThreshold) {
        return false;
      }
    }

    return true;
  };

  const forEachRenderablePoint = (visitor) => {
    if (representationMode === "overview") {
      for (let atomIndex = 0; atomIndex < structure.atomCount; atomIndex += 1) {
        const kindCode = structure.kindCodes[atomIndex];
        if (kindCode !== VESICLE_KIND_CODES.protein) {
          continue;
        }
        const residueCode = structure.residueCodes[atomIndex];
        const residueName = structure.residueNames[residueCode];
        const leafletCode = structure.leafletCodes[atomIndex];
        const offset = atomIndex * 3;
        const x = structure.positions[offset];
        const y = structure.positions[offset + 1];
        const z = structure.positions[offset + 2];
        if (
          !includeEntry({
            kindCode,
            leafletCode,
            residueName,
            coordinate: axisIndex === -1 ? 0 : structure.positions[offset + axisIndex],
          })
        ) {
          continue;
        }
        visitor({ x, y, z, residueCode });
      }

      for (let moleculeIndex = 0; moleculeIndex < structure.moleculeCount; moleculeIndex += 1) {
        const kindCode = structure.moleculeKindCodes[moleculeIndex];
        if (kindCode !== VESICLE_KIND_CODES.lipid) {
          continue;
        }
        const residueCode = structure.moleculeResidueCodes[moleculeIndex];
        const residueName = structure.residueNames[residueCode];
        const leafletCode = structure.moleculeLeafletCodes[moleculeIndex];
        const offset = moleculeIndex * 3;
        const x = structure.moleculePositions[offset];
        const y = structure.moleculePositions[offset + 1];
        const z = structure.moleculePositions[offset + 2];
        if (
          !includeEntry({
            kindCode,
            leafletCode,
            residueName,
            coordinate: axisIndex === -1 ? 0 : structure.moleculePositions[offset + axisIndex],
          })
        ) {
          continue;
        }
        visitor({ x, y, z, residueCode });
      }
      return;
    }

    for (let atomIndex = 0; atomIndex < structure.atomCount; atomIndex += 1) {
      const kindCode = structure.kindCodes[atomIndex];
      const leafletCode = structure.leafletCodes[atomIndex];
      const residueCode = structure.residueCodes[atomIndex];
      const residueName = structure.residueNames[residueCode];
      const offset = atomIndex * 3;
      const x = structure.positions[offset];
      const y = structure.positions[offset + 1];
      const z = structure.positions[offset + 2];
      if (
        !includeEntry({
          kindCode,
          leafletCode,
          residueName,
          coordinate: axisIndex === -1 ? 0 : structure.positions[offset + axisIndex],
        })
      ) {
        continue;
      }
      visitor({ x, y, z, residueCode });
    }
  };

  let includedCount = 0;
  let sumX = 0;
  let sumY = 0;
  let sumZ = 0;
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;

  forEachRenderablePoint(({ x, y, z }) => {
    includedCount += 1;
    sumX += x;
    sumY += y;
    sumZ += z;
    minX = Math.min(minX, x);
    maxX = Math.max(maxX, x);
    minY = Math.min(minY, y);
    maxY = Math.max(maxY, y);
    minZ = Math.min(minZ, z);
    maxZ = Math.max(maxZ, z);
  });

  if (includedCount === 0) {
    return {
      count: 0,
      positions: new Float32Array(0),
      colors: new Float32Array(0),
      center: null,
      bounds: null,
      effectiveDisplayMode: "points",
      pointSize: 0.2,
      sphereRadius: 0.12,
      note: "Current filters remove every bead.",
      clipThreshold,
    };
  }

  const positions = new Float32Array(includedCount * 3);
  const colors = new Float32Array(includedCount * 3);
  let writeIndex = 0;

  forEachRenderablePoint(({ x, y, z, residueCode }) => {
    const targetOffset = writeIndex * 3;
    positions[targetOffset] = x;
    positions[targetOffset + 1] = y;
    positions[targetOffset + 2] = z;

    const color = residueColorMap.get(residueCode);
    colors[targetOffset] = color.r;
    colors[targetOffset + 1] = color.g;
    colors[targetOffset + 2] = color.b;
    writeIndex += 1;
  });

  const bounds = { minX, maxX, minY, maxY, minZ, maxZ };
  const diagonal = computeDiagonal(bounds);
  const pointSize =
    representationMode === "overview"
      ? clampValue(diagonal / 320, 0.2, 0.58)
      : clampValue(diagonal / 420, 0.16, 0.42);
  const sphereRadius =
    representationMode === "overview"
      ? clampValue(diagonal / 520, 0.1, 0.26)
      : clampValue(diagonal / 620, 0.08, 0.22);

  let effectiveDisplayMode = displayMode;
  let note = null;
  if (displayMode === "spheres" && includedCount > SPHERE_RENDER_LIMIT) {
    effectiveDisplayMode = "points";
    note = `Filtered subset still has ${formatCount(includedCount)} markers, so rendering falls back to points. Narrow the filters or add clipping to enable local spheres.`;
  } else if (representationMode === "overview") {
    note =
      "Overview mode renders lipids as molecule-center markers and proteins as bead clouds so the closed vesicle shell remains legible at whole-system scale.";
  }

  return {
    count: includedCount,
    positions,
    colors,
    center: {
      x: sumX / includedCount,
      y: sumY / includedCount,
      z: sumZ / includedCount,
    },
    bounds,
    effectiveDisplayMode,
    pointSize,
    sphereRadius,
    note,
    clipThreshold,
  };
}
