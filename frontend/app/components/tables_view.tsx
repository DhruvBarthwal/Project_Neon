"use client";

import React, { useState, useEffect } from "react";
import {
  ReconciliationSummary,
  AllTableRecords,
  RiskLevel,
  PeriodStatus,
} from "../types/types";
import { fetchAllTables, fetchSummary } from "../connection/api";
import InspectionModal from "./inspection_model";

export type TableType =
  | "exceptions"
  | "ledger_matches"
  | "gateway"
  | "bank"
  | "merchant";

interface Props {
  period: string;
  periods?: PeriodStatus[];
  summary: ReconciliationSummary | null;
  initialTable?: TableType;
  onSelectPeriod?: (period: string) => void;
  onBack: () => void;
}

const TABLE_OPTIONS: { id: TableType; label: string; desc: string }[] = [
  {
    id: "exceptions",
    label: "Exceptions",
    desc: "Transactions failing matching rules",
  },
  {
    id: "ledger_matches",
    label: "Reconciled Ledger Matches",
    desc: "Successfully matched multi-way records",
  },
  {
    id: "gateway",
    label: "Gateway Records",
    desc: "Raw captured payment events from gateway",
  },
  {
    id: "bank",
    label: "Bank Records",
    desc: "Inbound settlement credits & UTRs from bank",
  },
  {
    id: "merchant",
    label: "Merchant Records",
    desc: "Order book claims & internal merchant status",
  },
];

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
    maximumFractionDigits: 2,
  }).format(amount);
}

function formatDate(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const TablesView = ({
  period,
  periods = [],
  summary: initialSummary,
  initialTable = "exceptions",
  onSelectPeriod,
  onBack,
}: Props) => {
  const [selectedPeriod, setSelectedPeriod] = useState<string>(period);
  const [currentSummary, setCurrentSummary] = useState<ReconciliationSummary | null>(
    initialSummary,
  );
  const [selectedTable, setSelectedTable] = useState<TableType>(initialTable);
  const [searchQuery, setSearchQuery] = useState("");
  const [tableData, setTableData] = useState<AllTableRecords | null>(null);
  const [loading, setLoading] = useState(true);
  const [inspectingPaymentId, setInspectingPaymentId] = useState<string | null>(
    null,
  );

  useEffect(() => {
    setSelectedPeriod(period);
  }, [period]);

  useEffect(() => {
    setCurrentSummary(initialSummary);
  }, [initialSummary]);

  // Synchronize when parent updates target table from chat deep-link
  useEffect(() => {
    if (initialTable) {
      setSelectedTable(initialTable);
    }
  }, [initialTable]);

  useEffect(() => {
    setLoading(true);
    fetchAllTables(selectedPeriod)
      .then(setTableData)
      .catch((err) => console.error("Error fetching tables:", err))
      .finally(() => setLoading(false));

    // Keep exceptions data aligned when period changes within tables view
    if (selectedPeriod !== period) {
      fetchSummary(selectedPeriod)
        .then(setCurrentSummary)
        .catch(() => setCurrentSummary(null));
    }
  }, [selectedPeriod, period]);

  const handlePeriodChange = (newPeriod: string) => {
    setSelectedPeriod(newPeriod);
    if (onSelectPeriod) {
      onSelectPeriod(newPeriod);
    }
  };

  return (
    <div className="h-full w-full p-6 md:p-8 flex flex-col overflow-hidden bg-white">
      {/* Top Controls */}
      <div className="flex flex-wrap items-center justify-between pb-4 border-b border-gray-100 flex-shrink-0 gap-4 mb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl md:text-2xl font-bold text-gray-900 tracking-tight">
              Data &amp; Reconciliation Tables
            </h1>
            <span className="bg-gray-100 text-gray-700 px-2 py-0.5 rounded text-xs font-mono font-semibold">
              {selectedPeriod}
            </span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">
            {TABLE_OPTIONS.find((t) => t.id === selectedTable)?.desc}
          </p>
        </div>

        <div className="flex items-center gap-3">
          {/* Month / Period Dropdown Selector */}
          {periods.length > 0 && (
            <div className="relative">
              <select
                value={selectedPeriod}
                onChange={(e) => handlePeriodChange(e.target.value)}
                className="appearance-none bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-800 text-xs font-semibold py-2 pl-3 pr-8 rounded-xl cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition shadow-sm font-mono"
              >
                {periods.map((p) => (
                  <option key={p.period} value={p.period}>
                    {p.period}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M19 9l-7 7-7-7"
                  />
                </svg>
              </div>
            </div>
          )}

          {/* Table Type Dropdown Selector */}
          <div className="relative">
            <select
              value={selectedTable}
              onChange={(e) => setSelectedTable(e.target.value as TableType)}
              className="appearance-none bg-gray-50 hover:bg-gray-100 border border-gray-200 text-gray-800 text-xs font-semibold py-2 pl-3 pr-8 rounded-xl cursor-pointer focus:outline-none focus:ring-2 focus:ring-blue-500/20 transition shadow-sm"
            >
              {TABLE_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
            <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-500">
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </div>
          </div>

          {/* Search Bar */}
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search reference ID / UTR..."
              className="bg-gray-50 border border-gray-200 text-xs rounded-xl py-1.5 px-3 pl-8 text-gray-800 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500/20 w-44 md:w-56"
            />
            <svg
              className="w-3.5 h-3.5 text-gray-400 absolute left-2.5 top-2"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
          </div>

          {/* Back Button */}
          <button
            onClick={onBack}
            className="px-3.5 py-1.5 rounded-xl bg-gray-100 hover:bg-gray-200 text-xs font-semibold text-gray-700 transition"
          >
            ← Back to Dashboard
          </button>
        </div>
      </div>

      {/* Main Table Body */}
      <div className="flex-1 min-h-0 bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden flex flex-col">
        {loading ? (
          <div className="flex-1 flex items-center justify-center text-xs text-gray-400">
            Querying PostgreSQL database records for {selectedPeriod}...
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto min-h-0">
            {/* 1. EXCEPTIONS TABLE */}
            {selectedTable === "exceptions" && currentSummary && (
              <table className="w-full table-fixed text-left text-xs">
                <colgroup>
                  <col className="w-[16%]" />
                  <col className="w-[22%]" />
                  <col className="w-[32%]" />
                  <col className="w-[15%]" />
                  <col className="w-[15%]" />
                </colgroup>
                <thead className="sticky top-0 bg-gray-50 z-10 border-b border-gray-100 text-gray-500 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Payment ID</th>
                    <th className="py-2.5 px-3">Reason</th>
                    <th className="py-2.5 px-3">Recommended Action</th>
                    <th className="py-2.5 px-3 text-right">Amount</th>
                    <th className="py-2.5 px-3 text-center">Risk Tier</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {currentSummary.exceptions
                    .filter((e) =>
                      e.paymentId
                        .toLowerCase()
                        .includes(searchQuery.toLowerCase()),
                    )
                    .map((e) => (
                      <tr
                        key={e.paymentId}
                        onClick={() => setInspectingPaymentId(e.paymentId)}
                        className="hover:bg-blue-50/40 cursor-pointer transition"
                      >
                        <td className="py-2.5 px-3 font-mono font-medium text-gray-800 truncate">
                          {e.paymentId}{" "}
                          <span className="text-[10px] text-blue-600">↗</span>
                        </td>
                        <td className="py-2.5 px-3 text-gray-700 truncate">
                          {e.reasonLabel}
                        </td>
                        <td
                          className="py-2.5 px-3 text-gray-500 truncate"
                          title={e.recommendedAction}
                        >
                          {e.recommendedAction}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-gray-900">
                          {formatInr(e.amount)}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span
                            className={`inline-block text-[10px] px-2 py-0.5 uppercase font-bold ${RISK_BADGES[e.risk]}`}
                          >
                            {e.risk}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* 2. RECONCILED MATCHES */}
            {selectedTable === "ledger_matches" && tableData && (
              <table className="w-full table-fixed text-left text-xs">
                <colgroup>
                  <col className="w-[14%]" />
                  <col className="w-[12%]" />
                  <col className="w-[14%]" />
                  <col className="w-[14%]" />
                  <col className="w-[34%]" />
                  <col className="w-[12%]" />
                </colgroup>
                <thead className="sticky top-0 bg-gray-50 z-10 border-b border-gray-100 text-gray-500 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="py-2.5 px-3">Payment ID</th>
                    <th className="py-2.5 px-3">Match Type</th>
                    <th className="py-2.5 px-3 text-right">Gateway Amount</th>
                    <th className="py-2.5 px-3 text-right">Bank Settled</th>
                    <th className="py-2.5 px-3">Explanation</th>
                    <th className="py-2.5 px-3 text-center">Risk</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tableData.ledger_matches
                    .filter((m) =>
                      m.payment_id
                        .toLowerCase()
                        .includes(searchQuery.toLowerCase()),
                    )
                    .map((m, i) => (
                      <tr
                        key={i}
                        onClick={() => setInspectingPaymentId(m.payment_id)}
                        className="hover:bg-blue-50/40 cursor-pointer transition"
                      >
                        <td className="py-2.5 px-3 font-mono text-gray-800 font-medium truncate">
                          {m.payment_id}{" "}
                          <span className="text-[10px] text-blue-600">↗</span>
                        </td>
                        <td className="py-2.5 px-3">
                          <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">
                            {m.match_type}
                          </span>
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-gray-900">
                          {formatInr(m.matched_amount)}
                        </td>
                        <td className="py-2.5 px-3 text-right font-semibold text-gray-900">
                          {formatInr(m.bank_amount)}
                        </td>
                        <td
                          className="py-2.5 px-3 text-gray-500 text-[11px] truncate"
                          title={m.explanation}
                        >
                          {m.explanation}
                        </td>
                        <td className="py-2.5 px-3 text-center">
                          <span
                            className={`inline-block text-[10px] px-2 py-0.5 uppercase font-bold ${RISK_BADGES[m.risk]}`}
                          >
                            {m.risk}
                          </span>
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* 3. GATEWAY RECORDS */}
            {selectedTable === "gateway" && tableData && (
              <table className="w-full table-fixed text-left text-xs">
                <thead className="sticky top-0 bg-gray-50 z-10 border-b border-gray-100 text-gray-500 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="w-[22%] py-2.5 px-4">Payment ID</th>
                    <th className="w-[18%] py-2.5 px-4">Order ID</th>
                    <th className="w-[18%] py-2.5 px-4">UTR</th>
                    <th className="w-[14%] py-2.5 px-4 text-right">Amount</th>
                    <th className="w-[12%] py-2.5 px-4 text-center">Status</th>
                    <th className="w-[16%] py-2.5 px-4">Created At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tableData.gateway_records
                    .filter(
                      (g) =>
                        g.payment_id
                          .toLowerCase()
                          .includes(searchQuery.toLowerCase()) ||
                        g.order_id
                          .toLowerCase()
                          .includes(searchQuery.toLowerCase()),
                    )
                    .map((g) => (
                      <tr
                        key={g.payment_id}
                        onClick={() => setInspectingPaymentId(g.payment_id)}
                        className="hover:bg-blue-50/40 cursor-pointer transition"
                      >
                        <td className="w-[22%] py-2.5 px-4 font-mono font-medium text-gray-800 truncate">
                          {g.payment_id}{" "}
                          <span className="text-[10px] text-blue-600">↗</span>
                        </td>
                        <td className="w-[18%] py-2.5 px-4 font-mono text-gray-600 truncate">
                          {g.order_id}
                        </td>
                        <td className="w-[18%] py-2.5 px-4 font-mono text-gray-600 truncate">
                          {g.utr || "—"}
                        </td>
                        <td className="w-[14%] py-2.5 px-4 text-right font-semibold text-gray-900">
                          {formatInr(g.amount)}
                        </td>
                        <td className="w-[12%] py-2.5 px-4 text-center">
                          <span className="bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded text-[10px] font-semibold uppercase">
                            {g.status}
                          </span>
                        </td>
                        <td className="w-[16%] py-2.5 px-4 text-gray-500 text-[11px] truncate">
                          {formatDate(g.created_at)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* 4. BANK RECORDS */}
            {selectedTable === "bank" && tableData && (
              <table className="w-full table-fixed text-left text-xs">
                <thead className="sticky top-0 bg-gray-50 z-10 border-b border-gray-100 text-gray-500 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="w-[20%] py-2.5 px-4">Bank UTR</th>
                    <th className="w-[30%] py-2.5 px-4">Narration</th>
                    <th className="w-[16%] py-2.5 px-4 text-right">
                      Credited Amount
                    </th>
                    <th className="w-[16%] py-2.5 px-4">Credited At</th>
                    <th className="w-[18%] py-2.5 px-4">Linked Payments</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tableData.bank_records
                    .filter((b) =>
                      b.utr.toLowerCase().includes(searchQuery.toLowerCase()),
                    )
                    .map((b) => (
                      <tr key={b.id} className="hover:bg-gray-50/70 transition">
                        <td className="w-[20%] py-2.5 px-4 font-mono text-gray-800 font-medium truncate">
                          {b.utr}
                        </td>
                        <td
                          className="w-[30%] py-2.5 px-4 text-gray-600 truncate"
                          title={b.narration}
                        >
                          {b.narration}
                        </td>
                        <td className="w-[16%] py-2.5 px-4 text-right font-semibold text-gray-900">
                          {formatInr(b.amount)}
                        </td>
                        <td className="w-[16%] py-2.5 px-4 text-gray-500 text-[11px] truncate">
                          {formatDate(b.credited_at)}
                        </td>
                        <td
                          className="w-[18%] py-2.5 px-4 font-mono text-gray-500 text-[11px] truncate"
                          title={b.linked_payment_ids || undefined}
                        >
                          {b.linked_payment_ids || "—"}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}

            {/* 5. MERCHANT RECORDS */}
            {selectedTable === "merchant" && tableData && (
              <table className="w-full table-fixed text-left text-xs">
                <thead className="sticky top-0 bg-gray-50 z-10 border-b border-gray-100 text-gray-500 font-semibold uppercase text-[10px]">
                  <tr>
                    <th className="w-[24%] py-2.5 px-4">Order ID</th>
                    <th className="w-[24%] py-2.5 px-4">Linked Payment ID</th>
                    <th className="w-[18%] py-2.5 px-4 text-right">
                      Claimed Amount
                    </th>
                    <th className="w-[14%] py-2.5 px-4 text-center">Status</th>
                    <th className="w-[20%] py-2.5 px-4">Marked Paid At</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {tableData.merchant_records
                    .filter((m) =>
                      m.order_id
                        .toLowerCase()
                        .includes(searchQuery.toLowerCase()),
                    )
                    .map((m, i) => (
                      <tr
                        key={i}
                        onClick={() =>
                          m.payment_id && setInspectingPaymentId(m.payment_id)
                        }
                        className={`${m.payment_id ? "hover:bg-blue-50/40 cursor-pointer" : ""} transition`}
                      >
                        <td className="w-[24%] py-2.5 px-4 font-mono text-gray-800 font-medium truncate">
                          {m.order_id}
                        </td>
                        <td className="w-[24%] py-2.5 px-4 font-mono text-gray-600 truncate">
                          {m.payment_id ? (
                            <span className="text-blue-600 font-medium">
                              {m.payment_id} ↗
                            </span>
                          ) : (
                            "—"
                          )}
                        </td>
                        <td className="w-[18%] py-2.5 px-4 text-right font-semibold text-gray-900">
                          {formatInr(m.amount)}
                        </td>
                        <td className="w-[14%] py-2.5 px-4 text-center">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              m.status === "paid"
                                ? "text-emerald-700"
                                : " text-amber-700"
                            }`}
                          >
                            {m.status}
                          </span>
                        </td>
                        <td className="w-[20%] py-2.5 px-4 text-gray-500 text-[11px] truncate">
                          {formatDate(m.marked_paid_at)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      {/* Rendered once globally at root level */}
      <InspectionModal
        paymentId={inspectingPaymentId}
        period={selectedPeriod}
        onClose={() => setInspectingPaymentId(null)}
      />
    </div>
  );
};

export default TablesView;