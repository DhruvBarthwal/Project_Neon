import React from "react";
import { ReconciliationSummary } from "../types/types";

interface Props {
  summary: ReconciliationSummary;
}

function formatInr(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

const Metrics = ({ summary }: Props) => {
  const cards = [
    {
      label: "Exception Rate",
      value: `${summary.exceptionRate}%`,
      badge: summary.exceptionRate > 5 ? "Above target" : "On target",
      badgeType: summary.exceptionRate > 5 ? "negative" : "positive",
      subtext: `${summary.exceptions.length} of ${summary.totalRecords} records`,
      icon: (
        <svg
          className="w-4 h-4 text-blue-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
      ),
    },
    {
      label: "Auto-Match Rate",
      value: `${summary.matchRate.toFixed(1)}%`,
      badge: summary.matchRate >= 95 ? "On target" : "Below target",
      badgeType: summary.matchRate >= 95 ? "positive" : "negative",
      subtext: "target: 95.0%",
      icon: (
        <svg
          className="w-4 h-4 text-emerald-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M5 13l4 4L19 7"
          />
        </svg>
      ),
    },
    {
      label: "High-Risk Exceptions",
      value: summary.exceptions
        .filter((e) => e.risk === "high")
        .length.toString(),
      badge: summary.exceptions.length > 0 ? "Action needed" : "Clean",
      badgeType: summary.exceptions.length > 0 ? "negative" : "neutral",
      subtext: "requires review",
      icon: (
        <svg
          className="w-4 h-4 text-amber-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
          />
        </svg>
      ),
    },
    {
      label: "Amount at Risk",
      value: formatInr(summary.amountAtRisk),
      badge: "Pending",
      badgeType: "neutral",
      subtext: "unallocated balance",
      icon: (
        <svg
          className="w-4 h-4 text-purple-500"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="bg-white rounded-3xl px-5 py-2 border border-gray-100 shadow-[0_2px_10px_-4px_rgba(0,0,0,0.04)] flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-gray-500 tracking-wide">
              {c.label}
            </span>
            <div className="p-2 bg-gray-50 rounded-xl">{c.icon}</div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900 tracking-tight">
                {c.value}
              </span>
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                  c.badgeType === "positive"
                    ? "bg-emerald-50 text-emerald-600"
                    : c.badgeType === "negative"
                      ? "bg-rose-50 text-rose-600"
                      : "bg-gray-100 text-gray-600"
                }`}
              >
                {c.badge}
              </span>
            </div>
            <p className="text-[11px] text-gray-400 mt-1">{c.subtext}</p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default Metrics;
