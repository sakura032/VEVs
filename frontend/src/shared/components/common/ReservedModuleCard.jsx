import Badge from "./Badge";

export default function ReservedModuleCard({ name, note = "Coming later" }) {
  return (
    <div className="reserved-module-card" role="note" aria-label={`${name} reserved`}>
      <span className="reserved-module-card__name">{name}</span>
      <Badge label="Status" value={note} variant="reserved" />
    </div>
  );
}
