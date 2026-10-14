import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type FormEvent,
} from 'react'
import './App.css'
import {
  approvePayment,
  getCash,
  getEvents,
  getTickets,
  resetDatabase,
  runTicket,
} from './api'
import { AGENTS, type AgentEvent, type AgentId, type Cash, type Ticket } from './types'

function money(n: number) {
  return n.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

function statusBadge(status: string, running: boolean) {
  if (running) return 'running'
  const s = status.toLowerCase()
  if (s === 'resolved') return 'resolved'
  if (s === 'waiting_approval') return 'waiting_approval'
  if (s === 'blocked') return 'blocked'
  if (s === 'open') return 'open'
  return ''
}

function suggestPay(ticket: Ticket | null): {
  kind: 'invoice' | 'rent'
  ref_id: number
  amount: number
} {
  if (ticket?.type === 'rent_notice' && ticket.lease_id) {
    return { kind: 'rent', ref_id: ticket.lease_id, amount: 2400 }
  }
  if (ticket?.invoice_id) {
    return { kind: 'invoice', ref_id: ticket.invoice_id, amount: 840 }
  }
  return { kind: 'invoice', ref_id: 501, amount: 840 }
}

function lineFromEvent(ev: AgentEvent): string {
  if (ev.tool && ev.step === 'mcp_tool_call') return `→ tool ${ev.tool}`
  if (ev.tool && ev.step === 'mcp_tool_result') return `← ${ev.tool} returned`
  if (typeof ev.said === 'string' && ev.said.trim()) return ev.said
  if (ev.said && typeof ev.said === 'object') {
    try {
      return JSON.stringify(ev.said)
    } catch {
      return String(ev.step)
    }
  }
  return ev.step || '…'
}

function summarizeAgent(events: AgentEvent[], agent: AgentId): string {
  const mine = events.filter((e) => e.agent === agent)
  if (!mine.length) return 'Quiet this run.'
  const tools = [
    ...new Set(
      mine
        .filter((e) => e.step === 'mcp_tool_call' && e.tool)
        .map((e) => e.tool as string),
    ),
  ]
  const speech = mine
    .filter((e) => e.step === 'delegate_result' || e.step === 'run_end')
    .map((e) => (typeof e.said === 'string' ? e.said : ''))
    .filter(Boolean)
  const last = speech.at(-1)
  const toolBit = tools.length ? `Tools: ${tools.slice(0, 4).join(', ')}.` : 'No MCP tools.'
  if (last) return `${toolBit} ${last.slice(0, 140)}${last.length > 140 ? '…' : ''}`
  const delegate = mine.find((e) => e.step === 'delegate')
  if (delegate && typeof delegate.said === 'string') return `${toolBit} ${delegate.said}`
  return toolBit
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(101)
  const [cash, setCash] = useState<Cash | null>(null)
  const [cashPulse, setCashPulse] = useState(false)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [activeRunId, setActiveRunId] = useState<string | null>(null)
  const [running, setRunning] = useState(false)
  const [runFinishedIds, setRunFinishedIds] = useState<Set<number>>(new Set())
  const [needsHuman, setNeedsHuman] = useState(false)
  const [humanNote, setHumanNote] = useState<string | null>(null)
  const [decisionText, setDecisionText] = useState('')
  const [status, setStatus] = useState<string>('Loading desk…')
  const [error, setError] = useState<string | null>(null)
  const pollRef = useRef<number | null>(null)

  const selected = tickets.find((t) => t.id === selectedId) || null
  const suggestion = suggestPay(selected)

  const [kind, setKind] = useState<'invoice' | 'rent'>(suggestion.kind)
  const [refId, setRefId] = useState(suggestion.ref_id)
  const [amount, setAmount] = useState(suggestion.amount)
  const [approvedBy, setApprovedBy] = useState('')

  useEffect(() => {
    setKind(suggestion.kind)
    setRefId(suggestion.ref_id)
    setAmount(suggestion.amount)
  }, [suggestion.kind, suggestion.ref_id, suggestion.amount])

  const refreshBoard = useCallback(async () => {
    const [t, c] = await Promise.all([getTickets(), getCash()])
    setTickets(t.tickets)
    setCash(c)
  }, [])

  useEffect(() => {
    refreshBoard()
      .then(() => setStatus('Desk ready. Pick a ticket and run the team.'))
      .catch((e: Error) => {
        setError(e.message)
        setStatus('Backend unreachable — is uvicorn on :8000?')
      })
  }, [refreshBoard])

  const stopPoll = () => {
    if (pollRef.current != null) {
      window.clearInterval(pollRef.current)
      pollRef.current = null
    }
  }

  useEffect(() => () => stopPoll(), [])

  const pullEvents = useCallback(async () => {
    const res = await getEvents(160)
    setEvents(res.events)
    if (!activeRunId) {
      const last = [...res.events].reverse().find((e) => e.run_id && e.run_id !== 'human-approve')
      if (last?.run_id) setActiveRunId(last.run_id)
    }
  }, [activeRunId])

  const onRun = async () => {
    if (!selectedId || running) return
    setError(null)
    setNeedsHuman(false)
    setHumanNote(null)
    setDecisionText('')
    setRunning(true)
    setStatus(`Running agents on ticket ${selectedId}…`)
    setActiveRunId(null)
    const before = await getEvents(160)
    const seen = new Set(before.events.map((e) => `${e.time}-${e.step}-${e.agent}`))

    stopPoll()
    pollRef.current = window.setInterval(() => {
      void pullEvents().catch(() => undefined)
    }, 900)

    try {
      const result = await runTicket(selectedId)
      stopPoll()
      await pullEvents()
      await refreshBoard()

      // Prefer run_id from newest events after the call
      const after = await getEvents(160)
      setEvents(after.events)
      const fresh = [...after.events]
        .reverse()
        .find(
          (e) =>
            e.run_id &&
            e.run_id !== 'human-approve' &&
            !seen.has(`${e.time}-${e.step}-${e.agent}`),
        )
      if (fresh?.run_id) setActiveRunId(fresh.run_id)

      const waiting =
        Boolean(result.decision.needs_human_approval) ||
        result.ticket.status === 'waiting_approval' ||
        result.decision.status === 'waiting_approval'
      // Desk rule: when the run finishes, mark resolved — unless cash still needs a human.
      const finishedStatus = waiting
        ? 'waiting_approval'
        : result.ticket.status === 'blocked' || result.decision.status === 'blocked'
          ? 'blocked'
          : 'resolved'

      setDecisionText(result.decision.decision)
      setNeedsHuman(waiting)
      setHumanNote(result.decision.human_action)

      setRunFinishedIds((prev) => new Set(prev).add(selectedId))

      setTickets((prev) =>
        prev.map((t) =>
          t.id === selectedId
            ? {
                ...result.ticket,
                status: finishedStatus,
                board_state: finishedStatus,
              }
            : t,
        ),
      )

      setStatus(
        finishedStatus === 'resolved'
          ? `Ticket ${selectedId} resolved.`
          : `Run finished for ticket ${selectedId} (${finishedStatus}).`,
      )
    } catch (e) {
      stopPoll()
      setError(e instanceof Error ? e.message : String(e))
      setStatus('Agent run failed.')
    } finally {
      setRunning(false)
    }
  }

  const onApprove = async (e: FormEvent) => {
    e.preventDefault()
    if (!approvedBy.trim()) {
      setError('Type the human approver name — agents cannot approve themselves.')
      return
    }
    setError(null)
    try {
      const prevBal = cash?.balance
      const res = await approvePayment({
        kind,
        ref_id: Number(refId),
        amount: Number(amount),
        approved_by: approvedBy.trim(),
      })
      const nextCash = {
        name: String(res.cash.name ?? 'checking'),
        balance: Number(res.cash.balance),
        date: String(res.cash.date ?? ''),
      }
      setCash(nextCash)
      if (prevBal != null && nextCash.balance < prevBal) {
        setCashPulse(true)
        window.setTimeout(() => setCashPulse(false), 900)
      }
      setNeedsHuman(false)
      await refreshBoard()
      await pullEvents()
      setStatus(`Payment approved by ${approvedBy.trim()}. Cash updated.`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const onReset = async () => {
    setError(null)
    try {
      const res = await resetDatabase()
      setTickets(res.tickets)
      setCash({
        name: String(res.cash.name ?? 'checking'),
        balance: Number(res.cash.balance),
        date: String(res.cash.date ?? ''),
      })
      setEvents([])
      setActiveRunId(null)
      setRunFinishedIds(new Set())
      setNeedsHuman(false)
      setDecisionText('')
      setStatus('Database reset to seed. Fresh desk.')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const runEvents = useMemo(() => {
    if (!activeRunId) return events.slice(-40)
    return events.filter((e) => e.run_id === activeRunId)
  }, [events, activeRunId])

  const activeAgents = useMemo(() => {
    const set = new Set<string>()
    for (const ev of runEvents.slice(-12)) {
      if (ev.agent) set.add(ev.agent)
    }
    return set
  }, [runEvents])

  return (
    <div className="desk">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark" aria-hidden>
            <img src="/desk.svg" alt="" />
          </div>
          <div>
            <h1>Campus Customs</h1>
            <p>Ops desk — tickets, agents, and human-approved cash</p>
          </div>
        </div>
        <div className="top-actions">
          <button type="button" className="btn btn-ghost" onClick={() => void refreshBoard()}>
            Refresh
          </button>
          <button type="button" className="btn" onClick={() => void onReset()} disabled={running}>
            Reset DB
          </button>
        </div>
      </header>

      <div className="layout">
        <section className="panel">
          <div className="panel-head">
            <h2>Ticket rail</h2>
            <span>Pick one</span>
          </div>
          <div className="ticket-list">
            {tickets.map((t) => {
              const isRunning = running && selectedId === t.id
              const finished = runFinishedIds.has(t.id)
              const resolved =
                t.status === 'resolved' ||
                t.board_state === 'resolved' ||
                (finished && t.status === 'resolved')
              return (
                <button
                  key={t.id}
                  type="button"
                  className={`ticket ${selectedId === t.id ? 'selected' : ''} ${resolved ? 'resolved' : ''}`}
                  onClick={() => setSelectedId(t.id)}
                >
                  <div className="ticket-top">
                    <span className="ticket-id">#{t.id}</span>
                    <span className={`badge ${statusBadge(resolved ? 'resolved' : t.status, isRunning)}`}>
                      {isRunning ? 'running' : resolved ? 'resolved' : t.status}
                    </span>
                  </div>
                  <h3>{t.subject}</h3>
                  <p className="meta">
                    {t.type.replaceAll('_', ' ')} · {t.requester}
                    {t.sku ? ` · ${t.sku}${t.size ? ` / ${t.size}` : ''}` : ''}
                    {t.lease_id ? ` · lease ${t.lease_id}` : ''}
                  </p>
                </button>
              )
            })}
          </div>
        </section>

        <section className="panel stage">
          <div className="panel-head">
            <h2>Agent stage</h2>
            <span>{running ? 'live' : 'idle'}</span>
          </div>
          <div className="stage-toolbar">
            <p className="hint">
              {selected
                ? `Selected #${selected.id} — ${selected.subject}. Start the team; lanes update as MCP tools and handoffs land.`
                : 'Select a ticket on the left.'}
            </p>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!selectedId || running}
              onClick={() => void onRun()}
            >
              {running ? 'Team working…' : `Run ticket ${selectedId ?? ''}`}
            </button>
          </div>

          <div className="agent-grid">
            {AGENTS.map((agent) => {
              const lines = runEvents
                .filter((e) => e.agent === agent.id)
                .slice(-8)
                .map((e, i) => (
                  <li key={`${agent.id}-${i}-${e.time}-${e.step}`}>
                    {e.tool ? <span className="tool">{e.tool}</span> : null}{' '}
                    {lineFromEvent(e)}
                  </li>
                ))
              return (
                <article
                  key={agent.id}
                  className={`agent-lane ${activeAgents.has(agent.id) || (running && agent.id === 'boss') ? 'active' : ''}`}
                  data-agent={agent.id}
                >
                  <header>
                    <strong>{agent.label}</strong>
                    <small>{agent.blurb}</small>
                  </header>
                  <ul className="feed">
                    {lines.length ? lines : <li className="empty">Waiting for work…</li>}
                  </ul>
                </article>
              )
            })}
          </div>

          {(decisionText || runFinishedIds.has(selectedId ?? -1)) && (
            <div className="summary-block">
              <h3>What each agent did</h3>
              <div className="summary-grid">
                {AGENTS.map((agent) => (
                  <div className="summary-card" key={`sum-${agent.id}`}>
                    <strong>{agent.label}</strong>
                    <p>{summarizeAgent(runEvents, agent.id)}</p>
                  </div>
                ))}
              </div>
              {decisionText ? (
                <p className="status-line" style={{ marginTop: '0.75rem' }}>
                  <strong>Boss wrap:</strong> {decisionText.slice(0, 420)}
                  {decisionText.length > 420 ? '…' : ''}
                </p>
              ) : null}
            </div>
          )}
        </section>

        <aside className="side">
          <section className="panel cash-panel">
            <div className="panel-head">
              <h2>Checking</h2>
              <span>{cash?.date || '—'}</span>
            </div>
            <p className={`cash-amount ${cashPulse ? 'drop' : ''}`}>
              {cash ? money(cash.balance) : '—'}
            </p>
            <p className="cash-meta">Drops only after a human approves pay</p>
          </section>

          <section className="panel approve">
            <div className="panel-head">
              <h2>Human approve</h2>
              <span>cash out</span>
            </div>
            {needsHuman ? (
              <p className="notice">
                Agents prepared a payment. {humanNote || 'Enter approver name and confirm to move cash.'}
              </p>
            ) : (
              <p className="status-line">Approve when a ticket is waiting on payment.</p>
            )}
            <form onSubmit={(e) => void onApprove(e)}>
              <label>
                Kind
                <select
                  value={kind}
                  onChange={(ev) => setKind(ev.target.value as 'invoice' | 'rent')}
                >
                  <option value="invoice">Invoice</option>
                  <option value="rent">Rent</option>
                </select>
              </label>
              <label>
                Ref id
                <input
                  type="number"
                  value={refId}
                  onChange={(ev) => setRefId(Number(ev.target.value))}
                  required
                />
              </label>
              <label>
                Amount
                <input
                  type="number"
                  step="0.01"
                  value={amount}
                  onChange={(ev) => setAmount(Number(ev.target.value))}
                  required
                />
              </label>
              <label>
                Approved by (human)
                <input
                  value={approvedBy}
                  onChange={(ev) => setApprovedBy(ev.target.value)}
                  placeholder="Your name"
                  required
                />
              </label>
              <button type="submit" className="btn btn-brass" disabled={running}>
                Approve &amp; pay
              </button>
            </form>
          </section>
        </aside>
      </div>

      <p className={`status-line ${error ? 'error' : 'ok'}`}>
        {error ? `Error: ${error}` : status}
      </p>
    </div>
  )
}
