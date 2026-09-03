import { ReconciliationSummary, MonthlyRiskPoint,PeriodStatus, TransactionInspectionDetails, AuditRun, AllTableRecords } from "../types/types"

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

let cachedToken: string | null = null

async function getToken(): Promise<string> {
  if (cachedToken) return cachedToken
  const res = await fetch(`${API_BASE}/auth/token`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id: "demo-user", role: "viewer" }),
  })
  if (!res.ok) throw new Error("Failed to get an auth token")
  const data = await res.json()
  const token: string = data.token
  cachedToken = token
  return token
}

async function authedFetch(url: string, options: RequestInit = {}): Promise<Response> {
  const token = await getToken()
  return fetch(url, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
    },
  })
}

export async function fetchPeriods(): Promise<PeriodStatus[]> {
  const res = await authedFetch(`${API_BASE}/api/reconciliation/periods`)
  if (!res.ok) throw new Error("Failed to load periods")
  return res.json()
}

export async function fetchSummary(period: string): Promise<ReconciliationSummary> {
  const res = await authedFetch(`${API_BASE}/api/reconciliation/summary?period=${period}`)
  if (!res.ok) throw new Error("Failed to load summary")
  return res.json()
}

export async function runReconciliation(period: string): Promise<ReconciliationSummary> {
  const res = await authedFetch(`${API_BASE}/api/reconciliation/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ period }),
  })
  if (!res.ok) throw new Error("Failed to run reconciliation")
  return res.json()
}

export async function fetchAuditLog(period: string) {
  const res = await authedFetch(`${API_BASE}/api/audit-trail?period=${encodeURIComponent(period)}`);
  if (!res.ok) throw new Error("Failed to fetch audit trail");
  const data = await res.json();
  return data.records || [];
}

export async function askQuestion(
  question: string,
  period: string,
  convoId: string
): Promise<string> {
  const res = await authedFetch(`${API_BASE}/intent`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: question, period, convo_id: convoId }),
  })
  if (!res.ok) throw new Error("Failed to get an answer")
  const data = await res.json()
  return data.response as string
}

export async function fetchAllTables(period: string): Promise<AllTableRecords> {
  const res = await fetch(`http://localhost:8000/api/reconciliation/tables?period=${encodeURIComponent(period)}`)
  if (!res.ok) {
    throw new Error(`Failed to fetch tables for period ${period}`)
  }
  return res.json()
}

export async function fetchTransactionInspection(
  paymentId: string,
  period: string
): Promise<TransactionInspectionDetails> {
  const res = await fetch(
    `http://localhost:8000/api/reconciliation/transaction/${encodeURIComponent(paymentId)}?period=${encodeURIComponent(period)}`
  )
  if (!res.ok) {
    throw new Error(`Failed to fetch inspection details for ${paymentId}`)
  }
  return res.json()
}

export async function fetchRiskTrends(): Promise<MonthlyRiskPoint[]> {
  const res = await fetch("http://localhost:8000/api/reconciliation/trends")
  if (!res.ok) throw new Error("Failed to fetch risk trends")
  return res.json()
}