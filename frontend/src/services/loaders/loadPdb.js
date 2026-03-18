function parseAtomRecord(line, atomIndex) {
  const serialRaw = line.slice(6, 11).trim();
  const serialValue = Number.parseInt(serialRaw, 10);
  const x = Number.parseFloat(line.slice(30, 38).trim());
  const y = Number.parseFloat(line.slice(38, 46).trim());
  const z = Number.parseFloat(line.slice(46, 54).trim());
  if ([x, y, z].some((value) => Number.isNaN(value))) {
    return null;
  }

  const residue = line.slice(17, 20).trim();
  const atomName = line.slice(12, 16).trim();
  const chainId = line.slice(21, 22).trim() || "_";
  const residueId = line.slice(22, 26).trim() || "0";
  const elementSymbol = line.slice(76, 78).trim() || atomName[0] || "C";
  const occupancyValue = Number.parseFloat(line.slice(54, 60).trim());
  const bFactorValue = Number.parseFloat(line.slice(60, 66).trim());
  const isHetAtom = line.startsWith("HETATM");
  const isWater = ["HOH", "WAT", "TIP3"].includes(residue);
  const serial = Number.isNaN(serialValue) ? atomIndex + 1 : serialValue;

  let category = "receptor";
  if (isWater) {
    category = "water";
  } else if (isHetAtom) {
    category = "ligand";
  }

  const atomKey = `${serial}|${chainId}|${residueId}|${residue || "UNK"}|${
    atomName || "UNK"
  }`;
  return {
    atomIndex,
    serial,
    atomName,
    residue,
    chainId,
    residueId,
    insertionCode: line.slice(26, 27).trim() || "",
    altLoc: line.slice(16, 17).trim() || "",
    occupancy: Number.isNaN(occupancyValue) ? null : occupancyValue,
    bFactor: Number.isNaN(bFactorValue) ? null : bFactorValue,
    element: elementSymbol.toUpperCase(),
    x,
    y,
    z,
    category,
    role: category,
    roleConfidence: "fallback",
    atomKey,
    raw: line,
  };
}

export async function loadPdb(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load PDB: ${url} (${response.status})`);
  }
  const content = await response.text();
  const atoms = [];
  const serialToAtomIndex = new Map();
  const bondPairs = [];
  const bondPairSet = new Set();
  const lines = content.split(/\r?\n/);
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.startsWith("ATOM") && !line.startsWith("HETATM")) {
      continue;
    }
    const atom = parseAtomRecord(line, atoms.length);
    if (atom) {
      serialToAtomIndex.set(atom.serial, atom.atomIndex);
      atoms.push(atom);
    }
  }
  for (let index = 0; index < lines.length; index += 1) {
    const line = lines[index];
    if (!line.startsWith("CONECT")) {
      continue;
    }
    const serialTokens = line
      .slice(6)
      .trim()
      .match(/\d+/g);
    if (!serialTokens || serialTokens.length < 2) {
      continue;
    }
    const sourceSerial = Number.parseInt(serialTokens[0], 10);
    const sourceIndex = serialToAtomIndex.get(sourceSerial);
    if (sourceIndex === undefined) {
      continue;
    }
    serialTokens.slice(1).forEach((token) => {
      const targetSerial = Number.parseInt(token, 10);
      const targetIndex = serialToAtomIndex.get(targetSerial);
      if (targetIndex === undefined || targetIndex === sourceIndex) {
        return;
      }
      const left = Math.min(sourceIndex, targetIndex);
      const right = Math.max(sourceIndex, targetIndex);
      const pairKey = `${left}:${right}`;
      if (bondPairSet.has(pairKey)) {
        return;
      }
      bondPairSet.add(pairKey);
      bondPairs.push([left, right]);
    });
  }
  if (atoms.length === 0) {
    throw new Error(`No atoms found in PDB: ${url}`);
  }

  const center = atoms.reduce(
    (accumulator, atom) => {
      accumulator.x += atom.x;
      accumulator.y += atom.y;
      accumulator.z += atom.z;
      return accumulator;
    },
    { x: 0, y: 0, z: 0 },
  );
  center.x /= atoms.length;
  center.y /= atoms.length;
  center.z /= atoms.length;

  const bounds = atoms.reduce(
    (accumulator, atom) => {
      accumulator.minX = Math.min(accumulator.minX, atom.x);
      accumulator.maxX = Math.max(accumulator.maxX, atom.x);
      accumulator.minY = Math.min(accumulator.minY, atom.y);
      accumulator.maxY = Math.max(accumulator.maxY, atom.y);
      accumulator.minZ = Math.min(accumulator.minZ, atom.z);
      accumulator.maxZ = Math.max(accumulator.maxZ, atom.z);
      return accumulator;
    },
    {
      minX: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
      minZ: Number.POSITIVE_INFINITY,
      maxZ: Number.NEGATIVE_INFINITY,
    },
  );

  return {
    atoms,
    bonds: bondPairs,
    center,
    bounds,
    atomCount: atoms.length,
    sourceUrl: url,
  };
}
