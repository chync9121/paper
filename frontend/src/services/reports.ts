import { api } from './api'

export interface GenerateReportPayload {
  report_type: 'related_work' | 'experimental_analysis'
  selected_node_ids: number[]
  selected_experiment_ids: number[]
  prompt?: string
  title?: string
  model_name?: string
}

export interface GeneratedReport {
  id: number
  report_type: string
  title?: string | null
  selected_node_ids: number[]
  selected_run_ids: number[]
  prompt?: string | null
  context_snapshot: Record<string, unknown>
  model_name?: string | null
  output_markdown?: string | null
  output_text?: string | null
  created_at: string
}

export async function generateReport(payload: GenerateReportPayload) {
  const { data } = await api.post<GeneratedReport>('/reports/generate', payload)
  return data
}

export async function fetchReports(limit = 20) {
  const { data } = await api.get<GeneratedReport[]>('/reports', { params: { limit } })
  return data
}
