export function sortDatasetsByUpdatedAt(datasets) {
  return [...datasets].sort((left, right) =>
    String(right.updated_at ?? "").localeCompare(String(left.updated_at ?? "")),
  );
}

export function normalizeDatasetCatalog(payload) {
  const datasets = Array.isArray(payload?.datasets) ? payload.datasets : [];
  return sortDatasetsByUpdatedAt(
    datasets.filter(
      (entry) =>
        entry &&
        typeof entry.dataset_id === "string" &&
        typeof entry.structure_url === "string" &&
        typeof entry.topology_url === "string",
    ),
  );
}
