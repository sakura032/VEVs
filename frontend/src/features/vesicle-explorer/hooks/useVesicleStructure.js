import { useEffect, useState } from "react";

import { loadGro } from "../../../lib/loaders/loadGro";

export function useVesicleStructure(selectedDataset) {
  const [structureState, setStructureState] = useState({
    status: "idle",
    structure: null,
    error: null,
  });

  useEffect(() => {
    if (!selectedDataset) {
      setStructureState({ status: "idle", structure: null, error: null });
      return;
    }

    let cancelled = false;
    setStructureState({ status: "loading", structure: null, error: null });

    loadGro(selectedDataset.structure_url)
      .then((structure) => {
        if (cancelled) {
          return;
        }
        setStructureState({ status: "loaded", structure, error: null });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        setStructureState({ status: "error", structure: null, error });
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDataset]);

  return structureState;
}
