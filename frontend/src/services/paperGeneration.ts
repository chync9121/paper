import { api } from './api'

export interface GeneratePaperPayload {
  title: string
  experiment_ids: number[]
  selected_node_ids: number[]
  target_venue?: string
  main_metric_names?: string[]
  prompt?: string
  model_name?: string
  use_llm?: boolean
  try_compile_pdf?: boolean
}

export interface GeneratedPaperDraft {
  title: string
  target_venue: string
  output_dir: string
  tex_path: string
  figure_paths: string[]
  table_paths: string[]
  used_llm: boolean
  pdf_compiled: boolean
  pdf_path?: string | null
  pdf_url?: string | null
  output_url_base?: string | null
  tex_url?: string | null
  context_snapshot_url?: string | null
  sections: Record<string, string>
}

export async function generatePaper(payload: GeneratePaperPayload) {
  const { data } = await api.post<GeneratedPaperDraft>('/paper-generation/generate', payload)
  return data
}
