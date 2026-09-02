"use client"

import React, { useEffect, useState } from "react"
import { TransactionInspectionDetails, RiskLevel } from "../types/types"
import { fetchTransactionInspection } from "../connection/api"

interface Props {
  paymentId: string | null
  period: string
  onClose: () => void
}

function formatInr(amount: number | null | undefined) {
  if (amount === null || amount === undefined) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(amount)
}

function formatDate(iso: string | null | undefined) {
  if (!iso) return "—"
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  })
}

const RISK_BADGES: Record<RiskLevel, string> = {
  low: "bg-emerald-50 text-emerald-700 border-emerald-200",
  medium: "bg-amber-50 text-amber-700 border-amber-200",
  high: "bg-rose-50 text-rose-700 border-rose-200",
  critical: "bg-red-100 text-red-800 border-red-300 font-bold",
}

const InspectionModal = ({ paymentId, period, onClose }: Props) => {
  const [data, setData] = useState<TransactionInspectionDetails | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!paymentId) return
    setLoading(true)
    fetchTransactionInspection(paymentId, period)
      .then(setData)
      .catch((err) => console.error(err))
      .finally(() => setLoading(false))
  }, [paymentId, period])

  if (!paymentId) return null

  const isException = data?.status === "exception"
  const isLumpSum = Boolean(
    data?.bank?.narration?.toLowerCase().includes("bulk") ||
    data?.gateway?.payment_id?.includes("_ls") ||
    data?.gateway?.scenario === "lump_sum_member"
  )

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/50 backdrop-blur-sm p-4 animate-in fade-in duration-150"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-3xl max-w-4xl w-full p-6 shadow-2xl border border-gray-100 flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-150 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="flex items-start justify-between pb-4 border-b border-gray-100 flex-shrink-0">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border ${
                  isException
                    ? "bg-rose-50 text-rose-700 border-rose-200"
                    : "bg-emerald-50 text-emerald-700 border-emerald-200"
                }`}
              >
                {isException ? "Exception Root-Cause Audit" : "Reconciled Transaction Audit"}
              </span>
              {isLumpSum && (
                <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md border bg-purple-50 text-purple-700 border-purple-200">
                  Lump-Sum Batch Member
                </span>
              )}
              <span className="text-xs text-gray-400 font-mono">Period: {period}</span>
            </div>
            <h2 className="font-mono text-lg font-bold text-gray-900 mt-1">{paymentId}</h2>
          </div>

          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center transition"
          >
            ✕
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0 text-xs pr-1">
          {loading ? (
            <div className="py-16 text-center text-gray-400">
              <span className="w-5 h-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin inline-block mb-2" />
              <p>Reconstructing 3-way transaction records...</p>
            </div>
          ) : !data ? (
            <div className="py-12 text-center text-gray-400">Transaction record not found.</div>
          ) : (
            <>
              {/* Top Status Alert Pane */}
              <div
                className={`p-4 rounded-2xl border ${
                  isException
                    ? "bg-rose-50/60 border-rose-200/80 text-rose-950"
                    : "bg-emerald-50/60 border-emerald-200/80 text-emerald-950"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-bold text-sm">
                    {isException ? `Flagged: ${data.exception?.reason_code}` : "Successfully Matched"}
                  </span>
                  {data.exception && (
                    <span
                      className={`text-[10px] px-2 py-0.5 rounded border uppercase ${
                        RISK_BADGES[data.exception.risk]
                      }`}
                    >
                      {data.exception.risk} Risk
                    </span>
                  )}
                </div>
                <p className="text-xs leading-relaxed text-gray-700 mt-1">
                  {isException
                    ? data.exception?.recommended_action ||
                      "Transaction failed multi-way comparison tests. Review ledger deltas below."
                    : data.reconciled_match?.explanation || "Amounts and settlement UTR match across all systems."}
                </p>
              </div>

              {/* 3-Way Crosscheck Grid: Chronological Flow (Merchant -> Gateway -> Bank) */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                {/* 1. MERCHANT OMS CARD (Origin) */}
                <div className="bg-gray-50/80 rounded-2xl p-3.5 border border-gray-200/70 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-gray-200/60">
                      <span className="font-bold text-gray-800 uppercase text-[10px] tracking-wide">
                        1. Merchant Order Book
                      </span>
                      <span className="bg-emerald-100 text-emerald-700 px-1.5 py-0.5 rounded text-[9px] font-semibold">
                        Origin / OMS
                      </span>
                    </div>
                    {data.merchant ? (
                      <div className="space-y-2 text-[11px]">
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Claimed Amount</span>
                          <span className="font-bold text-sm text-gray-900">
                            {formatInr(data.merchant.amount)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Order Status</span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase ${
                              data.merchant.status === "paid"
                                ? "bg-emerald-50 text-emerald-700"
                                : "bg-amber-50 text-amber-700"
                            }`}
                          >
                            {data.merchant.status}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Order ID</span>
                          <span className="font-mono text-gray-700 truncate block">
                            {data.merchant.order_id}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Marked Paid At</span>
                          <span className="text-gray-600">{formatDate(data.merchant.marked_paid_at)}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Scenario Tag</span>
                          <span className="text-gray-500 font-mono text-[10px]">
                            {data.merchant.scenario}
                          </span>
                        </div>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-rose-500 font-medium">
                        No Merchant Record Linked
                      </div>
                    )}
                  </div>
                </div>

                {/* 2. GATEWAY LEDGER (Processing & Ingest) */}
                <div className="bg-gray-50/80 rounded-2xl p-3.5 border border-gray-200/70 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-gray-200/60">
                      <span className="font-bold text-gray-800 uppercase text-[10px] tracking-wide">
                        2. Gateway Ledger
                      </span>
                      <span className="bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded text-[9px] font-semibold">
                        Processor / Ingest
                      </span>
                    </div>
                    {data.gateway ? (
                      <div className="space-y-2 text-[11px]">
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Captured Amount</span>
                          <span className="font-bold text-sm text-gray-900">
                            {formatInr(data.gateway.amount)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Gateway Status</span>
                          <span className="bg-emerald-50 text-emerald-700 px-1.5 py-0.5 rounded text-[9px] font-semibold uppercase">
                            {data.gateway.status}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Order ID</span>
                          <span className="font-mono text-gray-700 truncate block">
                            {data.gateway.order_id}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">UTR Reference</span>
                          <span className="font-mono text-gray-700 truncate block">
                            {data.gateway.utr || "None"}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Capture Timestamp</span>
                          <span className="text-gray-600">{formatDate(data.gateway.created_at)}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-rose-500 font-medium">
                        Missing Gateway Record
                      </div>
                    )}
                  </div>
                </div>

                {/* 3. BANK STATEMENT CARD (Settlement & Vault) */}
                <div className="bg-gray-50/80 rounded-2xl p-3.5 border border-gray-200/70 flex flex-col justify-between">
                  <div>
                    <div className="flex items-center justify-between pb-2 mb-2 border-b border-gray-200/60">
                      <span className="font-bold text-gray-800 uppercase text-[10px] tracking-wide">
                        3. Bank Settlement
                      </span>
                      <span className="bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded text-[9px] font-semibold">
                        Vault / Payout
                      </span>
                    </div>
                    {data.bank ? (
                      <div className="space-y-2 text-[11px]">
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">
                            Credited Amount {isLumpSum && "(Aggregate Batch)"}
                          </span>
                          <span className="font-bold text-sm text-gray-900">
                            {formatInr(data.bank.amount)}
                          </span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Bank UTR</span>
                          <span className="font-mono text-gray-700 truncate block">{data.bank.utr}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Narration</span>
                          <span className="text-gray-600 truncate block">{data.bank.narration}</span>
                        </div>
                        <div>
                          <span className="text-gray-400 block text-[9px] uppercase">Credit Date</span>
                          <span className="text-gray-600">{formatDate(data.bank.credited_at)}</span>
                        </div>
                      </div>
                    ) : (
                      <div className="py-6 text-center text-rose-500 font-medium">
                        Missing Inbound Bank Credit
                      </div>
                    )}
                  </div>
                </div>
              </div>

              {/* Settlement Math & Variance Breakdown */}
              <div className="bg-gray-50 rounded-2xl p-4 border border-gray-200/70">
                <span className="font-bold text-gray-900 block text-xs mb-2">
                  Reconciliation Breakdown &amp; Financial Exposure
                </span>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center">
                  <div className="bg-white p-2.5 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-400 block uppercase">Merchant Claimed</span>
                    <span className="font-semibold text-gray-800">
                      {formatInr(data.merchant?.amount ?? 0)}
                    </span>
                  </div>

                  <div className="bg-white p-2.5 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-400 block uppercase">Gateway Captured</span>
                    <span className="font-semibold text-gray-800">
                      {formatInr(data.gateway?.amount ?? 0)}
                    </span>
                  </div>

                  <div className="bg-white p-2.5 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-400 block uppercase">Bank Credit</span>
                    <span className="font-semibold text-gray-800">
                      {formatInr(data.bank?.amount ?? 0)}
                    </span>
                    {isLumpSum && (
                      <span className="text-[9px] text-purple-600 block mt-0.5 font-medium">
                        Batch Deposit
                      </span>
                    )}
                  </div>

                  <div className="bg-white p-2.5 rounded-xl border border-gray-100">
                    <span className="text-[10px] text-gray-400 block uppercase">
                      {isException ? "Exposure at Risk" : "Net Variance"}
                    </span>
                    <span
                      className={`font-bold ${
                        isException ? "text-rose-600" : "text-emerald-600"
                      }`}
                    >
                      {formatInr(data.exception?.amount ?? 0)}
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
        </div>

        {/* Modal Footer */}
        <div className="pt-3 border-t border-gray-100 flex items-center justify-between flex-shrink-0">
          <span className="text-[11px] text-gray-400">
            Immutable 3-way log audit for period {period}
          </span>
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-xl bg-gray-900 hover:bg-gray-800 text-white text-xs font-semibold transition cursor-pointer"
          >
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  )
}

export default InspectionModal