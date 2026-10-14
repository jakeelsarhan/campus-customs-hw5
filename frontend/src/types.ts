export type Ticket = {
  id: number
  type: string
  requester: string
  subject: string
  status: string
  board_state: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  notes: string | null
  created_at: string | null
}

export type AgentEvent = {
  time?: string
  run_id?: string
  agent?: string
  step?: string
  said?: unknown
  tool?: string | null
  detail?: Record<string, unknown>
}

export type TeamDecision = {
  ticket_id: number
  status: string
  decision: string
  needs_human_approval: boolean
  human_action: string | null
  drafts_on_board: string[]
  agents_involved: string[]
}

export type RunResult = {
  ticket: Ticket
  decision: TeamDecision
  model: string
}

export type Cash = {
  name: string
  balance: number
  date: string
}

export type AgentId =
  | 'boss'
  | 'inventory'
  | 'accounting'
  | 'facilities'
  | 'customer_service'

export const AGENTS: { id: AgentId; label: string; blurb: string }[] = [
  { id: 'boss', label: 'Boss', blurb: 'Triage & final calls' },
  { id: 'inventory', label: 'Inventory', blurb: 'Stock & vendors' },
  { id: 'accounting', label: 'Accounting', blurb: 'Cash & margins' },
  { id: 'facilities', label: 'Facilities', blurb: 'Lease & rent' },
  { id: 'customer_service', label: 'Customer Service', blurb: 'Board drafts only' },
]
