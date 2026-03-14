import { api } from './api'
import type { KGEdge, KGNode } from '../types'

export interface SubgraphResponse {
  nodes: KGNode[]
  edges: KGEdge[]
}

export async function fetchNodes(params?: { node_type?: string; q?: string }) {
  const { data } = await api.get<KGNode[]>('/graph/nodes', { params })
  return data
}

export async function fetchSubgraph(nodeIds: number[]) {
  if (nodeIds.length === 0) {
    return { nodes: [], edges: [] } as SubgraphResponse
  }
  const { data } = await api.get<SubgraphResponse>('/graph/subgraph', {
    params: { node_ids: nodeIds },
    paramsSerializer: {
      indexes: null,
    },
  })
  return data
}

export async function createNode(payload: {
  node_type: string
  name: string
  canonical_name?: string
  description?: string
  paper_id?: number
  extra?: Record<string, unknown>
}) {
  const { data } = await api.post<KGNode>('/graph/nodes', payload)
  return data
}

export async function createEdge(payload: {
  source_node_id: number
  target_node_id: number
  relation_type: string
  paper_id?: number
  confidence?: number
  evidence_text?: string
}) {
  const { data } = await api.post<KGEdge>('/graph/edges', payload)
  return data
}
