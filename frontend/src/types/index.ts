export type NodeType = 'paper' | 'model' | 'dataset' | 'metric' | 'task' | 'method'

export interface KGNode {
  id: number
  node_type: string
  name: string
  canonical_name?: string | null
  description?: string | null
  paper_id?: number | null
  extra: Record<string, unknown>
  created_at: string
}

export interface KGEdge {
  id: number
  source_node_id: number
  target_node_id: number
  relation_type: string
  paper_id?: number | null
  confidence?: number | null
  evidence_text?: string | null
  created_at: string
}

export interface Experiment {
  id: number
  name: string
  description?: string | null
  task_name?: string | null
  owner?: string | null
  created_at: string
}

export interface ExperimentMetricsRow {
  run_id: number
  run_name?: string | null
  model_node_id?: number | null
  dataset_node_id?: number | null
  metric_name: string
  metric_value: number
  stage?: string | null
}
