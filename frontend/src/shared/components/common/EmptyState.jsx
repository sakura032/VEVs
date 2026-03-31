export default function EmptyState({ title = null, message }) {
  return (
    <div className="empty-state" role="status">
      {title ? <h2 className="empty-state__title">{title}</h2> : null}
      <p className="empty-state__message">{message}</p>
    </div>
  );
}
