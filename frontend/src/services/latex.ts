import { api } from './api'

export interface GenerateLatexPayload {
  experiment_ids: number[]
  metric_names?: string[]
  model_node_ids?: number[]
  dataset_node_ids?: number[]
  caption?: string
  label?: string
  note?: string
  placement?: string
  precision?: number
  highlight_best?: boolean
  highlight_second?: boolean
  use_resizebox?: boolean
  compact?: boolean
  show_std?: boolean
  omit_zero_std?: boolean
  use_threeparttable?: boolean
  table_environment?: string
  column_group_by?: string
}

export interface LatexTableResponse {
  latex_code: string
  model_names: string[]
  dataset_names: string[]
  metric_names: string[]
  num_runs: number
  num_metrics: number
  packages_hint: string[]
  guideline_notes: string[]
}

export async function generateLatexTable(payload: GenerateLatexPayload) {
  const { data } = await api.post<LatexTableResponse>('/latex/generate', payload)
  return data
}
