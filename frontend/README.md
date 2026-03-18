# VEVs Frontend (Route A Structure Explorer v1)

This frontend is a single-page scientific workspace for Route A receptor-ligand complex visualization.

## Key boundaries

- Scope is `receptor-ligand complex`, not whole vesicle.
- Docking backend is currently `placeholder`.
- UI explicitly exposes `backend / scientific_validity / analysis_mode`.
- Frontend consumes files from run artifacts and does not change scientific outputs.

## Bundle export

Before running frontend, export one or more run bundles:

```bash
python scripts/export_visualization_bundle.py --run-id binding_route_a_3_13
python scripts/export_visualization_bundle.py --run-id routeA_demo_20260310
```

This creates:

- `frontend/visualization/<run_id>/work` (link to `work/runs/<run_id>`)
- `frontend/visualization/<run_id>/outputs` (link to `outputs/runs/<run_id>`)
- `frontend/visualization/<run_id>/sampled_frames.json` (symlink when source exists)
- `frontend/visualization/<run_id>/frame_pdb/*` (symlinked frame PDB files when listed)
- `frontend/visualization/<run_id>/derived/structure_roles.json` (lightweight role mapping metadata)
- `frontend/visualization/index.json`
- `frontend/public/visualization/` is cleaned and kept free of run artifacts

## Start

```bash
cd frontend
npm install
npm run dev
```

Open the dev URL and load a run id from the left panel.
