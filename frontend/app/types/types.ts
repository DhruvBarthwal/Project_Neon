export type MatchType = "exact" | "fuzzy" | "lump_sum" | "fee_aware"
export type RiskLevel = "low" | "medium" | "high" | "critical"

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
  reasonLabel: string        
  amount: number
  recommendedAction?: string      
  recommended_action?: string
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

export interface AuditRun {
  period: string
  triggeredBy: string
  triggerSource: "manual" | "auto_qa"
  totalRecords: number
  matchedCount: number
  exceptionCount: number
  matchRate: number
  runAt: string  
}

export interface AllTableRecords {
  period: string
  ledger_matches: Array<{
    payment_id: string
    match_type: MatchType
    matched_amount: number
    bank_amount: number
    risk: RiskLevel
    explanation: string
  }>
  gateway_records: Array<{
    payment_id: string
    order_id: string
    amount: number
    status: string
    utr: string | null
    created_at: string
    scenario: string
  }>
  bank_records: Array<{
    id: number
    utr: string
    amount: number
    credited_at: string
    narration: string
    linked_payment_ids: string | null
  }>
  merchant_records: Array<{
    order_id: string
    payment_id: string | null
    amount: number
    status: string
    marked_paid_at: string | null
    scenario: string
  }>
}

export interface TransactionInspectionDetails {
  payment_id: string
  period: string
  status: "exception" | "matched" | "unprocessed"
  gateway: {
    payment_id: string
    order_id: string
    amount: number
    status: string
    utr: string | null
    created_at: string
    scenario: string
  } | null
  bank: {
    id: number
    utr: string
    amount: number
    credited_at: string
    narration: string
    linked_payment_ids: string | null
  } | null
  merchant: {
    order_id: string
    payment_id: string | null
    amount: number
    status: string
    marked_paid_at: string | null
    scenario: string
  } | null
  reconciled_match: {
    match_type: string
    matched_amount: number
    bank_amount: number
    risk: RiskLevel
    explanation: string
  } | null
  exception: {
    reason_code: string
    reason_detail: string | null
    recommended_action: string | null
    risk: RiskLevel
    amount: number
  } | null
}

export interface MonthlyRiskPoint {
  period: string
  label: string
  amountAtRisk: number
  exceptionCount: number
}

export interface AuditLogEntry {
  id: string;
  created_at: string;
  period: string;
  actor: string;
  event_type: "CYCLE_RUN" | "RECORD_AUDIT" | string;
  intent: string;
  target_identifier: string;
  outcome_status: string;
  exposure_amount: number | string;
  metadata: Record<string, any>;
}
