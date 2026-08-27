import { ReconciliationSummary, PeriodStatus } from "../types/types";

export async function fetchPeriods(): Promise<PeriodStatus[]> {
    const res = await fetch("api/reconciliation/periods")
    if(!res.ok) throw new Error("Failed to load periods")
    return res.json() 
}

export async function fetchSummary(period: string): Promise<ReconciliationSummary> {
    const res = await fetch('/api/reconciliation/summary?period=${period}')
    if(!res.ok) throw new Error("Failed to load summary")
        return res.json()
}

export async function runReconciliaton(period: string): Promise<ReconciliationSummary> {
    const res = await fetch("/api/reconcialtion/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({period}),
    })
    if (!res.ok) throw new Error("Failed to run reconciliation")
        return res.json()
}