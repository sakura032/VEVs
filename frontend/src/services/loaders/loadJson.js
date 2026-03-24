export async function loadJson(url) {
  const response = await fetch(url);
  if (!response.ok) {
    const error = new Error(`Failed to load JSON: ${url} (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return response.json();
}
