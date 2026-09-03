"use client"

import React, { useEffect, useState } from "react"
import Metrics from "./metrics"
import TrendChart from "./trend_chart"
import ExceptionsTable from "./exceptions_table"
import LumpSumHighlights from "./lump_sum_highlights"
import MiniQAPanel from "./mini_qa_panel"
import AuditLog from "./audit_log"
import { ReconciliationSummary, PeriodStatus } from "../types/types"
import { fetchSummary, runReconciliation } from "../connection/api"

interface Props {
  period: string
  periods: PeriodStatus[]
  onSelectPeriod: (period: string) => void
  onNavigateToTables?: () => void
}

const Dashboard = ({ period, periods, onSelectPeriod, onNavigateToTables }: Props) => {
  const [summary, setSummary] = useState<ReconciliationSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState(false)
  const [runCount, setRunCount] = useState(0)

  useEffect(() => {
    setLoading(true)
    fetchSummary(period)
      .then(setSummary)
      .catch(() => setSummary(null))
      .finally(() => setLoading(false))
  }, [period, runCount])

  async function handleRun() {
    setRunning(true)
    try {
      const result = await runReconciliation(period)
      setSummary(result)
      setRunCount((c) => c + 1)
    } catch (err) {
      console.error("Reconciliation run failed:", err)
    } finally {
      setRunning(false)
    }
  }

  const isNotRun = summary?.status === "not_run"

  return (
    <main className="bg-[#f5f8fc] h-screen w-full p-4 flex flex-col overflow-hidden text-gray-900 antialiased">
      {/* Top Header Bar with Month Switcher */}
      <header className="flex items-center justify-between pb-3 flex-shrink-0">
        <div>
          <h1 className="font-bold text-2xl text-gray-900 tracking-tight leading-none">Dashboard</h1>
        </div>

        <div className="flex items-center gap-2">
          {/* Month Selector Dropdown */}
          <div className="relative">
            <select
              value={period}
              onChange={(e) => onSelectPeriod(e.target.value)}
              className="appearance-none bg-white border border-gray-200/90 hover:border-gray-300 py-1.5 pl-3 pr-8 rounded-xl text-xs font-semibold text-gray-800 shadow-sm cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20"
            >
              {periods.map((p) => (
                <option key={p.period} value={p.period}>
                  {p.label} 
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-400">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </div>
          </div>

          {/* Run Reconciliation Button */}
          <button
            onClick={handleRun}
            disabled={running}
            className="px-3.5 py-1.5 rounded-xl bg-gray-600 hover:bg-gray-700 active:scale-95 transition text-white text-xs font-semibold shadow-sm disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
          >
            {running ? (
              <>
                <span className="w-2.5 h-2.5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                <span>Processing...</span>
              </>
            ) : (
              "Run Reconciliation"
            )}
          </button>
        </div>
      </header>

      {/* Main Container */}
      {loading ? (
        <div className="flex-1 flex items-center justify-center bg-white rounded-2xl border border-gray-100 shadow-sm">
          <div className="flex flex-col items-center gap-2">
            <span className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
            <p className="text-gray-400 text-xs">Loading records for {period}...</p>
          </div>
        </div>
      ) : summary === null ? (
        <div className="flex-1 flex flex-col items-center justify-center bg-white rounded-2xl border border-dashed border-gray-200 p-8 text-center shadow-sm">
          <p className="text-sm text-gray-500">
            Couldn't load data for {period}. Try refreshing or check the backend connection.
          </p>
        </div>
      ) : isNotRun ? (
        /* Empty State for Unreconciled Month */
        <div className="flex-1 flex flex-col items-center justify-center bg-white rounded-2xl border border-dashed border-gray-200 p-8 text-center shadow-sm">
          <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center text-xl font-bold mb-3">
            ⏱
          </div>
          <h3 className="text-base font-bold text-gray-900">Reconciliation Pending for {period}</h3>
          <p className="text-xs text-gray-400 max-w-sm mt-1 mb-5">
            Raw ingest records ({summary?.totalRecords ?? 0} rows) are loaded into the ledger, but 3-way reconciliation has not been executed yet.
          </p>
          <button
            onClick={handleRun}
            disabled={running}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-xl text-xs font-semibold shadow-sm transition cursor-pointer"
          >
            {running ? "Processing Batch..." : "Run 3-Way Reconciliation Now"}
          </button>
        </div>
      ) : (
        /* Reconciled Active Dashboard */
        <div className="flex-1 flex flex-col gap-3 min-h-0 overflow-hidden">
          <div className="flex-shrink-0">
            <Metrics summary={summary} />
          </div>

          <div className="flex-1 grid grid-cols-12 gap-3 min-h-0 overflow-hidden">
            <section className="col-span-8 flex flex-col gap-3 min-h-0 h-full overflow-hidden">
              <div className="flex-shrink-0">
                <TrendChart currentPeriod={period} onSelectPeriod={onSelectPeriod} />
              </div>
              <div className="flex-1 min-h-0">
                <ExceptionsTable summary={summary} onViewAll={onNavigateToTables} />
              </div>
            </section>

            <aside className="col-span-4 flex flex-col gap-3 min-h-0 h-full overflow-hidden">
              <div className="flex-shrink-0">
                <LumpSumHighlights summary={summary} />
              </div>
              <div className="flex-shrink-0">
                <MiniQAPanel period={period} />
              </div>
              <div className="flex-1 min-h-0">
                <AuditLog key={runCount} period={period} />
              </div>
            </aside>
          </div>
        </div>
      )}
    </main>
  )
}

export default Dashboard