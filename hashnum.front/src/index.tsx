import React, { useEffect, useRef, useState } from 'react'
import { API, ensureToken } from './api'
import type { TaskInfo, TaskStatus, LogChunk } from './types'

export default function Dashboard() {
  const [file, setFile] = useState<File | null>(null)
  const [salt, setSalt] = useState('')
  const [taskId, setTaskId] = useState<string>('')
  const [status, setStatus] = useState<TaskStatus | null>(null)
  const [logs, setLogs] = useState<string[]>([])
  const [busy, setBusy] = useState(false)

  const poller = useRef<number | null>(null)
  const cursorRef = useRef(0)

  useEffect(() => {
    ensureToken().catch(() => {})
    return () => { if (poller.current) window.clearInterval(poller.current) }
  }, [])

  async function start() {
    if (!file || !salt || busy) return
    await ensureToken().catch(() => {})

    setBusy(true)
    setLogs([])
    setStatus(null)
    setTaskId('')
    cursorRef.current = 0

    const fd = new FormData()
    fd.append('file', file)
    const up = await API.post<TaskInfo>('/upload', fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    const tid = up.data.task_id
    setTaskId(tid)

    await API.post(`/crack/${tid}`, { salt })

    if (poller.current) {
      window.clearInterval(poller.current)
      poller.current = null
    }

    const tick = async () => {
      try {
        const s = await API.get<TaskStatus>(`/status/${tid}`)
        setStatus(s.data)

        const l = await API.get<LogChunk>(`/logs/${tid}`, {
          params: { cursor: cursorRef.current },
        })

        if (l.data.lines?.length) setLogs(prev => [...prev, ...l.data.lines])
        cursorRef.current = l.data.cursor

        if (s.data.status === 'finished' || s.data.status === 'failed') {
          if (poller.current) { window.clearInterval(poller.current); poller.current = null }
          setBusy(false)
        }
      } catch { /* ignore */ }
    }

    await tick()
    poller.current = window.setInterval(tick, 1000)
  }

  const progress = Math.min(100, status?.progress ?? 0)

  return (
    <div className="container">
      <div className="card">
        <h2>CrackNum Web</h2>
        <div className="row" style={{marginTop: 12}}>
          <input className="input" type="file" accept=".txt,.csv"
                 onChange={e => setFile(e.target.files?.[0] || null)} />
          <input className="input" placeholder="Соль" value={salt}
                 onChange={e => setSalt(e.target.value)} />
          <button className="btn" disabled={!file || !salt || busy} onClick={start}>
            {busy ? 'Идёт задача…' : 'Старт'}
          </button>
        </div>

        {taskId && (
          <div style={{marginTop: 12}}>
            Task: <code>{taskId}</code> {status?.status && <>• <b>{status.status}</b></>}
          </div>
        )}

        <div className="progress" style={{marginTop: 12}}>
          <div style={{width: `${progress}%`}} />
        </div>

        <div style={{marginTop: 8, opacity: .9}}>
          {status && <>
            <span>{progress.toFixed(2)}%</span>
            {status.total > 0 && <> • найдено {status.cracked}/{status.total}</>}
            {status.status === 'failed' && status.message && <> • ошибка: {status.message}</>}
          </>}
        </div>

        {taskId && status?.status === 'finished' && (
          <div style={{marginTop: 12}}>
            <a className="link" href={`${API.defaults.baseURL}/download/${taskId}`}>Скачать результат</a>
          </div>
        )}

        <h3 style={{marginTop: 16}}>Лог</h3>
        <div className="log">{logs.join('\n')}</div>
      </div>
    </div>
  )
}
