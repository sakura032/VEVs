const DEFAULT_VARIANT = "info";

export default function Badge({ label, value, variant = DEFAULT_VARIANT }) {
  return (
    <span className={`badge badge--${variant}`}>
      <strong>{label}:</strong> <span>{value ?? "N/A"}</span>
    </span>
  );
}
