"use client";

import React, { useEffect, useState } from "react";
import { fetchAuditLog } from "../connection/api";

export interface AuditLogEntry {
  id?: string;
  created_at?: string;
  run_at?: string;
  period: string;
  actor?: string;
  triggered_by?: string;
  event_type?: string;
  trigger_source?: string;
  intent?: string;
  target_identifier?: string;
  outcome_status?: string;
  exposure_amount?: number | string;
  match_rate?: number;
  metadata?: Record<string, any>;
}

interface Props {
  period: string;
}

function formatTime(iso?: string) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("en-IN", {
      hour: "2-digit",
      minute: "2-digit",
    });
  } catch {
    return "—";
  }
}

function formatFullDateTime(iso?: string) {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "—";
  }
}

const EVENT_LABELS: Record<string, string> = {
  CYCLE_RUN: "Batch Cycle Reconciliation",
  RECORD_AUDIT: "Atomic Transaction Audit",
  WORKSPACE_NAVIGATION: "Ledger Table Navigation",
  METRIC_INSPECTION: "Performance & SLA Review",
  BATCH_UNBUNDLE: "Lump-Sum Settlement Audit",
};

const TABLE_NAMES: Record<string, string> = {
  gateway: "Gateway Records Ledger",
  bank: "Bank Settlements Feed",
  merchant: "Merchant OMS Orders",
  exceptions: "Exceptions & Discrepancies Queue",
  ledger_matches: "Reconciled Matches Registry",
};

// Human-readable, accountant-focused verification details
const MetadataRenderer = ({ log }: { log: AuditLogEntry }) => {
  const meta = log.metadata || {};
  const event = log.event_type || "";

  // 1. Transaction 3-Way Inspection
  if (event === "RECORD_AUDIT" || log.intent === "lookup_record") {
    return (
      <div className="space-y-3">
        <div className="border border-gray-200/80 rounded-2xl overflow-hidden bg-white shadow-xs">
          <div className="bg-gray-50/80 px-3.5 py-2 border-b border-gray-100 text-[11px] font-semibold text-gray-700 flex justify-between items-center">
            <span>3-Way Cross-Ledger Verification</span>
            <span className="text-[10px] text-gray-400 font-mono">Chain of Custody</span>
          </div>
          <div className="divide-y divide-gray-100 text-xs">
            <div className="flex justify-between items-center px-3.5 py-2">
              <span className="text-gray-500 font-medium">Merchant OMS Order</span>
              <span className="font-semibold text-gray-800">
                {meta.merchant_status ? (
                  <span className="capitalize text-emerald-600 font-bold">{meta.merchant_status}</span>
                ) : (
                  <span className="text-gray-400 italic">Not recorded</span>
                )}
              </span>
            </div>
            <div className="flex justify-between items-center px-3.5 py-2">
              <span className="text-gray-500 font-medium">Payment Gateway Status</span>
              <span className="font-semibold text-gray-800">
                {meta.gateway_status ? (
                  <span className="capitalize text-blue-600 font-bold">{meta.gateway_status}</span>
                ) : (
                  <span className="text-gray-400 italic">Not ingested</span>
                )}
              </span>
            </div>
            <div className="flex justify-between items-center px-3.5 py-2">
              <span className="text-gray-500 font-medium">Bank Settlement Ref (UTR)</span>
              <span className="font-mono font-medium text-gray-800">
                {meta.bank_utr || <span className="text-gray-400 italic">Uncredited / Pending</span>}
              </span>
            </div>
            <div className="flex justify-between items-center px-3.5 py-2 bg-gray-50/40">
              <span className="text-gray-500 font-medium">Idempotency Retry Check</span>
              <span className="font-semibold text-gray-700">
                {meta.is_retry ? (
                  <span className="text-blue-600 font-medium">Duplicate attempt verified</span>
                ) : (
                  <span className="text-gray-500">Standard initial payment</span>
                )}
              </span>
            </div>
          </div>
        </div>

        {log.outcome_status === "BENIGN_RETRY" && (
          <div className="p-3 bg-blue-50/70 border border-blue-100/80 rounded-2xl text-[11px] text-blue-900 leading-relaxed">
            <span className="font-bold block mb-0.5">Auditor Note:</span>
            This attempt was flagged as a secondary checkout retry. Because the parent merchant order is already verified as settled, the real financial balance sheet exposure is <strong>₹0.00</strong>.
          </div>
        )}
      </div>
    );
  }

  // 2. Navigation Action
  if (event === "WORKSPACE_NAVIGATION" || log.intent === "table_navigation") {
    const rawTable = meta.target_table || "records";
    const readableTable = TABLE_NAMES[rawTable] || `${rawTable} Ledger`;
    return (
      <div className="bg-gray-50/70 p-3.5 rounded-2xl border border-gray-100 space-y-2 text-xs">
        <div className="flex items-center justify-between pb-2 border-b border-gray-200/60">
          <span className="text-gray-500 font-medium">Requested Data Grid</span>
          <span className="font-bold text-gray-900">{readableTable}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-gray-500 font-medium">Dataset Scope</span>
          <span className="font-semibold text-gray-800">Full Monthly Ledger ({log.period})</span>
        </div>
        <div className="pt-2 text-[11px] text-gray-500 leading-relaxed border-t border-gray-200/50">
          The Copilot navigated the analyst directly into the raw data workspace to avoid flooding the audit log with large tabular exports.
        </div>
      </div>
    );
  }

  // 3. Batch Reconciliation Cycle Run
  if (event === "CYCLE_RUN" || log.intent === "reconcile_cycle") {
    return (
      <div className="border border-gray-200/80 rounded-2xl overflow-hidden bg-white shadow-xs">
        <div className="bg-gray-50/80 px-3.5 py-2 border-b border-gray-100 text-[11px] font-semibold text-gray-700">
          Reconciliation Batch Summary
        </div>
        <div className="divide-y divide-gray-100 text-xs">
          <div className="flex justify-between items-center px-3.5 py-2">
            <span className="text-gray-500 font-medium">Matches Resolved</span>
            <span className="font-bold text-emerald-600">{meta.matches_count ?? "—"}</span>
          </div>
          <div className="flex justify-between items-center px-3.5 py-2">
            <span className="text-gray-500 font-medium">Exceptions Flagged</span>
            <span className="font-bold text-rose-600">{meta.exceptions_count ?? "—"}</span>
          </div>
          <div className="flex justify-between items-center px-3.5 py-2">
            <span className="text-gray-500 font-medium">Cycle Auto-Match Efficiency</span>
            <span className="font-bold text-gray-900">{meta.match_rate_pct ?? "—"}%</span>
          </div>
          <div className="flex justify-between items-center px-3.5 py-2 bg-gray-50/40">
            <span className="text-gray-500 font-medium">Execution Mode</span>
            <span className="font-medium text-gray-700 capitalize">{meta.trigger_source || "Automated run"}</span>
          </div>
        </div>
      </div>
    );
  }

  // 4. Metric / SLA Review
  if (event === "METRIC_INSPECTION" || log.intent === "metric_query") {
    return (
      <div className="border border-gray-200/80 rounded-2xl overflow-hidden bg-white shadow-xs">
        <div className="bg-gray-50/80 px-3.5 py-2 border-b border-gray-100 text-[11px] font-semibold text-gray-700">
          Period Metrics Inspected
        </div>
        <div className="divide-y divide-gray-100 text-xs">
          <div className="flex justify-between items-center px-3.5 py-2">
            <span className="text-gray-500 font-medium">Match Efficiency (SLA: 95%)</span>
            <span className="font-bold text-emerald-600">{meta.match_rate ?? "—"}%</span>
          </div>
          <div className="flex justify-between items-center px-3.5 py-2">
            <span className="text-gray-500 font-medium">Unreconciled Discrepancies</span>
            <span className="font-bold text-rose-600">{meta.exceptions ?? "—"} exceptions</span>
          </div>
        </div>
      </div>
    );
  }

  // 5. Clean fallback for any generic custom events
  return (
    <div className="p-3 bg-gray-50 rounded-2xl border border-gray-100 text-xs text-gray-600">
      Operational verification confirmed for cycle <strong>{log.period}</strong> under target entity <strong>{log.target_identifier}</strong>.
    </div>
  );
};

const AuditLog = ({ period }: Props) => {
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedLog, setSelectedLog] = useState<AuditLogEntry | null>(null);

  useEffect(() => {
    let isMounted = true;

    const loadData = () => {
      fetchAuditLog(period)
        .then((data: any) => {
          if (!isMounted) return;
          const entries = Array.isArray(data) ? data : data?.records || [];
          setLogs(entries);
        })
        .catch(() => {
          if (isMounted) setLogs([]);
        })
        .finally(() => {
          if (isMounted) setLoading(false);
        });
    };

    loadData();
    const interval = setInterval(loadData, 4000);

    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, [period]);

  const renderActorBadge = (actorName?: string) => {
    const name = (actorName || "").toLowerCase();
    if (name.includes("agent") || name.includes("copilot")) {
      return (
        <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-gray-700 px-1.5 py-0.5 rounded-md">
          Agent
        </span>
      );
    }
    if (name.includes("engine") || name.includes("system") || name === "auto") {
      return (
        <span className="text-[9px] font-semibold bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded-md">
          Engine
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 text-[9px] font-semibold text-amber-800px-1.5 py-0.5 rounded-md">
         User
      </span>
    );
  };

  const getStatusBadge = (status?: string) => {
    switch (status) {
      case "CLEAN_MATCH":
        return <span className="font-semibold text-[10px] text-emerald-700  px-1.5 py-0.5 rounded">Clean Match</span>;
      case "BENIGN_RETRY":
        return <span className="font-semibold text-[10px] text-sky-700 px-1.5 py-0.5 rounded">Benign Retry</span>;
      case "EXCEPTION_FLAGGED":
        return <span className="font-semibold text-[10px] text-rose-700  px-1.5 py-0.5 rounded">Exception</span>;
      case "COMPLETED":
        return <span className="font-semibold text-[10px] text-purple-900 px-1.5 py-0.5 rounded">Reconciled</span>;
      case "NAVIGATED":
        return <span className="font-semibold text-[10px] text-indigo-900  px-1.5 py-0.5 rounded">Navigated</span>;
      default:
        return <span className="font-semibold text-[10px] text-gray-600 px-1.5 py-0.5 rounded">{status || "Audited"}</span>;
    }
  };

  if (loading) {
    return (
      <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm flex items-center justify-center h-full">
        <span className="text-xs text-gray-400 animate-pulse font-medium">Loading audit trail...</span>
      </div>
    );
  }

  if (logs.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-3 border border-gray-100 shadow-sm flex flex-col h-full">
        <div className="flex items-center justify-between pb-1.5 flex-shrink-0">
          <h3 className="font-bold text-xs text-gray-900">Audit Trail</h3>
          <span className="text-[9px] font-bold uppercase bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
            Live Ledger
          </span>
        </div>
        <div className="flex-1 flex flex-col items-center justify-center text-center p-3 border border-dashed border-gray-100 rounded-xl my-1">
          <p className="text-[11px] font-medium text-gray-500">No events logged for {period}</p>
          <p className="text-[9px] text-gray-400 mt-0.5">
            Query a transaction in the Copilot to create audit entries.
          </p>
        </div>
      </div>
    );
  }

  return (
    <>
      <div className="bg-white rounded-2xl p-3 border border-gray-100 shadow-sm flex flex-col h-full overflow-hidden">
        <div className="flex items-center justify-between pb-1.5 flex-shrink-0">
          <div className="flex items-center gap-1.5">
            <h3 className="font-bold text-xs text-gray-900">Audit Trail</h3>
            <span className="text-[10px] text-gray-400">({logs.length})</span>
          </div>
          <span className="text-[9px] font-bold uppercase bg-gray-100 text-gray-700 px-1.5 py-0.5 rounded">
            Live Ledger
          </span>
        </div>

        <div className="flex-1 overflow-y-auto pr-1 space-y-1.5 min-h-0">
          {logs.map((item, i) => {
            const rawTarget = item.target_identifier || (item as any).payment_id || (item.event_type === "CYCLE_RUN" ? `Cycle ${item.period}` : `Run #${logs.length - i}`);
            const rawTime = item.created_at || item.run_at || "";
            const rawActor = item.actor || item.triggered_by || "system";
            const rawStatus = item.outcome_status || (item.match_rate !== undefined ? "COMPLETED" : "INSPECTED");
            const exposure = Number(item.exposure_amount || 0);

            return (
              <div
                key={item.id || `log-${i}`}
                onClick={() => setSelectedLog(item)}
                className="flex items-center justify-between p-2 rounded-lg hover:bg-gray-50/80 active:scale-[0.99] cursor-pointer transition border border-transparent hover:border-gray-100 group"
              >
                <div className="truncate max-w-[140px]">
                  <div className="flex items-center gap-1">
                    <span className="font-mono text-[10px] font-semibold text-gray-900 block truncate">
                      {rawTarget}
                    </span>
                    <span className="text-[9px] text-blue-600 opacity-0 group-hover:opacity-100 transition">
                      ↗
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <span className="text-[9px] text-gray-400">{formatTime(rawTime)}</span>
                    {renderActorBadge(rawActor)}
                  </div>
                </div>

                <div className="text-right flex flex-col items-end">
                  {getStatusBadge(rawStatus)}
                  <span className="text-[8px] text-gray-400 mt-0.5 font-mono">
                    {exposure > 0 ? `₹${exposure.toLocaleString("en-IN")}` : "₹0.00 Risk"}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Detail Modal */}
      {selectedLog && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-gray-900/40 backdrop-blur-sm p-4"
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="bg-white rounded-3xl max-w-lg w-full p-6 shadow-2xl border border-gray-100 flex flex-col max-h-[85vh]"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="flex items-start justify-between pb-4 border-b border-gray-100 flex-shrink-0">
              <div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold uppercase tracking-wider text-blue-900 py-0.5 rounded-md">
                    Audit Verification Card
                  </span>
                  {renderActorBadge(selectedLog.actor || selectedLog.triggered_by)}
                </div>
                <h2 className="font-mono text-base font-bold text-gray-900 mt-1">
                  {selectedLog.target_identifier || `Cycle ${selectedLog.period}`}
                </h2>
                <p className="text-xs text-gray-500 mt-0.5">
                  Logged: {formatFullDateTime(selectedLog.created_at || selectedLog.run_at)}
                </p>
              </div>

              <button
                onClick={() => setSelectedLog(null)}
                className="w-7 h-7 rounded-full bg-gray-100 hover:bg-gray-200 text-gray-500 flex items-center justify-center cursor-pointer transition"
              >
                ✕
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto py-4 space-y-4 min-h-0 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 p-3 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Audit Outcome
                  </span>
                  <div className="mt-1">
                    {getStatusBadge(selectedLog.outcome_status || "COMPLETED")}
                  </div>
                  <span className="text-[10px] text-gray-400 block mt-1">
                    Event: <span className="text-gray-700 font-medium">{EVENT_LABELS[selectedLog.event_type || ""] || selectedLog.event_type}</span>
                  </span>
                </div>

                <div className="bg-gray-50 p-3 rounded-2xl border border-gray-100">
                  <span className="text-[10px] font-semibold text-gray-400 uppercase tracking-wider block">
                    Financial Capital at Risk
                  </span>
                  <span className={`text-lg font-bold mt-0.5 block ${Number(selectedLog.exposure_amount || 0) > 0 ? "text-rose-600" : "text-emerald-600"}`}>
                    ₹{Number(selectedLog.exposure_amount || 0).toLocaleString("en-IN", { minimumFractionDigits: 2 })}
                  </span>
                  <span className="text-[10px] text-gray-400 block mt-0.5">
                    Accounting Period: <strong className="text-gray-700">{selectedLog.period}</strong>
                  </span>
                </div>
              </div>

              {/* Dynamic Accountant-Friendly Inspection Card */}
              <div>
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider block mb-1.5">
                  Forensic Breakdown & Evidence
                </span>
                <MetadataRenderer log={selectedLog} />
              </div>

              {/* Immutable Compliance Guarantee */}
              <div className="p-3 bg-gray-50/70 rounded-2xl border border-gray-100 text-[11px] text-gray-500 leading-relaxed">
                Immutable compliance event stored in the PostgreSQL ledger. Proves data lineage, user access history, and verified ledger status for regulatory audits.
              </div>
            </div>

            {/* Modal Footer */}
            <div className="pt-3 border-t border-gray-100 flex justify-end">
              <button
                onClick={() => setSelectedLog(null)}
                className="px-4 py-2 rounded-xl bg-gray-100 hover:bg-gray-200 text-gray-700 text-xs font-semibold cursor-pointer transition"
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