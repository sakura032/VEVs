import { useEffect, useMemo, useState } from "react";

import { loadJson } from "../../../lib/loaders/loadJson";
import { VESICLE_INDEX_URL } from "../constants/catalog";
import { normalizeDatasetCatalog } from "../services/catalog";

export function useVesicleCatalog() {
  const [catalogState, setCatalogState] = useState({
    status: "loading",
    datasets: [],
    error: null,
  });
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setCatalogState({ status: "loading", datasets: [], error: null });

    loadJson(VESICLE_INDEX_URL)
      .then((payload) => {
        if (cancelled) {
          return;
        }
        const datasets = normalizeDatasetCatalog(payload);
        setCatalogState({ status: "loaded", datasets, error: null });
        setSelectedDatasetId((previous) => {
          if (previous && datasets.some((entry) => entry.dataset_id === previous)) {
            return previous;
          }
          return datasets[0]?.dataset_id ?? null;
        });
      })
      .catch((error) => {
        if (cancelled) {
          return;
        }
        if (error?.status === 404) {
          setCatalogState({ status: "loaded", datasets: [], error: null });
          setSelectedDatasetId(null);
          return;
        }
        setCatalogState({ status: "error", datasets: [], error });
        setSelectedDatasetId(null);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedDataset = useMemo(
    () =>
      catalogState.datasets.find((entry) => entry.dataset_id === selectedDatasetId) ?? null,
    [catalogState.datasets, selectedDatasetId],
  );

  return {
    catalogState,
    datasets: catalogState.datasets,
    selectedDataset,
    selectedDatasetId,
    setSelectedDatasetId,
  };
}
