import { useMemo, useState } from "react";

function normalizeDefaultOpen(defaultOpenIds) {
  if (!Array.isArray(defaultOpenIds)) {
    return [];
  }
  return defaultOpenIds.filter((value) => typeof value === "string");
}

export default function AccordionGroup({
  idPrefix = "accordion",
  items,
  defaultOpenIds = [],
  className = "",
}) {
  const normalizedDefault = useMemo(
    () => normalizeDefaultOpen(defaultOpenIds),
    [defaultOpenIds],
  );
  const [openIdSet, setOpenIdSet] = useState(() => new Set(normalizedDefault));

  return (
    <div className={`accordion-group ${className}`.trim()}>
      {items.map((item) => {
        const itemId = String(item.id);
        const triggerId = `${idPrefix}-${itemId}-trigger`;
        const panelId = `${idPrefix}-${itemId}-panel`;
        const isOpen = openIdSet.has(itemId);
        return (
          <section
            key={itemId}
            className={`accordion-item ${isOpen ? "accordion-item--open" : ""}`}
          >
            <h2 className="accordion-item__heading">
              <button
                id={triggerId}
                type="button"
                className="accordion-item__trigger"
                aria-expanded={isOpen}
                aria-controls={panelId}
                onClick={() => {
                  setOpenIdSet((previousSet) => {
                    const nextSet = new Set(previousSet);
                    if (nextSet.has(itemId)) {
                      nextSet.delete(itemId);
                    } else {
                      nextSet.add(itemId);
                    }
                    return nextSet;
                  });
                }}
              >
                <span>{item.title}</span>
                <span className="accordion-item__icon" aria-hidden="true">
                  {isOpen ? "-" : "+"}
                </span>
              </button>
            </h2>
            {item.subtitle ? (
              <p className="accordion-item__subtitle">{item.subtitle}</p>
            ) : null}
            <div
              id={panelId}
              role="region"
              aria-labelledby={triggerId}
              className="accordion-item__panel"
              hidden={!isOpen}
            >
              {item.content}
            </div>
          </section>
        );
      })}
    </div>
  );
}
