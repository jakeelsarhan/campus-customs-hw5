import type { Cash, RunResult, Ticket, AgentEvent } from './types'

/** Direct to FastAPI (CORS allows Vite origin). */
export const API_BASE = 'http://localhost:8000'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  })
  if (!res.ok) {
    let detail: unknown
    try {
      detail = await res.json()
    } catch {
      detail = await res.text()
    }
    throw new Error(
      typeof detail === 'object' && detail && 'detail' in detail
        ? JSON.stringify((detail as { detail: unknown }).detail)
        : `HTTP ${res.status}`,
    )
  }
  return res.json() as Promise<T>
}

export function getTickets() {
  return request<{ tickets: Ticket[] }>('/api/tickets')
}

export function getCash() {
  return request<Cash>('/api/cash')
}

export function getEvents(limit = 120, runId?: string) {
  const q = new URLSearchParams({ limit: String(limit) })
  if (runId) q.set('run_id', runId)
  return request<{ count: number; events: AgentEvent[] }>(`/api/events?${q}`)
}

export function runTicket(ticketId: number, extra = '') {
  return request<RunResult>(`/api/tickets/${ticketId}/run`, {
    method: 'POST',
    body: JSON.stringify({ extra }),
  })
}

export function approvePayment(body: {
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
  approved_by: string
  account?: string
}) {
  return request<{ payment: Record<string, unknown>; cash: Cash }>(
    '/api/payments/approve',
    { method: 'POST', body: JSON.stringify(body) },
  )
}

export function resetDatabase() {
  return request<{ ok: boolean; cash: Cash; tickets: Ticket[] }>('/api/reset', {
    method: 'POST',
  })
}
