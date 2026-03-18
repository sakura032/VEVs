import { Color } from "three";

export const ROLE_ORDER = ["receptor", "ligand", "water", "unresolved"];

export function cssColor(variableName, fallback) {
  if (typeof window === "undefined") {
    return fallback;
  }
  const value = window
    .getComputedStyle(document.documentElement)
    .getPropertyValue(variableName)
    .trim();
  return value || fallback;
}

export function buildRoleColorMap() {
  return {
    receptor: new Color(cssColor("--accent-receptor", "#4f6d8a")),
    ligand: new Color(cssColor("--accent-ligand", "#2a927a")),
    water: new Color(cssColor("--accent-water", "#5f7fa0")),
    unresolved: new Color(cssColor("--accent-unresolved", "#c84b31")),
  };
}

export function buildElementColorMap() {
  return {
    C: new Color(cssColor("--element-carbon", "#6f7e8e")),
    N: new Color(cssColor("--element-nitrogen", "#2f6fed")),
    O: new Color(cssColor("--element-oxygen", "#c84b31")),
    S: new Color(cssColor("--element-sulfur", "#c99000")),
    P: new Color(cssColor("--element-phosphorus", "#ad6f17")),
    H: new Color(cssColor("--element-hydrogen", "#d7dee8")),
    FE: new Color(cssColor("--element-metal", "#9b6ad4")),
    ZN: new Color(cssColor("--element-metal", "#9b6ad4")),
    MG: new Color(cssColor("--element-metal", "#9b6ad4")),
    CA: new Color(cssColor("--element-metal", "#9b6ad4")),
  };
}

export function blendColor(baseColor, overlayColor, overlayWeight = 0.35) {
  const safeWeight = Math.min(Math.max(overlayWeight, 0), 1);
  return new Color(
    baseColor.r * (1 - safeWeight) + overlayColor.r * safeWeight,
    baseColor.g * (1 - safeWeight) + overlayColor.g * safeWeight,
    baseColor.b * (1 - safeWeight) + overlayColor.b * safeWeight,
  );
}

export function getElementColor(element, elementColorMap) {
  return elementColorMap[element] ?? elementColorMap.C;
}

export function getRoleFromFallback(atom) {
  if (atom.category === "water") {
    return "water";
  }
  if (atom.category === "ligand") {
    return "ligand";
  }
  return "receptor";
}

export function mergeStructureRoles(structure, rolePayload) {
  if (!structure) {
    return null;
  }
  const roleLookup =
    rolePayload && rolePayload.atom_roles && typeof rolePayload.atom_roles === "object"
      ? rolePayload.atom_roles
      : {};
  const resolutionStatus =
    rolePayload && typeof rolePayload.resolution_status === "string"
      ? rolePayload.resolution_status
      : "missing";
  const resolutionNotes =
    rolePayload && Array.isArray(rolePayload.resolution_notes)
      ? rolePayload.resolution_notes.filter((note) => typeof note === "string")
      : [];
  const roleCounts = {
    receptor: 0,
    ligand: 0,
    water: 0,
    unresolved: 0,
  };
  const atoms = structure.atoms.map((atom) => {
    const mappedRole = roleLookup[atom.atomKey];
    const fallbackRole = getRoleFromFallback(atom);
    const role =
      mappedRole === "receptor" ||
      mappedRole === "ligand" ||
      mappedRole === "water" ||
      mappedRole === "unresolved"
        ? mappedRole
        : fallbackRole;
    if (roleCounts[role] !== undefined) {
      roleCounts[role] += 1;
    }
    return {
      ...atom,
      role,
      roleConfidence:
        mappedRole === undefined
          ? "fallback"
          : mappedRole === "unresolved"
            ? "conflict"
            : "mapped",
    };
  });
  return {
    ...structure,
    atoms,
    roleCounts,
    roleResolution: {
      status: resolutionStatus,
      notes: resolutionNotes,
      source: rolePayload?.source ?? null,
    },
  };
}

export function shouldIncludeAtomByFilter(atom, visibilityFilter) {
  if (visibilityFilter === "all") {
    return atom.role !== "water";
  }
  if (visibilityFilter === "receptor") {
    return atom.role === "receptor";
  }
  if (visibilityFilter === "ligand") {
    return atom.role === "ligand";
  }
  return atom.role !== "water";
}

export function clampValue(value, minValue, maxValue) {
  return Math.max(minValue, Math.min(maxValue, value));
}

export function formatRoleCounts(roleCounts) {
  if (!roleCounts) {
    return "N/A";
  }
  return ROLE_ORDER.map((role) => `${role}:${roleCounts[role] ?? 0}`).join(" ");
}

