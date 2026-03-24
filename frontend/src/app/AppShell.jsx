import { useEffect, useMemo, useState } from "react";

import AppProviders from "./providers";
import { appRoutes } from "./routes";

function resolveRouteIdFromHash() {
  const rawHash = window.location.hash.replace(/^#/, "").trim();
  return appRoutes.some((route) => route.id === rawHash) ? rawHash : appRoutes[0].id;
}

export default function AppShell() {
  const [activeRouteId, setActiveRouteId] = useState(() => resolveRouteIdFromHash());

  useEffect(() => {
    const handleHashChange = () => {
      setActiveRouteId(resolveRouteIdFromHash());
    };
    window.addEventListener("hashchange", handleHashChange);
    return () => {
      window.removeEventListener("hashchange", handleHashChange);
    };
  }, []);

  const activeRoute = useMemo(
    () => appRoutes.find((route) => route.id === activeRouteId) ?? appRoutes[0],
    [activeRouteId],
  );
  const ActivePage = activeRoute.element;

  return (
    <AppProviders>
      <nav className="app-route-switcher" aria-label="Application pages">
        {appRoutes.map((route) => (
          <button
            key={route.id}
            type="button"
            className={[
              "app-route-switcher__button",
              route.id === activeRoute.id ? "is-active" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            onClick={() => {
              window.location.hash = route.id;
              setActiveRouteId(route.id);
            }}
          >
            {route.label}
          </button>
        ))}
      </nav>
      <ActivePage />
    </AppProviders>
  );
}
