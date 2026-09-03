import React from "react";
import { ReconciliationSummary } from "../types/types";
import { LuFileWarning, LuShieldCheck } from "react-icons/lu";
import { HiOutlineExclamationTriangle } from "react-icons/hi2";
import { MdOutlineAccountBalanceWallet } from "react-icons/md";

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
      iconBg: "text-gray-600",
      icon: <LuFileWarning className="w-4 h-4" />,
    },
    {
      label: "Auto-Match Rate",
      value: `${summary.matchRate.toFixed(1)}%`,
      badge: summary.matchRate >= 95 ? "On target" : "Below target",
      badgeType: summary.matchRate >= 95 ? "positive" : "negative",
      subtext: "Target: 95.0%",
      iconBg: "text-gray-600",
      icon: <LuShieldCheck className="w-4 h-4" />,
    },
    {
      label: "High-Risk Exceptions",
      value: summary.exceptions
        .filter((e) => e.risk === "high")
        .length.toString(),
      badge: summary.exceptions.length > 0 ? "Action needed" : "Clean",
      badgeType: summary.exceptions.length > 0 ? "negative" : "neutral",
      subtext: "Requires Review",
      iconBg: "text-gray-600",
      icon: <HiOutlineExclamationTriangle className="w-4 h-4" />,
    },
    {
      label: "Amount at Risk",
      value: formatInr(summary.amountAtRisk),
      badge: "Pending",
      badgeType: "neutral",
      subtext: "Unallocated Balance",
      iconBg: "text-gray-600",
      icon: <MdOutlineAccountBalanceWallet className="w-4 h-4" />,
    },
  ];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {cards.map((c) => (
        <div
          key={c.label}
          className="bg-white rounded-3xl px-5 py-3.5 border border-slate-100/80 shadow-[0_12px_24px_-8px_rgba(15,23,42,0.12),0_4px_8px_-2px_rgba(15,23,42,0.06)] hover:shadow-[0_18px_30px_-10px_rgba(15,23,42,0.16),0_6px_10px_-3px_rgba(15,23,42,0.08)] hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-bold text-gray-800 tracking-tight">
              {c.label}
            </span>
            <div className={`p-2 rounded-xl ${c.iconBg}`}>{c.icon}</div>
          </div>
          <div>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-bold text-gray-900 tracking-tight">
                {c.value}
              </span>
              <span
                className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${
                  c.badgeType === "positive"
                    ? " text-emerald-600"
                    : c.badgeType === "negative"
                      ? " text-rose-600"
                      : "text-gray-600"
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
