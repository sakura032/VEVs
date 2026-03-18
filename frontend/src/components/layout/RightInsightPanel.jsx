import ReservedModuleCard from "../common/ReservedModuleCard";
import AccordionGroup from "../common/AccordionGroup";
import PoseTable from "../data/PoseTable";
import MetricsCards from "../data/MetricsCards";
import ProvenancePanel from "../data/ProvenancePanel";
import ReportViewer from "../data/ReportViewer";

export default function RightInsightPanel({
  currentObject,
  poseState,
  selectedPoseId,
  onPoseSelect,
  metricsState,
  manifest,
  preprocessReport,
  mdPdbfixerReport,
  routeSummary,
}) {
  const accordionItems = [
    {
      id: "object-overview",
      title: "Current Object Overview",
      subtitle: "Current stage, source, and boundary context",
      content: (
        <dl className="kv-list">
          <div className="kv-item">
            <dt>stage</dt>
            <dd className="mono-text">{currentObject.stage}</dd>
          </div>
          <div className="kv-item">
            <dt>pose</dt>
            <dd className="mono-text">{currentObject.poseLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>frame</dt>
            <dd className="mono-text">{currentObject.frameLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>render mode</dt>
            <dd className="mono-text">{currentObject.renderModeLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>counts by role</dt>
            <dd className="mono-text">{currentObject.roleCountsLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>role resolution</dt>
            <dd className="mono-text">{currentObject.roleResolutionStatus}</dd>
          </div>
          <div className="kv-item">
            <dt>role note</dt>
            <dd>{currentObject.roleResolutionNote}</dd>
          </div>
          <div className="kv-item">
            <dt>atom count</dt>
            <dd className="mono-text">{currentObject.atomCountLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>performance mode</dt>
            <dd>{currentObject.performanceNote}</dd>
          </div>
          <div className="kv-item">
            <dt>source file</dt>
            <dd className="mono-text">{currentObject.sourceLabel}</dd>
          </div>
          <div className="kv-item">
            <dt>quick notes</dt>
            <dd>{currentObject.quickNotes}</dd>
          </div>
        </dl>
      ),
    },
    {
      id: "pose-table",
      title: "Pose Table",
      subtitle: "Docking pose ranking (placeholder semantics, not physical affinity)",
      content: (
        <PoseTable
          poseState={poseState}
          selectedPoseId={selectedPoseId}
          onPoseSelect={onPoseSelect}
          embedded
        />
      ),
    },
    {
      id: "metrics-cards",
      title: "Metrics Cards",
      subtitle: "analysis/binding/metrics.json",
      content: <MetricsCards metricsState={metricsState} embedded />,
    },
    {
      id: "provenance",
      title: "Provenance & Boundary",
      subtitle: "Boundary-first disclosure for backend and validity semantics",
      content: (
        <ProvenancePanel
          manifest={manifest}
          preprocessReport={preprocessReport}
          mdPdbfixerReport={mdPdbfixerReport}
          embedded
        />
      ),
    },
    {
      id: "report-viewer",
      title: "Report Viewer",
      subtitle: "reports/route_a_summary.md",
      content: <ReportViewer markdown={routeSummary} embedded />,
    },
    {
      id: "roadmap-boundary",
      title: "Roadmap Boundary",
      subtitle: "Scope honesty for v1",
      content: (
        <ReservedModuleCard name="Whole Vesicle Explorer" note="Coming later" />
      ),
    },
  ];

  return (
    <aside className="right-insight-panel">
      <AccordionGroup
        idPrefix="right"
        items={accordionItems}
        defaultOpenIds={[
          "object-overview",
          "pose-table",
          "metrics-cards",
          "provenance",
        ]}
      />
    </aside>
  );
}
