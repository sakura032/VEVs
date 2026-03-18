import ReservedModuleCard from "../common/ReservedModuleCard";
import AccordionGroup from "../common/AccordionGroup";
import {
  RESERVED_FUTURE_MODULES,
  STRUCTURE_STAGES,
} from "../../services/artifactRegistry";

export default function LeftControlPanel({
  availableRunIds,
  pendingRunId,
  onPendingRunIdChange,
  onLoadRun,
  onRefreshRuns,
  selectedStage,
  onStageSelect,
  stageAvailability,
  displayMode,
  onDisplayModeChange,
  visibilityFilter,
  onVisibilityFilterChange,
  onResetCamera,
}) {
  const accordionItems = [
    {
      id: "run-selector",
      title: "Run Selector",
      subtitle: "Load a run_id visualization bundle",
      content: (
        <div className="panel-stack">
          <div className="control-row">
            <input
              className="control-input mono-text"
              list="run-id-options"
              value={pendingRunId}
              onChange={(event) => onPendingRunIdChange(event.target.value)}
              placeholder="binding_route_a_3_13"
            />
            <datalist id="run-id-options">
              {availableRunIds.map((runEntry) => (
                <option key={runEntry.run_id} value={runEntry.run_id} />
              ))}
            </datalist>
            <button
              type="button"
              className="control-button"
              onClick={() => onLoadRun(pendingRunId)}
              disabled={!pendingRunId}
            >
              Load
            </button>
          </div>
          <div className="control-row">
            <select
              className="control-select mono-text"
              value={pendingRunId}
              onChange={(event) => onPendingRunIdChange(event.target.value)}
            >
              <option value="">-- Select discovered run_id --</option>
              {availableRunIds.map((runEntry) => (
                <option key={runEntry.run_id} value={runEntry.run_id}>
                  {runEntry.run_id}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="control-button"
              onClick={onRefreshRuns}
            >
              Refresh Runs
            </button>
          </div>
        </div>
      ),
    },
    {
      id: "stage-selector",
      title: "Stage Selector",
      subtitle: "Route A structural stages",
      content: (
        <ul className="stage-list">
          {STRUCTURE_STAGES.map((stage) => {
            const isAvailable = Boolean(stageAvailability?.[stage.id]);
            const isDisabled = !isAvailable;
            return (
              <li key={stage.id}>
                <button
                  type="button"
                  className={[
                    "stage-item-button",
                    selectedStage === stage.id ? "stage-item-button--active" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  disabled={isDisabled}
                  onClick={() => onStageSelect(stage.id)}
                >
                  <span className="mono-text">{stage.label}</span>
                  <span>{isAvailable ? "Ready" : "Missing"}</span>
                </button>
              </li>
            );
          })}
        </ul>
      ),
    },
    {
      id: "display-controls",
      title: "Display Controls",
      subtitle: "MainScene rendering toggles",
      content: (
        <div className="panel-stack">
          <div className="control-row">
            <label htmlFor="display-mode">Mode</label>
            <select
              id="display-mode"
              className="control-select"
              value={displayMode}
              onChange={(event) => onDisplayModeChange(event.target.value)}
            >
              <option value="cartoon">cartoon (chain trace)</option>
              <option value="sticks">sticks (atom + bond)</option>
              <option value="spheres">spheres (vdw)</option>
            </select>
          </div>
          <div className="control-row">
            <label htmlFor="visibility-filter">Filter</label>
            <select
              id="visibility-filter"
              className="control-select"
              value={visibilityFilter}
              onChange={(event) => onVisibilityFilterChange(event.target.value)}
            >
              <option value="all">all</option>
              <option value="ligand">show ligand only</option>
              <option value="receptor">show receptor only</option>
            </select>
          </div>
          <button type="button" className="control-button" onClick={onResetCamera}>
            reset camera
          </button>
          <button type="button" className="control-button" disabled>
            show waters nearby (Reserved)
          </button>
        </div>
      ),
    },
    {
      id: "future-modules",
      title: "Future Modules",
      subtitle: "Reserved for next phases",
      content: (
        <div className="panel-stack">
          {RESERVED_FUTURE_MODULES.map((moduleName) => (
            <ReservedModuleCard key={moduleName} name={moduleName} note="Reserved" />
          ))}
        </div>
      ),
    },
  ];

  return (
    <aside className="left-control-panel">
      <AccordionGroup
        idPrefix="left"
        items={accordionItems}
        defaultOpenIds={["run-selector", "stage-selector"]}
      />
    </aside>
  );
}
