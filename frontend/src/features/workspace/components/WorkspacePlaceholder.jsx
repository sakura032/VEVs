import ReservedModuleCard from "../../../shared/components/common/ReservedModuleCard";
import SectionCard from "../../../shared/components/common/SectionCard";
import PageHero from "../../../shared/components/layout/PageHero";
import { RESERVED_MODULES } from "../constants/modules";

export default function WorkspacePlaceholder() {
  return (
    <div className="app-shell">
      <PageHero
        eyebrow="Workspace"
        title="Project Workspace"
        description="This page replaces the retired explorer route and now acts as a clean entry point for future modules. The live vesicle viewer stays isolated in its own feature folder, and new capabilities will be added here without reintroducing cross-feature coupling."
      />

      <main className="workspace-placeholder-grid">
        <SectionCard
          title="Current role"
          subtitle="A stable placeholder route that keeps the two-page shell while the next modules are designed."
        >
          <div className="panel-stack">
            <p className="workspace-copy">
              The frontend is now organized around explicit feature boundaries. This route no longer
              loads legacy run bundles, metrics panels, or retired artifact types.
            </p>
            <p className="workspace-copy">
              When a new workflow is ready, it should land as its own feature module and page
              rather than being mixed into the vesicle explorer.
            </p>
          </div>
        </SectionCard>

        <SectionCard
          title="Module map"
          subtitle="Planned expansion points inside the cleaned frontend shell."
        >
          <div className="panel-stack">
            {RESERVED_MODULES.map((module) => (
              <div key={module.name} className="workspace-module-row">
                <ReservedModuleCard name={module.name} note={module.note} />
                <p className="workspace-copy">{module.description}</p>
              </div>
            ))}
          </div>
        </SectionCard>

        <SectionCard
          title="Architecture rules"
          subtitle="New frontend work should follow these boundaries."
        >
          <ul className="workspace-rules">
            <li>Route pages assemble features, but do not own domain parsing logic.</li>
            <li>Feature folders contain their own hooks, services, constants, and components.</li>
            <li>Shared and lib folders stay generic and must not absorb vesicle-only behavior.</li>
          </ul>
        </SectionCard>
      </main>
    </div>
  );
}
