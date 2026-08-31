import React, { useEffect, useState } from "react"
import { AuditRun } from "../types/types"
import { fetchAuditLog } from "../connection/api"

interface Props {
  period: string
}

function formatDateTime(iso: string) {
  return new Date(iso).toLocaleString("en-IN", {
    day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
  })
}

const SOURCE_LABELS: Record<string, string> = {
  manual: "Manual run",
  auto_qa: "Auto-run (Q&A agent)",
}

const AuditLog = ({ period }: Props) => {
  const [runs, setRuns] = useState<AuditRun[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setLoading(true)
    fetchAuditLog(period)
      .then(setRuns)
      .finally(() => setLoading(false))
  }, [period])

  if (loading) return null
  if (runs.length === 0) return null

  return (
    <div className="mx-8 mt-5 mb-8">
      <p className="text-sm text-gray-500 mb-2">Audit log — {runs.length} run(s) for {period}</p>
      <div className="bg-white rounded-2xl border border-white overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 text-gray-500 text-left">
              <th className="px-4 py-2 font-medium">When</th>
              <th className="px-4 py-2 font-medium">Triggered by</th>
              <th className="px-4 py-2 font-medium">Source</th>
              <th className="px-4 py-2 font-medium text-right">Match rate</th>
              <th className="px-4 py-2 font-medium text-right">Matched / Total</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((r, i) => (
              <tr key={i} className="border-t border-gray-100">
                <td className="px-4 py-2 text-gray-600">{formatDateTime(r.runAt)}</td>
                <td className="px-4 py-2 font-mono text-xs">{r.triggeredBy}</td>
                <td className="px-4 py-2 text-gray-600">{SOURCE_LABELS[r.triggerSource] ?? r.triggerSource}</td>
                <td className="px-4 py-2 text-right">{r.matchRate}%</td>
                <td className="px-4 py-2 text-right">{r.matchedCount} / {r.totalRecords}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default AuditLog