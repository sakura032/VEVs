export default function LoadingState({ message = "Loading..." }) {
  return (
    <div className="loading-state" role="status" aria-live="polite">
      <span className="loading-state__pulse" aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}
