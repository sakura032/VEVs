import { useMemo, useState } from "react";

import { RESERVED_ANALYTICS_TABS } from "../../services/artifactRegistry";
import RmsdChart from "../data/RmsdChart";
import MdLogChart from "../data/MdLogChart";
import EmptyState from "../common/EmptyState";

const PRIMARY_TABS = ["RMSD", "MD Log"];
const TAB_ORDER = [...PRIMARY_TABS, ...RESERVED_ANALYTICS_TABS];

export default function BottomAnalyticsPanel({
  rmsdState,
  mdLogState,
  onRmsdPointSelect,
}) {
  const [activeTab, setActiveTab] = useState(TAB_ORDER[0]);
  const tabContent = useMemo(() => {
    if (activeTab === "RMSD") {
      return <RmsdChart rmsdState={rmsdState} onPointSelect={onRmsdPointSelect} />;
    }
    if (activeTab === "MD Log") {
      return <MdLogChart mdLogState={mdLogState} />;
    }
    return (
      <EmptyState
        message={`Reserved for future analysis modules: ${activeTab}.`}
      />
    );
  }, [activeTab, mdLogState, onRmsdPointSelect, rmsdState]);

  return (
    <section className="bottom-analytics">
      <header>
        <h2 className="section-card__title">Analytics Panel</h2>
        <p className="section-card__subtitle">
          RMSD and MD Log are active. H-bond, Contacts, Interface Map, Endpoint FE,
          PMF are Reserved.
        </p>
      </header>
      <div className="analytics-tabs">
        {TAB_ORDER.map((tab) => {
          const isPrimary = PRIMARY_TABS.includes(tab);
          return (
            <button
              key={tab}
              type="button"
              className={`analytics-tab ${activeTab === tab ? "is-active" : ""}`}
              onClick={() => setActiveTab(tab)}
              aria-label={isPrimary ? tab : `${tab} reserved tab`}
            >
              {tab}
              {isPrimary ? "" : " (Reserved)"}
            </button>
          );
        })}
      </div>
      <div className="analytics-panel">{tabContent}</div>
    </section>
  );
}
