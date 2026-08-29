import React from 'react'
import { ReconciliationSummary, RiskLevel } from '../types/types'

interface Props {
    summary: ReconciliationSummary
}

const RISK_STYLES: Record<RiskLevel, string> = {
    low: "bg-green-50 text-green-700",
    medium: "bg-amber-50 text-amber-700",
    high: "bg-red-50 text-red-700"
}

function formatInr(amount: number) {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(amount)
}

const ExceptionsTable = ({summary}: Props) => {
  return (
    <div className="mx-8 mt-5 mb-8">
      <p className="text-sm text-gray-500 mb-2">
        Exceptions ({summary.exceptions.length})
      </p>
      <div className="bg-white rounded-2xl border border-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-left">
              <th className="px-4 py-2 font-medium">Payment</th>
              <th className="px-4 py-2 font-medium">Reason</th>
              <th className="px-4 py-2 font-medium text-right">Amount</th>
              <th className="px-4 py-2 font-medium">Risk</th>
            </tr>
          </thead>
          <tbody>
            {summary.exceptions.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-400">
                  No exceptions — everything reconciled.
                </td>
              </tr>
            ) : (
              summary.exceptions.map((e) => (
                <tr key={e.paymentId} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-mono text-xs">{e.paymentId}</td>
                  <td className="px-4 py-2 text-gray-600">{e.reasonLabel}</td>
                  <td className="px-4 py-2 text-right">{formatInr(e.amount)}</td>
                  <td className="px-4 py-2">
                    <span className={`px-2 py-0.5 rounded text-xs capitalize ${RISK_STYLES[e.risk]}`}>
                      {e.risk}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default ExceptionsTable