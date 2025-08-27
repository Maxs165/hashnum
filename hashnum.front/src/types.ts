export type TaskInfo = { task_id: string }
export type TaskStatus = {
  task_id: string
  status: 'queued' | 'started' | 'finished' | 'failed'
  progress: number
  cracked: number
  total: number
  message?: string | null
}
export type LogChunk = { lines: string[]; cursor: number }