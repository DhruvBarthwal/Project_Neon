"use client"

import { useEffect, useState } from "react"
import Sidebar from "./components/sidebar"
import Dashboard from "./components/dashboard"
import Navbar from "./components/navbar"
import QAPanel from "./components/qa_panel"
import { PeriodStatus } from "./types/types"
import { fetchPeriods } from "./connection/api"

export default function Home() {
  const [periods, setPeriods] = useState<PeriodStatus[]>([])
  const [activePeriod, setActivePeriod] = useState<string>("")
  const [view, setView] = useState<"dashboard" | "qa">("dashboard")

  useEffect(() => {
    fetchPeriods().then((p) => {
      setPeriods(p)
      const done = p.find((x) => x.status === "done")
      if (done) setActivePeriod(done.period)
    })
  }, [])

  return (
    <div className="flex h-screen w-full">
      <Sidebar view={view} onSelect={setView} />
      <div className="flex flex-col h-full w-full">
        <Navbar periods={periods} activePeriod={activePeriod} onSelect={setActivePeriod} />
        {activePeriod && view === "dashboard" && <Dashboard period={activePeriod} />}
        {activePeriod && view === "qa" && <QAPanel period={activePeriod} />}
      </div>
    </div>
  )
}