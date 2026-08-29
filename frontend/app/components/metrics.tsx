import React from 'react'
import { ReconciliationSummary } from '../types/types'

interface Props {
    summary: ReconciliationSummary
}

function formatInr(amount: number) {
    return new Intl.NumberFormat("en-IN", {style: "currency", currency: "INR", maximumFractionDigits: 0}).format(amount)
}

const Metrics = ({summary}: Props) => {

    const cards = [
        { label: "Total records", value: summary.totalRecords, tone: "neutral" },
        { label: "Auto-match rate", value: `${summary.matchRate.toFixed(1)}%`, tone: "success" },
        { label: "Exceptions", value: summary.exceptions.length, tone: "danger" },
        { label: "Amount at risk", value: formatInr(summary.amountAtRisk), tone: "neutral" },
    ] as const
    
    const toneStyles: Record<string, string> = {
        neutral: "bg-white text-gray-900",
        success: "bg-green-50 text-green-800",
        danger: "bg-red-50 text-red-800",
    }

  return (
    <div className="px-8 py-2">
      <div className="flex gap-5">
        {cards.map((c) => (
          <div
            key={c.label}
            className={`rounded-2xl border border-white p-4 w-1/4 ${toneStyles[c.tone]}`}
          >
            <p className="text-sm text-gray-500 mb-1">{c.label}</p>
            <p className="text-2xl font-semibold">{c.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Metrics