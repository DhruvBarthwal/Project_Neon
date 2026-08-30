export type MatchType = "exact" | "fuzzy" | "lump_sum" | "fee_aware"
export type RiskLevel = "low" | "medium" | "high"

export interface ReconciliationSummary {
  period: string
  status: "not_run" | "running" | "done"
  totalRecords: number
  matchRate: number       
  exceptionRate: number     
  amountAtRisk: number
  breakdown: Record<MatchType, number>
  exceptions: ExceptionRow[]
  highlights: LumpSumHighlight[]
}

export interface ExceptionRow {
  paymentId: string
  reasonCode: string
  reasonLabel: string        // human-readable version of reasonCode
  amount: number
  risk: RiskLevel
}

export interface LumpSumHighlight {
  utr: string
  bankAmount: number
  memberPaymentIds: string[]
  memberAmounts: number[]
  heldBackPaymentIds: string[]
}

export interface PeriodStatus {
  period: string             
  label: string            
  status: "not_run" | "running" | "done"
}

export interface ChatMessage {
  role: "user" | "assistant"
  content: string
}