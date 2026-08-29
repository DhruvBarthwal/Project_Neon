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

const LumpSumHighlights = ({ summary }: Props) => {
  if (summary.highlights.length == 0) return null;

  return (
    <div className="mx-8 mt-5 flex flex-col gap-3">
      {summary.highlights.map((h) => (
        <div
          key={h.utr}
          className="bg-purple-50 rounded-2xl p-4 flex gap-3 items-start"
        >
          <span className="text-purple-700 mt-0.5">⇄</span>
          <div>
            <p className="text-sm font-semibold text-purple-800">
              Lump-sum unbundled: {h.utr}
            </p>
            <p className="text-sm text-gray-600 mt-1">
              One bank credit of {formatInr(h.bankAmount)} decomposed into{" "}
              {h.memberPaymentIds.length} payments
              {h.heldBackPaymentIds.length > 0 && (
                <>
                  {" "}
                  — {h.heldBackPaymentIds.length} held back, flagged separately.
                </>
              )}
            </p>
          </div>
        </div>
      ))}
    </div>
  );
};

export default LumpSumHighlights;
