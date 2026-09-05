"use client";

import React, { useEffect, useState } from "react";
import { MonthlyRiskPoint } from "../types/types";
import { fetchRiskTrends } from "../connection/api";

interface Props {
  currentPeriod: string;
  onSelectPeriod?: (period: string) => void;
}

function formatInrCompact(amount: number) {
  if (amount >= 10000000) return `₹${(amount / 10000000).toFixed(1)}Cr`;
  if (amount >= 100000) return `₹${(amount / 100000).toFixed(1)}L`;
  if (amount >= 1000) return `₹${(amount / 1000).toFixed(0)}k`;
  return `₹${amount.toFixed(0)}`;
}

function formatInrFull(amount: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(amount);
}

const TrendChart = ({ currentPeriod, onSelectPeriod }: Props) => {
  const [trends, setTrends] = useState<MonthlyRiskPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchRiskTrends()
      .then(setTrends)
      .catch((err) => console.error("Error loading risk trends:", err))
      .finally(() => setLoading(false));
  }, []);

  if (loading || trends.length === 0) {
    return (
      <div className="bg-white rounded-2xl p-4 border border-gray-100 shadow-sm h-48 flex items-center justify-center text-xs text-gray-400">
        Loading historical risk trajectory...
      </div>
    );
  }

  // Dimensions with safe headrooms for tooltips and Y-axis labels
  const width = 640;
  const height = 160;
  const padLeft = 70;
  const padRight = 35;
  const padTop = 32; // Extra headroom so floating tooltips don't clip at top
  const padBottom = 28;

  const maxRiskVal = Math.max(...trends.map((t) => t.amountAtRisk), 0);
  const maxVal = maxRiskVal > 0 ? maxRiskVal * 1.15 : 10000;
  const minVal = 0;

  // 4 Horizontal Y-axis Ticks
  const yTicksCount = 4;
  const yTicks = Array.from({ length: yTicksCount }, (_, i) => {
    const val = minVal + (i / (yTicksCount - 1)) * (maxVal - minVal);
    const yPos =
      height -
      padBottom -
      (i / (yTicksCount - 1)) * (height - padTop - padBottom);
    return { val, yPos };
  });

  // Calculate coordinates for all available points
  const points = trends.map((t, idx) => {
    const x =
      trends.length === 1
        ? (width - padLeft - padRight) / 2 + padLeft
        : padLeft + (idx / (trends.length - 1)) * (width - padLeft - padRight);

    const y =
      height -
      padBottom -
      ((t.amountAtRisk - minVal) / (maxVal - minVal)) *
        (height - padTop - padBottom);

    return { ...t, x, y };
  });

  const pathString = points.reduce((acc, p, idx) => {
    return `${acc} ${idx === 0 ? "M" : "L"} ${p.x} ${p.y}`;
  }, "");

  const activePoint =
    points.find((p) => p.period === currentPeriod) || points[points.length - 1];

  return (
    <div className="bg-white rounded-3xl p-5 border border-slate-100/90 border-t-white shadow-[0_14px_30px_-8px_rgba(15,23,42,0.12),0_4px_10px_-2px_rgba(15,23,42,0.05),inset_0_1px_0_rgba(255,255,255,0.9)] hover:shadow-[0_20px_35px_-10px_rgba(15,23,42,0.15),0_6px_12px_-3px_rgba(15,23,42,0.07)] hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between">
      {/* Header Info */}
      <div className="flex items-center justify-between pb-2 flex-shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-bold text-xs text-gray-900 uppercase tracking-wide">
              Monthly Financial Exposure
            </h3>
            <span className="text-[10px] text-gray-400 font-mono">
              Amount at Risk Trend
            </span>
          </div>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Viewing:{" "}
            <span className="font-semibold text-gray-900">
              {activePoint.label}
            </span>{" "}
            —{" "}
            <span className="font-mono font-bold text-rose-600">
              {formatInrFull(activePoint.amountAtRisk)}
            </span>{" "}
            at risk
          </p>
        </div>

        <div className="flex items-center gap-1.5 bg-gray-100 border border-rose-100 px-2.5 py-1 rounded-xl">
          <span className="w-2 h-2 rounded-full bg-gray-500 animate-pulse" />
          <span className="text-[10px] font-bold text-gray-700">
            {activePoint.exceptionCount} Active Exceptions
          </span>
        </div>
      </div>

      {/* SVG Canvas with X & Y Axes */}
      <div className="relative w-full h-[155px] mt-1">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
        >
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#091B31" stopOpacity="0.22" />
              <stop offset="100%" stopColor="#A66565" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Y-Axis Horizontal Grid Lines & Ticks */}
          {yTicks.map((tick, i) => (
            <g key={i}>
              <line
                x1={padLeft}
                y1={tick.yPos}
                x2={width - padRight}
                y2={tick.yPos}
                stroke="#f1f5f9"
                strokeDasharray={i === 0 ? "none" : "3 3"}
                strokeWidth={i === 0 ? "1.5" : "1"}
              />
              <text
                x={padLeft - 10}
                y={tick.yPos}
                dominantBaseline="middle"
                textAnchor="end"
                fontSize="9"
                fill="#94a3b8"
                fontFamily="monospace"
                fontWeight="500"
              >
                {formatInrCompact(tick.val)}
              </text>
            </g>
          ))}

          {/* Left Vertical Axis Line */}
          <line
            x1={padLeft}
            y1={padTop}
            x2={padLeft}
            y2={height - padBottom}
            stroke="#e2e8f0"
            strokeWidth="1.5"
          />

          {/* Area Fill Under Curve (Requires >= 2 points) */}
          {points.length > 1 && (
            <path
              d={`${pathString} L ${points[points.length - 1].x} ${height - padBottom} L ${points[0].x} ${height - padBottom} Z`}
              fill="url(#riskGradient)"
            />
          )}

          {/* Risk Trend Path */}
          {points.length > 1 && (
            <path
              d={pathString}
              fill="none"
              stroke="#918181"
              strokeWidth="2.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          )}

          {/* Active Period Vertical Guide Line */}
          {activePoint && (
            <line
              x1={activePoint.x}
              y1={padTop}
              x2={activePoint.x}
              y2={height - padBottom}
              stroke="#07152B"
              strokeDasharray="2 2"
              strokeWidth="1.5"
            />
          )}

          {/* Data Points & Interactive Nodes */}
          {points.map((p) => {
            const isCurrent = p.period === currentPeriod;
            return (
              <g
                key={p.period}
                className="cursor-pointer group"
                onClick={() => onSelectPeriod && onSelectPeriod(p.period)}
              >
                {/* Ping pulse for active month */}
                {isCurrent && (
                  <>
                    <circle
                      cx={p.x}
                      cy={p.y}
                      r="5"
                      fill="#030B17"
                      fillOpacity="0.3"
                      stroke="#00040A"
                      strokeWidth="1.5"
                    >
                      <animate
                        attributeName="r"
                        values="5;11;5"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                      <animate
                        attributeName="opacity"
                        values="0.8;0;0.8"
                        dur="2s"
                        repeatCount="indefinite"
                      />
                    </circle>
                  </>
                )}

                {/* Point circle */}
                <circle
                  cx={p.x}
                  cy={p.y}
                  r={isCurrent ? "5" : "3.5"}
                  className={
                    isCurrent
                      ? "fill-gray-600 stroke-white"
                      : "fill-white stroke-rose-400 group-hover:stroke-rose-600"
                  }
                  strokeWidth={isCurrent ? "2" : "1.5"}
                />

                {/* Floating pill badge */}
                {isCurrent && (
                  <g transform={`translate(${p.x}, ${Math.max(p.y - 14, 18)})`}>
                    <rect
                      x="-32"
                      y="-16"
                      width="64"
                      height="16"
                      rx="4"
                      fill="#0f172a"
                      className="drop-shadow-sm"
                    />
                    <text
                      x="0"
                      y="-5"
                      textAnchor="middle"
                      fill="#ffffff"
                      fontSize="9"
                      fontWeight="bold"
                      fontFamily="monospace"
                    >
                      {formatInrCompact(p.amountAtRisk)}
                    </text>
                  </g>
                )}

                {/* X-Axis Month Label */}
                <text
                  x={p.x}
                  y={height - 10}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight={isCurrent ? "bold" : "500"}
                  className={isCurrent ? "fill-gray-600" : "fill-gray-400"}
                >
                  {p.label.split(" ")[0]}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};

export default TrendChart;
