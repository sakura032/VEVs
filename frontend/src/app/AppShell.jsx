import AppProviders from "./providers";
import { appRoutes } from "./routes";

export default function AppShell() {
  const ActivePage = appRoutes[0].element;
  return (
    <AppProviders>
      <ActivePage />
    </AppProviders>
  );
}
