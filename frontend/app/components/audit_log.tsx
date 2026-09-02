"use client";

import React, { useEffect, useState } from "react";
import { AuditRun } from "../types/types";
import { fetchAuditLog } from "../connection/api";

interface Props {
  period: string;
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFullDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual Trigger (User Action)",
  auto_qa: "Automated Reconciler (Q&A Agent)",
};

const AuditLog = ({ period }: Props) => {
  const [runs, setRuns] = useState<AuditRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedRun, setSelectedRun] = useState<AuditRun | null>(null);

  useEffect(() => {
    setLoading(true);
    fetchAuditLog(period)
      .then(setRuns)
      .finally(() => setLoading(false));
  }, [period]);

  if (loading || runs.length === 0) return null;

  return (
    <>
      {/* Widget Box */}
      <div className="bg-white rounded-2xl p-3 border border-gray-100 shadow-sm flex flex-col h-full overflow-hidden">
        <div className="flex items-center justify-between pb-1.5 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <h3 className="font-bold text-xs text-gray-900">Audit Trail</h3>
            <span className="text-[10px] text-gray-400">({runs.length})</span>
          </div>
          <span className="text-[9px] font-bold uppercase bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
            Immutable Log
          </span>
        </div>

        {/* Internal Scroll Body */}
        <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 min-h-0">
          {runs.map((r, i) => (
            <div
              key={i}
              onClick={() => setSelectedRun(r)}
              className="flex items-center justify-between p-1.5 rounded-lg hover:bg-gray-50/80 active:scale-[0.99] cursor-pointer transition border border-transparent hover:border-gray-100 group"
            >
              <div className="truncate max-w-[130px]">
                <div className="flex items-center gap-1">
                  <span className="font-mono text-[10px] font-semibold text-gray-800 block truncate">
                    {r.triggeredBy}
                  </span>
                  <span className="text-[9px] text-blue-600 opacity-0 group-hover:opacity-100 transition">
                    ↗
                  </span>
                </div>
                <span className="text-[9px] text-gray-400">
                  {formatTime(r.runAt)}
                </span>
              </div>
              <div className="text-right flex flex-col items-end">
                <span className="font-semibold text-[10px] text-emerald-600 bg-emerald-50 px-1.5 py-0.2 rounded leading-tight">
                  {r.matchRate}%
                </span>
                <span className="text-[8px] text-gray-400 mt-0.5">
                  {r.matchedCount}/{r.totalRecords}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Modal / Backdrop Overlay */}
      {selectedRun && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4 animate-in fade-in duration-150"
          onClick={() => setSelectedRun(null)}
        >
          <div
            className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 flex flex-col max-h-[85vh] animate-in zoom-in-95 duration-150"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Modal Header */}
            <div className="flex items-start justify-between pb-4 border-b border-gray-100 flex-shrink-0">
              <div>
                <span className="text-xs font-bold uppercase tracking-wider bg-blue-50 text-blue-700 px-2 py-0.5 rounded-md">
                  Audit Run Details
                </span>
                <h2 className="font-mono text-base font-bold text-gray-900 mt-1">
                  {selectedRun.triggeredBy}
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Executed on:{" "}
                  <span className="text-gray-900 font-medium">
                    {formatFullDateTime(selectedRun.runAt)}
                  </span>
                </p>
              </div>

              {/* Close Button */}
              <button
                onClick={() => setSelectedRun(null)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center transition"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0 pr-1 text-xs">
              {/* Metric Highlights */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 p-3 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Match Efficiency
                  </span>
                  <span className="text-lg font-bold text-emerald-600 mt-0.5 block">
                    {selectedRun.matchRate}%
                  </span>
                </div>
                <div className="bg-gray-50 p-3 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Resolved / Total
                  </span>
                  <span className="text-lg font-bold text-gray-900 mt-0.5 block">
                    {selectedRun.matchedCount}{" "}
                    <span className="text-xs font-normal text-gray-400">
                      / {selectedRun.totalRecords}
                    </span>
                  </span>
                </div>
              </div>

              {/* Event Metadata Breakdown */}
              <div className="bg-gray-50 rounded-2xl p-3.5 border border-gray-100 space-y-2.5">
                <div className="flex items-center justify-between pb-2 border-b border-gray-200/60">
                  <span className="text-gray-500 font-medium">
                    Execution Source
                  </span>
                  <span className="font-semibold text-gray-800">
                    {SOURCE_LABELS[selectedRun.triggerSource] ??
                      selectedRun.triggerSource}
                  </span>
                </div>
                <div className="flex items-center justify-between pb-2 border-b border-gray-200/60">
                  <span className="text-gray-500 font-medium">
                    Reconciliation Period
                  </span>
                  <span className="font-mono font-semibold text-gray-800">
                    {period}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-500 font-medium">
                    Unreconciled Delta
                  </span>
                  <span className="font-semibold text-rose-600">
                    {selectedRun.totalRecords - selectedRun.matchedCount}{" "}
                    Exceptions
                  </span>
                </div>
              </div>

              {/* System Note */}
              <div className="p-3 bg-blue-50/60 rounded-2xl border border-blue-100 text-[11px] text-blue-900 leading-relaxed">
                🔒 <strong>Cryptographic Audit Stamp:</strong> This execution
                state is logged into the append-only ledger history. All matched
                records and fee variances are permanently committed.
              </div>
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex items-center justify-end flex-shrink-0">
              <button
                onClick={() => setSelectedRun(null)}
                className="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default AuditLog;
