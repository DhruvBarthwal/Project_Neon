import React from "react"
import { PeriodStatus } from "../types/types"

interface Props {
  periods: PeriodStatus[]
  activePeriod: string
  onSelect: (period: string) => void
}

const Navbar = ({ periods, activePeriod, onSelect }: Props) => {
  return (
    <div className="w-full p-4 flex items-center justify-between border-b border-gray-100">
      <div className="flex items-center gap-2">
        <span className="font-semibold text-lg">Finance controller</span>
      </div>
      <div className="flex items-center gap-2">
        {periods.map((p) => (
          <button
            key={p.period}
            onClick={() => onSelect(p.period)}
            disabled={p.status === "not_run"}
            className={`px-3 py-1.5 rounded-lg text-sm ${
              p.period === activePeriod
                ? "bg-gray-900 text-white"
                : p.status === "not_run"
                ? "text-gray-300"
                : "bg-gray-50 text-gray-700"
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>
    </div>
  )
}

export default Navbar