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

export async function askQuestion(
  question: string,
  period: string,
  convoId: string
): Promise<string> {
  const res = await fetch(`${API_BASE}/intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: question,
      period,
      convo_id: convoId,
      user_department: "finance",
      user_role: "viewer",
      user_id: "demo-user",
    }),
  })
  if (!res.ok) throw new Error("Failed to get an answer")
  const data = await res.json()
  return data.response as string
}