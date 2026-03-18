import fs from "node:fs";
import path from "node:path";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const visualizationFsRoot = path.resolve(__dirname, "visualization");

const contentTypeMap = {
  ".json": "application/json; charset=utf-8",
  ".csv": "text/csv; charset=utf-8",
  ".pdb": "chemical/x-pdb; charset=utf-8",
  ".md": "text/markdown; charset=utf-8",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
};

function createVisualizationMiddleware() {
  return (request, response, next) => {
    const requestPath = new URL(request.url, "http://localhost").pathname;
    if (!requestPath.startsWith("/visualization")) {
      next();
      return;
    }

    const relativePath = requestPath.replace(/^\/visualization\/?/, "");
    const safeResolvedPath = path.resolve(visualizationFsRoot, relativePath);
    if (!safeResolvedPath.startsWith(visualizationFsRoot)) {
      response.statusCode = 403;
      response.end("Forbidden");
      return;
    }

    let targetPath = safeResolvedPath;
    if (fs.existsSync(targetPath) && fs.statSync(targetPath).isDirectory()) {
      targetPath = path.join(targetPath, "index.json");
    }

    if (!fs.existsSync(targetPath) || !fs.statSync(targetPath).isFile()) {
      response.statusCode = 404;
      response.end("Not Found");
      return;
    }

    const fileExtension = path.extname(targetPath).toLowerCase();
    const contentType = contentTypeMap[fileExtension] || "application/octet-stream";
    response.setHeader("Content-Type", contentType);
    fs.createReadStream(targetPath).pipe(response);
  };
}

function visualizationFsPlugin() {
  const middleware = createVisualizationMiddleware();
  return {
    name: "vevs-visualization-fs",
    configureServer(server) {
      server.middlewares.use(middleware);
    },
    configurePreviewServer(server) {
      server.middlewares.use(middleware);
    },
  };
}

export default defineConfig({
  plugins: [react(), visualizationFsPlugin()],
});
