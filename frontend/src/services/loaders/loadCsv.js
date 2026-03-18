function splitCsvRow(row) {
  const cells = [];
  let cursor = "";
  let inQuotes = false;
  for (let index = 0; index < row.length; index += 1) {
    const character = row[index];
    if (character === '"') {
      const nextCharacter = row[index + 1];
      if (inQuotes && nextCharacter === '"') {
        cursor += '"';
        index += 1;
      } else {
        inQuotes = !inQuotes;
      }
      continue;
    }
    if (character === "," && !inQuotes) {
      cells.push(cursor);
      cursor = "";
      continue;
    }
    cursor += character;
  }
  cells.push(cursor);
  return cells;
}

function normalizeHeader(rawHeader) {
  const cleanedHeader = rawHeader.replace(/^#/, "").trim().replaceAll(" ", "_");
  return cleanedHeader
    .replaceAll("(", "")
    .replaceAll(")", "")
    .replaceAll("/", "_")
    .replaceAll("-", "_")
    .replaceAll(".", "_");
}

function normalizeValue(rawValue) {
  const value = rawValue.trim();
  if (value.length === 0) {
    return "";
  }
  const numeric = Number(value);
  if (!Number.isNaN(numeric) && Number.isFinite(numeric)) {
    return numeric;
  }
  return value;
}

export async function loadCsv(url) {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Failed to load CSV: ${url} (${response.status})`);
  }
  const text = await response.text();
  const rawLines = text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
  if (rawLines.length === 0) {
    return [];
  }

  const headers = splitCsvRow(rawLines[0]).map((header) =>
    normalizeHeader(header),
  );
  return rawLines.slice(1).map((line) => {
    const values = splitCsvRow(line);
    const row = {};
    headers.forEach((header, headerIndex) => {
      row[header] = normalizeValue(values[headerIndex] ?? "");
    });
    return row;
  });
}
