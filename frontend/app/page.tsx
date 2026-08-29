"use client";
import { useEffect, useState } from "react";
import Sidebar from "./components/sidebar";
import Dashboard from "./components/dashboard";
import Navbar from "./components/navbar";
import { PeriodStatus } from "./types/types";
import { fetchPeriods } from "./connection/api";

export default function Home() {
  const [periods, setPeriods] = useState<PeriodStatus[]>([]);
  const [activePeriod, setActivePeriod] = useState<string>("");

  useEffect(() => {
    fetchPeriods().then((p) => {
      setPeriods(p);
      const done = p.find((x) => x.status == "done");
      if (done) setActivePeriod(done.period);
    });
  }, []);

  return (
    <div className="flex h-screen w-full">
      <Sidebar />
      <div className="flex flex-col h-full w-full">
        <Navbar
          periods={periods}
          activePeriod={activePeriod}
          onSelect={setActivePeriod}
        />
        {activePeriod && <Dashboard period={activePeriod} />}
      </div>
    </div>
  );
}
