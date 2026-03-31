const PROTEIN_RESIDUES = new Set(["CD9", "CD63", "CD81"]);
const LIPID_RESIDUES = new Set(["CHOL", "POPC", "DPSM", "POPE", "POPS", "POP2"]);

export const VESICLE_RESIDUE_ORDER = [
  "CD9",
  "CD81",
  "CD63",
  "CHOL",
  "POPC",
  "DPSM",
  "POPE",
  "POPS",
  "POP2",
];

export const VESICLE_KIND_CODES = {
  protein: 0,
  lipid: 1,
  unknown: 2,
};

export const VESICLE_LEAFLET_CODES = {
  protein: 0,
  outer: 1,
  inner: 2,
  unknown: 3,
};

function parseGroAtomRecord(line, atomIndex) {
  const residueId = line.slice(0, 5).trim() || "0";
  const residue = line.slice(5, 10).trim() || "UNK";
  const atomName = line.slice(10, 15).trim() || "CG";
  const serial = Number.parseInt(line.slice(15, 20).trim(), 10) || atomIndex + 1;
  const x = Number.parseFloat(line.slice(20, 28).trim());
  const y = Number.parseFloat(line.slice(28, 36).trim());
  const z = Number.parseFloat(line.slice(36, 44).trim());
  if ([x, y, z].some((value) => Number.isNaN(value))) {
    return null;
  }
  return {
    residueId,
    residue,
    atomName,
    serial,
    x,
    y,
    z,
  };
}

function parseBoxLine(line) {
  const values = line
    .trim()
    .split(/\s+/)
    .map((token) => Number.parseFloat(token))
    .filter((value) => Number.isFinite(value));
  if (values.length < 3) {
    return null;
  }
  return { x: values[0], y: values[1], z: values[2] };
}

function resolveKindCode(residue) {
  if (PROTEIN_RESIDUES.has(residue)) {
    return VESICLE_KIND_CODES.protein;
  }
  if (LIPID_RESIDUES.has(residue)) {
    return VESICLE_KIND_CODES.lipid;
  }
  return VESICLE_KIND_CODES.unknown;
}

function classifyMoleculeLeaflets(molecules, center) {
  const moleculeLeaflets = new Uint8Array(molecules.length);
  const lipidMoleculeIndices = [];
  const lipidRadii = [];

  molecules.forEach((molecule, moleculeIndex) => {
    if (molecule.kindCode === VESICLE_KIND_CODES.protein) {
      moleculeLeaflets[moleculeIndex] = VESICLE_LEAFLET_CODES.protein;
      return;
    }
    if (molecule.kindCode !== VESICLE_KIND_CODES.lipid) {
      moleculeLeaflets[moleculeIndex] = VESICLE_LEAFLET_CODES.unknown;
      return;
    }
    const radius = Math.sqrt(
      (molecule.centerX - center.x) * (molecule.centerX - center.x) +
        (molecule.centerY - center.y) * (molecule.centerY - center.y) +
        (molecule.centerZ - center.z) * (molecule.centerZ - center.z),
    );
    lipidMoleculeIndices.push(moleculeIndex);
    lipidRadii.push(radius);
  });

  if (lipidRadii.length === 0) {
    return moleculeLeaflets;
  }

  let lowCentroid = Math.min(...lipidRadii);
  let highCentroid = Math.max(...lipidRadii);

  for (let iteration = 0; iteration < 8; iteration += 1) {
    let lowSum = 0;
    let lowCount = 0;
    let highSum = 0;
    let highCount = 0;

    lipidRadii.forEach((radius) => {
      if (Math.abs(radius - lowCentroid) <= Math.abs(radius - highCentroid)) {
        lowSum += radius;
        lowCount += 1;
      } else {
        highSum += radius;
        highCount += 1;
      }
    });

    const nextLow = lowCount > 0 ? lowSum / lowCount : lowCentroid;
    const nextHigh = highCount > 0 ? highSum / highCount : highCentroid;
    if (Math.abs(nextLow - lowCentroid) < 1e-6 && Math.abs(nextHigh - highCentroid) < 1e-6) {
      break;
    }
    lowCentroid = nextLow;
    highCentroid = nextHigh;
  }

  const innerCentroid = Math.min(lowCentroid, highCentroid);
  const outerCentroid = Math.max(lowCentroid, highCentroid);

  lipidMoleculeIndices.forEach((moleculeIndex, arrayIndex) => {
    const radius = lipidRadii[arrayIndex];
    moleculeLeaflets[moleculeIndex] =
      Math.abs(radius - outerCentroid) < Math.abs(radius - innerCentroid)
        ? VESICLE_LEAFLET_CODES.outer
        : VESICLE_LEAFLET_CODES.inner;
  });

  return moleculeLeaflets;
}

function sortResidueCatalog(residueCatalog) {
  return [...residueCatalog].sort((left, right) => {
    const leftOrder = VESICLE_RESIDUE_ORDER.indexOf(left.name);
    const rightOrder = VESICLE_RESIDUE_ORDER.indexOf(right.name);
    const safeLeftOrder = leftOrder === -1 ? Number.MAX_SAFE_INTEGER : leftOrder;
    const safeRightOrder = rightOrder === -1 ? Number.MAX_SAFE_INTEGER : rightOrder;
    if (safeLeftOrder !== safeRightOrder) {
      return safeLeftOrder - safeRightOrder;
    }
    return left.name.localeCompare(right.name);
  });
}

export async function loadGro(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load GRO: ${url} (${response.status})`);
  }

  const content = await response.text();
  const lines = content.split(/\r?\n/);
  if (lines.length < 3) {
    throw new Error(`Invalid GRO: ${url}`);
  }

  const declaredAtomCount = Number.parseInt(lines[1].trim(), 10);
  if (!Number.isFinite(declaredAtomCount) || declaredAtomCount <= 0) {
    throw new Error(`Invalid GRO atom count: ${url}`);
  }

  const atomLines = lines.slice(2, 2 + declaredAtomCount);
  if (atomLines.length !== declaredAtomCount) {
    throw new Error(`GRO atom block truncated: ${url}`);
  }

  const positions = new Float32Array(declaredAtomCount * 3);
  const residueCodes = new Uint8Array(declaredAtomCount);
  const kindCodes = new Uint8Array(declaredAtomCount);
  const serials = new Uint32Array(declaredAtomCount);

  const residueNameToCode = new Map();
  const residueNames = [];
  const residueBeadCounts = new Map();
  const residueMoleculeCounts = new Map();
  const molecules = [];

  let sumX = 0;
  let sumY = 0;
  let sumZ = 0;
  let minX = Number.POSITIVE_INFINITY;
  let maxX = Number.NEGATIVE_INFINITY;
  let minY = Number.POSITIVE_INFINITY;
  let maxY = Number.NEGATIVE_INFINITY;
  let minZ = Number.POSITIVE_INFINITY;
  let maxZ = Number.NEGATIVE_INFINITY;
  let lipidMinX = Number.POSITIVE_INFINITY;
  let lipidMaxX = Number.NEGATIVE_INFINITY;
  let lipidMinY = Number.POSITIVE_INFINITY;
  let lipidMaxY = Number.NEGATIVE_INFINITY;
  let lipidMinZ = Number.POSITIVE_INFINITY;
  let lipidMaxZ = Number.NEGATIVE_INFINITY;

  let currentMoleculeKey = null;
  let currentMoleculeStart = 0;
  let currentMoleculeResidue = "UNK";
  let currentMoleculeResidueCode = 0;
  let currentMoleculeKindCode = VESICLE_KIND_CODES.unknown;
  let moleculeSumX = 0;
  let moleculeSumY = 0;
  let moleculeSumZ = 0;
  let moleculeAtomCount = 0;

  function finalizeCurrentMolecule(endExclusive) {
    if (currentMoleculeKey === null || moleculeAtomCount === 0) {
      return;
    }
    molecules.push({
      start: currentMoleculeStart,
      end: endExclusive,
      residue: currentMoleculeResidue,
      residueCode: currentMoleculeResidueCode,
      kindCode: currentMoleculeKindCode,
      centerX: moleculeSumX / moleculeAtomCount,
      centerY: moleculeSumY / moleculeAtomCount,
      centerZ: moleculeSumZ / moleculeAtomCount,
    });
    residueMoleculeCounts.set(
      currentMoleculeResidue,
      (residueMoleculeCounts.get(currentMoleculeResidue) ?? 0) + 1,
    );
  }

  atomLines.forEach((line, atomIndex) => {
    const atom = parseGroAtomRecord(line, atomIndex);
    if (!atom) {
      throw new Error(`Failed to parse GRO atom record at line ${atomIndex + 3}`);
    }

    let residueCode = residueNameToCode.get(atom.residue);
    if (residueCode === undefined) {
      residueCode = residueNames.length;
      residueNameToCode.set(atom.residue, residueCode);
      residueNames.push(atom.residue);
    }

    const kindCode = resolveKindCode(atom.residue);
    const moleculeKey = `${atom.residueId}|${atom.residue}`;

    if (currentMoleculeKey !== moleculeKey) {
      finalizeCurrentMolecule(atomIndex);
      currentMoleculeKey = moleculeKey;
      currentMoleculeStart = atomIndex;
      currentMoleculeResidue = atom.residue;
      currentMoleculeResidueCode = residueCode;
      currentMoleculeKindCode = kindCode;
      moleculeSumX = 0;
      moleculeSumY = 0;
      moleculeSumZ = 0;
      moleculeAtomCount = 0;
    }

    const positionOffset = atomIndex * 3;
    positions[positionOffset] = atom.x;
    positions[positionOffset + 1] = atom.y;
    positions[positionOffset + 2] = atom.z;
    residueCodes[atomIndex] = residueCode;
    kindCodes[atomIndex] = kindCode;
    serials[atomIndex] = atom.serial;

    residueBeadCounts.set(atom.residue, (residueBeadCounts.get(atom.residue) ?? 0) + 1);

    moleculeSumX += atom.x;
    moleculeSumY += atom.y;
    moleculeSumZ += atom.z;
    moleculeAtomCount += 1;

    sumX += atom.x;
    sumY += atom.y;
    sumZ += atom.z;
    minX = Math.min(minX, atom.x);
    maxX = Math.max(maxX, atom.x);
    minY = Math.min(minY, atom.y);
    maxY = Math.max(maxY, atom.y);
    minZ = Math.min(minZ, atom.z);
    maxZ = Math.max(maxZ, atom.z);
    if (kindCode === VESICLE_KIND_CODES.lipid) {
      lipidMinX = Math.min(lipidMinX, atom.x);
      lipidMaxX = Math.max(lipidMaxX, atom.x);
      lipidMinY = Math.min(lipidMinY, atom.y);
      lipidMaxY = Math.max(lipidMaxY, atom.y);
      lipidMinZ = Math.min(lipidMinZ, atom.z);
      lipidMaxZ = Math.max(lipidMaxZ, atom.z);
    }
  });

  finalizeCurrentMolecule(declaredAtomCount);

  const center = {
    x: sumX / declaredAtomCount,
    y: sumY / declaredAtomCount,
    z: sumZ / declaredAtomCount,
  };

  const moleculeLeaflets = classifyMoleculeLeaflets(molecules, center);
  const leafletCodes = new Uint8Array(declaredAtomCount);
  const leafletBeadCounts = {
    protein: 0,
    outer: 0,
    inner: 0,
    unknown: 0,
  };
  const leafletMoleculeCounts = {
    protein: 0,
    outer: 0,
    inner: 0,
    unknown: 0,
  };

  molecules.forEach((molecule, moleculeIndex) => {
    const leafletCode = moleculeLeaflets[moleculeIndex];
    const leafletLabel =
      leafletCode === VESICLE_LEAFLET_CODES.protein
        ? "protein"
        : leafletCode === VESICLE_LEAFLET_CODES.outer
          ? "outer"
          : leafletCode === VESICLE_LEAFLET_CODES.inner
            ? "inner"
            : "unknown";
    leafletMoleculeCounts[leafletLabel] += 1;
    for (let atomIndex = molecule.start; atomIndex < molecule.end; atomIndex += 1) {
      leafletCodes[atomIndex] = leafletCode;
      leafletBeadCounts[leafletLabel] += 1;
    }
  });

  const moleculeCount = molecules.length;
  const moleculePositions = new Float32Array(moleculeCount * 3);
  const moleculeResidueCodes = new Uint8Array(moleculeCount);
  const moleculeKindCodes = new Uint8Array(moleculeCount);
  const moleculeLeafletCodes = new Uint8Array(moleculeCount);
  molecules.forEach((molecule, moleculeIndex) => {
    const offset = moleculeIndex * 3;
    moleculePositions[offset] = molecule.centerX;
    moleculePositions[offset + 1] = molecule.centerY;
    moleculePositions[offset + 2] = molecule.centerZ;
    moleculeResidueCodes[moleculeIndex] = molecule.residueCode;
    moleculeKindCodes[moleculeIndex] = molecule.kindCode;
    moleculeLeafletCodes[moleculeIndex] = moleculeLeaflets[moleculeIndex];
  });

  const hasLipidBounds = Number.isFinite(lipidMinX);
  const vesicleBounds = hasLipidBounds
    ? {
        minX: lipidMinX,
        maxX: lipidMaxX,
        minY: lipidMinY,
        maxY: lipidMaxY,
        minZ: lipidMinZ,
        maxZ: lipidMaxZ,
      }
    : {
        minX,
        maxX,
        minY,
        maxY,
        minZ,
        maxZ,
      };
  const vesicleCenter = {
    x: (vesicleBounds.minX + vesicleBounds.maxX) * 0.5,
    y: (vesicleBounds.minY + vesicleBounds.maxY) * 0.5,
    z: (vesicleBounds.minZ + vesicleBounds.maxZ) * 0.5,
  };

  const residueCatalog = sortResidueCatalog(
    residueNames.map((residueName, residueCode) => ({
      code: residueCode,
      name: residueName,
      kind:
        resolveKindCode(residueName) === VESICLE_KIND_CODES.protein
          ? "protein"
          : resolveKindCode(residueName) === VESICLE_KIND_CODES.lipid
            ? "lipid"
            : "unknown",
      beadCount: residueBeadCounts.get(residueName) ?? 0,
      moleculeCount: residueMoleculeCounts.get(residueName) ?? 0,
    })),
  );

  const box = parseBoxLine(lines[2 + declaredAtomCount] ?? "");

  return {
    atomCount: declaredAtomCount,
    positions,
    moleculeCount,
    moleculePositions,
    moleculeResidueCodes,
    moleculeKindCodes,
    moleculeLeafletCodes,
    residueCodes,
    kindCodes,
    leafletCodes,
    serials,
    residueNames,
    residueCatalog,
    center,
    bounds: {
      minX,
      maxX,
      minY,
      maxY,
      minZ,
      maxZ,
    },
    vesicleCenter,
    vesicleBounds,
    box,
    leafletCounts: {
      beads: leafletBeadCounts,
      molecules: leafletMoleculeCounts,
    },
    sourceUrl: url,
  };
}
