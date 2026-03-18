import SectionCard from "../common/SectionCard";
import EmptyState from "../common/EmptyState";
import LoadingState from "../common/LoadingState";

function formatNumber(value) {
  if (!Number.isFinite(Number(value))) {
    return "N/A";
  }
  return Number(value).toFixed(3);
}

export default function PoseTable({
  poseState,
  selectedPoseId,
  onPoseSelect,
  embedded = false,
}) {
  const content = (
    <>
      {poseState.status === "loading" ? (
        <LoadingState message="Loading poses.csv..." />
      ) : null}
      {poseState.status === "error" ? (
        <EmptyState message="Failed to load poses.csv for this run." />
      ) : null}
      {poseState.status === "loaded" && poseState.rows.length === 0 ? (
        <EmptyState message="No pose rows found." />
      ) : null}
      {poseState.status === "loaded" && poseState.rows.length > 0 ? (
        <div className="pose-table-wrapper">
          <table className="pose-table">
            <thead>
              <tr>
                <th>pose_id</th>
                <th>score</th>
                <th>rmsd</th>
                <th>backend</th>
                <th>scientific_validity</th>
              </tr>
            </thead>
            <tbody>
              {poseState.rows.map((row) => {
                const isSelected = Number(selectedPoseId) === Number(row.pose_id);
                return (
                  <tr
                    key={`${row.pose_id}-${row.rowIndex}`}
                    className={isSelected ? "is-selected" : ""}
                    onClick={() => onPoseSelect(row.pose_id)}
                  >
                    <td className="mono-text">{row.pose_id}</td>
                    <td className="mono-text">{formatNumber(row.score)}</td>
                    <td className="mono-text">{formatNumber(row.rmsd)}</td>
                    <td className="mono-text">{row.backend ?? "N/A"}</td>
                    <td className="mono-text">
                      {row.scientific_validity ?? "N/A"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : null}
    </>
  );

  if (embedded) {
    return content;
  }

  return (
    <SectionCard
      title="Pose Table"
      subtitle="Docking pose ranking (placeholder semantics, not physical affinity)"
    >
      {content}
    </SectionCard>
  );
}
