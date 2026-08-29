import React from 'react'
import { ReconciliationSummary, MatchType } from '../types/types'

interface Props {
    summary : ReconciliationSummary
}

const LABELS: Record<MatchType, string> = {
    exact: "Exact",
    fee_aware: "Fee-aware",
    lump_sum: "lump-sum",
    fuzzy: "Fuzzy",
}

const BAR_COLORS: Record<MatchType, string> = {
    exact: "bg-green-500",
    fee_aware: "bg-blue-500",
    lump_sum: "bg-purple-500",
    fuzzy: "bg-amber-500",
}

const MatchBreakdown = ({summary}: Props) => {
  
  const maxCount = Math.max(...Object.values(summary.breakdown),1)

    return (
    <div className="mx-8 mt-5 bg-white rounded-2xl border border-white p-5">
      <p className="text-sm text-gray-500 mb-3">Match type breakdown</p>
      <div className="flex flex-col gap-2.5">
        {(Object.keys(LABELS) as MatchType[]).map((type) => {
          const count = summary.breakdown[type] ?? 0
          const widthPct = (count / maxCount) * 100
          return (
            <div key={type} className="flex items-center gap-3">
              <span className="w-20 text-sm text-gray-500">{LABELS[type]}</span>
              <div className="flex-1 bg-gray-100 rounded h-2 overflow-hidden">
                <div className={`${BAR_COLORS[type]} h-full`} style={{ width: `${widthPct}%` }} />
              </div>
              <span className="w-8 text-sm text-right">{count}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default MatchBreakdown