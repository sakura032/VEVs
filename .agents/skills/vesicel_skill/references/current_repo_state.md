# Current repository alignment reference

This reference summarizes the current repository state that the skill should respect.

## Observed repository structure
- `src/configs/`
- `src/interfaces/`
- `src/models/workflows/`
- `src/models/all_atom/`
- `src/models/docking/`
- `src/utils/`
- `src/analysis/`
- `scripts/run_binding_route_a.py`
- `scripts/run_minimal_openmm_validation.py`
- `tests/`
- `work/runs/<run_id>/...`
- `outputs/runs/<run_id>/...`

## Current practical meaning
- Route A is the current main runnable path.
- Docking is a stage inside binding workflow, not the full workflow.
- `work/` stores process artifacts.
- `outputs/` stores result artifacts.
- Smoke tests are regression protection and should be kept unless clearly obsolete.

## Current artifact organization
- `work/runs/<run_id>/preprocessed/`
- `work/runs/<run_id>/assembled/`
- `work/runs/<run_id>/md/`
- `outputs/runs/<run_id>/docking/`
- `outputs/runs/<run_id>/analysis/`
- `outputs/runs/<run_id>/metadata/`
- `outputs/runs/<run_id>/logs/`
- `outputs/runs/<run_id>/reports/`
