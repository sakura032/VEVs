import SectionCard from "../common/SectionCard";
import EmptyState from "../common/EmptyState";

export default function ReportViewer({ markdown, embedded = false }) {
  const content = (
    <>
      {markdown ? (
        <div className="report-viewer">
          <pre>{markdown}</pre>
        </div>
      ) : (
        <EmptyState message="route_a_summary.md not available for this run." />
      )}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <SectionCard title="Report Viewer" subtitle="reports/route_a_summary.md">
      {content}
    </SectionCard>
  );
}
