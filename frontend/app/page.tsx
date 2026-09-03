"use client";

import { useEffect, useState } from "react";
import Sidebar, { ViewType } from "./components/sidebar";
import Dashboard from "./components/dashboard";
import TablesView, { TableType } from "./components/tables_view";
import QAPanel from "./components/qa_panel";
import { PeriodStatus, ReconciliationSummary } from "./types/types";
import { fetchPeriods, fetchSummary } from "./connection/api";

export default function Home() {
  const [periods, setPeriods] = useState<PeriodStatus[]>([]);
  const [activePeriod, setActivePeriod] = useState<string>("");
  const [view, setView] = useState<ViewType>("dashboard");
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [activeTableType, setActiveTableType] = useState<TableType>("exceptions");
  const [refreshKey, setRefreshKey] = useState<number>(0);

  useEffect(() => {
    fetchPeriods().then((fetchedPeriods) => {
      setPeriods(fetchedPeriods);
      if (fetchedPeriods.length > 0) {
        const defaultPeriod =
          fetchedPeriods.find((x) => x.status === "done") || fetchedPeriods[0];
        setActivePeriod(defaultPeriod.period);
      }
    });
  }, []);

  useEffect(() => {
    if (activePeriod) {
      fetchSummary(activePeriod)
        .then(setSummary)
        .catch(() => setSummary(null));
    }
  }, [activePeriod, refreshKey]);

  const handleSelectView = (newView: ViewType) => {
    if (newView === "dashboard") {
      setRefreshKey((prev) => prev + 1);
    }
    setView(newView);
  };

  const handleDeepLinkNavigation = (targetPeriod: string, targetTable?: string) => {
    if (targetPeriod) setActivePeriod(targetPeriod);
    if (targetTable) setActiveTableType(targetTable as TableType);
    setView("tables");
  };

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#f5f8fc]">
      <Sidebar view={view} onSelect={handleSelectView} />

      <div className="flex flex-col h-full w-full overflow-hidden">
        {/* 1. Dashboard View */}
        {activePeriod && view === "dashboard" && (
          <Dashboard
            key={`dashboard-${activePeriod}-${refreshKey}`}
            period={activePeriod}
            periods={periods}
            onSelectPeriod={setActivePeriod}
            onNavigateToTables={() => {
              setActiveTableType("exceptions");
              setView("tables");
            }}
          />
        )}

        {/* 2. Multi-Table View */}
        {activePeriod && view === "tables" && (
          <TablesView
            period={activePeriod}
            periods={periods}
            summary={summary}
            initialTable={activeTableType}
            onSelectPeriod={setActivePeriod}
            onBack={() => setView("dashboard")}
          />
        )}

        {/* 3. Audit Assistant (Persistent state via hidden class) */}
        {activePeriod && (
          <div className={`h-full w-full ${view === "qa" ? "flex" : "hidden"}`}>
            <QAPanel
              period={activePeriod}
              periods={periods}
              onNavigate={handleDeepLinkNavigation}
            />
          </div>
        )}
      </div>
    </div>
  );
}