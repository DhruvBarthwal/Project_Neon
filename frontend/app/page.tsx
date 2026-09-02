"use client";

import { useEffect, useState } from "react";
import Sidebar, { ViewType } from "./components/sidebar";
import Dashboard from "./components/dashboard";
import TablesView from "./components/tables_view";
import QAPanel from "./components/qa_panel";
import { PeriodStatus, ReconciliationSummary } from "./types/types";
import { fetchPeriods, fetchSummary } from "./connection/api";

export default function Home() {
  const [periods, setPeriods] = useState<PeriodStatus[]>([]);
  const [activePeriod, setActivePeriod] = useState<string>("");
  const [view, setView] = useState<ViewType>("dashboard");
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);

  // 1. Fetch available months from backend
  useEffect(() => {
    fetchPeriods().then((fetchedPeriods) => {
      setPeriods(fetchedPeriods);
      if (fetchedPeriods.length > 0) {
        // Default to the latest completed month or the first month in list
        const defaultPeriod =
          fetchedPeriods.find((x) => x.status === "done") || fetchedPeriods[0];
        setActivePeriod(defaultPeriod.period);
      }
    });
  }, []);

  // 2. Fetch summary whenever activePeriod changes
  useEffect(() => {
    if (activePeriod) {
      fetchSummary(activePeriod)
        .then(setSummary)
        .catch(() => setSummary(null));
    }
  }, [activePeriod]);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#f5f8fc]">
      {/* Sidebar with Navigation */}
      <Sidebar view={view} onSelect={setView} />

      <div className="flex flex-col h-full w-full overflow-hidden">
        {/* 1. Month-Wise Dashboard */}
        {activePeriod && view === "dashboard" && (
          <Dashboard
            period={activePeriod}
            periods={periods}
            onSelectPeriod={setActivePeriod}
            onNavigateToTables={() => setView("tables")}
          />
        )}

        {/* 2. Month-Wise Multi-Table & Ledger View */}
        {activePeriod && view === "tables" && (
          <TablesView
            period={activePeriod}
            summary={summary}
            onBack={() => setView("dashboard")}
          />
        )}

        {/* 3. Month-Wise Q&A Assistant */}
        {activePeriod && view === "qa" && <QAPanel period={activePeriod} />}
      </div>
    </div>
  );
}
