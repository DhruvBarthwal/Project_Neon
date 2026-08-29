import { ReconciliationSummary, PeriodStatus } from "../types/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export async function fetchPeriods(): Promise<PeriodStatus[]> {
  const res = await fetch(`${API_BASE}/api/reconciliation/periods`)
  if (!res.ok) throw new Error("Failed to load periods")
  return res.json()
}

export async function fetchSummary(period: string): Promise<ReconciliationSummary> {
  const res = await fetch(`${API_BASE}/api/reconciliation/summary?period=${period}`)
  if (!res.ok) throw new Error("Failed to load summary")
  return res.json()
}

export async function runReconciliation(period: string): Promise<ReconciliationSummary> {
  const res = await fetch(`${API_BASE}/api/reconciliation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period }),
  })
  if (!res.ok) throw new Error("Failed to run reconciliation")
  return res.json()
}