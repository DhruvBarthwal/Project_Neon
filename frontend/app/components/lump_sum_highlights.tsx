"use client"

import React, { useState } from "react"
import { ReconciliationSummary } from "../types/types"

interface Props {
  summary: ReconciliationSummary
}

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount)
}

const LumpSumHighlights = ({ summary }: Props) => {
  const [selectedHighlight, setSelectedHighlight] = useState<
    ReconciliationSummary["highlights"][0] | null
  >(null)

  return (
    <>
      {/* Widget Container */}
      <div className="bg-white rounded-xl py-3 px-3 border border-gray-100 shadow-sm flex flex-col">
        <div className="flex items-center justify-between mb-1.5 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <h3 className="font-bold text-xs text-gray-900">Batch settlements</h3>
            <span className="text-[10px] text-gray-400">({summary.highlights.length})</span>
          </div>
          <span className="text-[9px] font-bold uppercase bg-purple-50 text-gray-700 px-1.5 py-0.5 rounded">
            Needs allocation
          </span>
        </div>

        {summary.highlights.length === 0 ? (
          <p className="text-[11px] text-gray-400 py-1">No aggregate bank deposits pending.</p>
        ) : (
          /* Locked height displaying ~2 items with internal scrolling */
          <div className="max-h-[92px] overflow-y-auto space-y-1.5 pr-1">
            {summary.highlights.map((h) => (
              <div
                key={h.utr.split("(")[0].trim()}
                onClick={() => setSelectedHighlight(h)}
                className="bg-purple-50/60 hover:bg-purple-100/70 cursor-pointer active:scale-[0.99] transition rounded-lg py-1.5 px-2 border border-purple-100/60 flex items-center justify-between group"
              >
                <div>
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-[10px] font-bold text-gray-900 block">
                      {h.utr.split("(")[0].trim()}
                    </span>
                    <span className="text-[9px] text-gray-600 opacity-0 group-hover:opacity-100 transition">
                      ↗
                    </span>
                  </div>
                  <span className="text-[9px] text-gray-500">
                    {h.memberPaymentIds.length} invoices matched
                  </span>
                </div>
                <div className="text-right">
                  <span className="text-[10px] font-bold text-gray-900 block leading-tight">
                    {formatInr(h.bankAmount)}
                  </span>
                  <span className="text-[8px] text-gray-600 font-medium">Details</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Modal / Backdrop Overlay */}
      {selectedHighlight && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-150">
          <div
            className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-gray-100 flex-shrink-0">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider text-gray-700  py-0.5 rounded-md">
                  Batch settlement breakdown
                </span>
                <h2 className="font-mono text-base font-bold text-gray-900 mt-1">
                  {selectedHighlight.utr.split("(")[0].trim()}
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Total Bank Credit:{" "}
                  <span className="font-bold text-gray-900">
                    {formatInr(selectedHighlight.bankAmount)}
                  </span>
                </p>
              </div>

              <button
                onClick={() => setSelectedHighlight(null)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center transition"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0 pr-1 text-xs">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-semibold text-gray-700">
                    Matched invoices ({selectedHighlight.memberPaymentIds.length})
                  </span>
                  <span className="text-[13px] text-emerald-800 px-2 py-0.5 rounded-full font-medium">
                    Auto-allocated
                  </span>
                </div>
                <p className="text-[13px] text-gray-400 mb-2">
                  {formatInr(selectedHighlight.memberAmounts.reduce((a, b) => a + b, 0))} of{" "}
                  {formatInr(selectedHighlight.bankAmount)} allocated
                </p>
                <div className="bg-gray-50 rounded-2xl p-2.5 border border-gray-100 divide-y divide-gray-100 space-y-1">
                  {selectedHighlight.memberPaymentIds.map((pid, i) => (
                    <div key={pid} className="flex items-center justify-between py-1.5 px-1 font-mono text-gray-700">
                      <span className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                        {pid}
                      </span>
                      <span className="text-[13px] text-gray-500 font-sans">
                        {formatInr(selectedHighlight.memberAmounts[i])}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {selectedHighlight.heldBackPaymentIds && selectedHighlight.heldBackPaymentIds.length > 0 && (
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-semibold text-amber-800">
                      Held Back / Unallocated Payments ({selectedHighlight.heldBackPaymentIds.length})
                    </span>
                    <span className="text-[13px] text-amber-800 px-2 py-0.5 rounded-full font-medium">
                      Flagged for Review
                    </span>
                  </div>
                  <div className="bg-gray-50/50 rounded-2xl p-2.5 border border-amber-100 divide-y divide-amber-100 space-y-1">
                    {selectedHighlight.heldBackPaymentIds.map((pid) => (
                      <div key={pid} className="flex items-center justify-between py-1.5 px-1 font-mono text-amber-900">
                        <span className="flex items-center gap-2">
                          <span className="w-1.5 h-1.5 rounded-full bg-gray-500" />
                          {pid}
                        </span>
                        <span className="text-[13px] text-gray-600 font-sans">Pending Manual Audit</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex items-center justify-end flex-shrink-0">
              <button
                onClick={() => setSelectedHighlight(null)}
                className="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}

export default LumpSumHighlights