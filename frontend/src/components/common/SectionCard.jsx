export default function SectionCard({ title, subtitle, children }) {
  return (
    <section className="section-card">
      {(title || subtitle) && (
        <header className="section-card__header">
          {title ? <h2 className="section-card__title">{title}</h2> : null}
          {subtitle ? <p className="section-card__subtitle">{subtitle}</p> : null}
        </header>
      )}
      {children}
    </section>
  );
}
