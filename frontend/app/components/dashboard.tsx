import React, { useState, useEffect } from "react";
import Metrics from "./metrics";
import MatchBreakdown from "./match_breakdown";
import LumpSumHighlights from "./lump_sum_highlights";
import ExceptionsTable from "./exceptions_table";
import { ReconciliationSummary } from "../types/types";
import { fetchSummary, runReconciliation } from "../connection/api";

interface Props {
  period: string;
}

const Dashboard = ({ period }: Props) => {
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);

  useEffect(() => {
    setLoading(true);
    fetchSummary(period)
      .then(setSummary)
      .finally(() => setLoading(false));
  }, [period]);

  async function handleRun() {
    setRunning(true);
    try {
      const result = await runReconciliation(period);
      setSummary(result);
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="bg-[#f5f9fc] h-full w-full overflow-y-auto">
      <div className="flex items-center justify-between mx-8 pt-6">
        <h1 className="font-semibold text-3xl">Dashboard</h1>
        <button
          onClick={handleRun}
          disabled={running}
          className="px-4 py-2 rounded-lg bg-gray-900 text-white text-sm disabled:opacity-50"
        >
          {running ? "Running..." : "Run reconciliation"}
        </button>
      </div>

      {loading || !summary ? (
        <div className="mx-8 mt-6 text-gray-400 text-sm">
          {summary === null && !loading
            ? "No reconciliation has been run for this period yet."
            : "Loading..."}
        </div>
      ) : (
        <>
          <Metrics summary={summary} />
          <MatchBreakdown summary={summary} />
          <LumpSumHighlights summary={summary} />
          <ExceptionsTable summary={summary} />
        </>
      )}
    </div>
  );
};

export default Dashboard;
