import React from "react";
import { ReconciliationSummary, RiskLevel } from "../types/types";

interface Props {
  summary: ReconciliationSummary;
  onViewAll?: () => void;
}

const RISK_BADGES: Record<RiskLevel, string> = {
  low: "text-emerald-700",
  medium: "text-amber-700",
  high: "text-rose-700",
  critical: "text-red-800",
};

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

const ExceptionsTable = ({ summary, onViewAll }: Props) => {
  return (
    <div
      onClick={onViewAll}
      className="bg-white rounded-3xl p-4 border border-slate-100/90 border-t-white shadow-[0_14px_30px_-8px_rgba(15,23,42,0.12),0_4px_10px_-2px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)] hover:shadow-[0_20px_35px_-10px_rgba(15,23,42,0.15),0_6px_12px_-3px_rgba(15,23,42,0.07)] hover:-translate-y-0.5 transition-all duration-200 flex flex-col h-full overflow-hidden cursor-pointer group"
    >
      {/* Header */}
      <div className="flex items-center justify-between pb-2 flex-shrink-0">
        <div className="flex items-center gap-1.5">
          <h3 className="font-bold text-xs text-gray-900 ">
            Active Exceptions
          </h3>
          <span className="text-[10px] text-gray-400">
            ({summary.exceptions.length})
          </span>
        </div>
        <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-gray-100 text-gray-600 ">
          {summary.exceptions.length} Items
        </span>
      </div>

      {/* Internal scroll table body */}
      <div className="flex-1 overflow-y-auto pr-1 min-h-0">
        <table className="w-full text-left text-[11px]">
          <thead className="sticky top-0 bg-white z-10">
            <tr className="border-b border-gray-100 text-gray-400 font-semibold uppercase tracking-wider text-[9px]">
              <th className="pb-1.5 px-1">Payment ID</th>
              <th className="pb-1.5 px-1">Reason</th>
              <th className="pb-1.5 px-1 text-right">Amount</th>
              <th className="pb-1.5 px-1 text-center">Risk</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {summary.exceptions.length === 0 ? (
              <tr>
                <td
                  colSpan={4}
                  className="py-6 text-center text-gray-400 text-xs"
                >
                  Zero discrepancies detected.
                </td>
              </tr>
            ) : (
              summary.exceptions.map((e) => (
                <tr
                  key={e.paymentId}
                  className="hover:bg-blue-50/40 transition"
                >
                  <td className="py-2 px-1 font-mono text-gray-700 font-medium">
                    {e.paymentId}
                  </td>
                  <td className="py-2 px-1 text-gray-500 truncate max-w-[130px]">
                    {e.reasonLabel}
                  </td>
                  <td className="py-2 px-1 text-right font-semibold text-gray-900">
                    {formatInr(e.amount)}
                  </td>
                  <td className="py-2 px-1 text-center">
                    <span
                      className={`inline-block text-[9px] px-1.5 py-0.2 rounded font-bold uppercase ${RISK_BADGES[e.risk]}`}
                    >
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
  );
};

export default ExceptionsTable;
