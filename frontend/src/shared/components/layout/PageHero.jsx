export default function PageHero({ eyebrow, title, description, actions = null }) {
  return (
    <header className="page-hero">
      <div className="page-hero__copy">
        {eyebrow ? <span className="page-hero__eyebrow">{eyebrow}</span> : null}
        <h1 className="page-hero__title">{title}</h1>
        {description ? <p className="page-hero__description">{description}</p> : null}
      </div>
      {actions ? <div className="page-hero__actions">{actions}</div> : null}
    </header>
  );
}
