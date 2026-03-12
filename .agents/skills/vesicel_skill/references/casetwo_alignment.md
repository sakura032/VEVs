# casetwo.md alignment reference

The skill must stay aligned with the architecture and phase plan in `casetwo.md`.

## Non-negotiable architecture
1. Structure Preparation
2. MD Execution
3. Scientific Workflow
4. Trajectory / Free-Energy Analysis

## Non-negotiable role split
- `BindingWorkflow` handles orchestration.
- `AllAtomSimulation` is the AA-MD execution core.
- Analysis consumes real outputs and must not fabricate physics.

## Phase order
- Phase 0: freeze interfaces and contracts
- Phase 1: Route A minimum runnable loop
- Phase 2: membrane-ready platformization
- Phase 3: Route B membrane workflow
- Phase 4: umbrella sampling and PMF

## Route A to Route B transition requirement
All Route A code should preserve future compatibility with:
- `has_membrane`
- `MembraneConfig`
- solution / membrane protocol branching
- membrane-aware analysis expansion

## Scientific honesty
Placeholder implementations may exist, but they must be clearly marked and cannot be described as publishable physical evidence.
