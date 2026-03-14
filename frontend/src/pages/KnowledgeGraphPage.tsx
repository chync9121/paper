import { useEffect, useMemo, useState } from 'react'
import {
  Background,
  Controls,
  MiniMap,
  ReactFlow,
  type Edge,
  type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'

import { Panel } from '../components/common/Panel'
import { createEdge, createNode, fetchNodes, fetchSubgraph } from '../services/graph'
import type { KGNode } from '../types'

function radialPosition(index: number, total: number) {
  const angle = (index / Math.max(total, 1)) * Math.PI * 2
  const radius = 280 + (index % 3) * 46
  return {
    x: Math.cos(angle) * radius,
    y: Math.sin(angle) * radius,
  }
}

function nodeVisual(nodeType: string) {
  if (nodeType === 'model') {
    return { border: '#7dd3fc', bg: '#f0f9ff' }
  }
  if (nodeType === 'dataset') {
    return { border: '#86efac', bg: '#f0fdf4' }
  }
  if (nodeType === 'metric') {
    return { border: '#fcd34d', bg: '#fffbeb' }
  }
  if (nodeType === 'paper') {
    return { border: '#c4b5fd', bg: '#f5f3ff' }
  }
  return { border: '#cbd5e1', bg: '#f8fafc' }
}

export function KnowledgeGraphPage() {
  const [query, setQuery] = useState('')
  const [nodeType, setNodeType] = useState('')
  const [allNodes, setAllNodes] = useState<KGNode[]>([])
  const [flowNodes, setFlowNodes] = useState<Node[]>([])
  const [flowEdges, setFlowEdges] = useState<Edge[]>([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [newNodeName, setNewNodeName] = useState('')
  const [newNodeType, setNewNodeType] = useState('model')
  const [edgeSource, setEdgeSource] = useState<number | ''>('')
  const [edgeTarget, setEdgeTarget] = useState<number | ''>('')
  const [edgeType, setEdgeType] = useState('compares_with')

  useEffect(() => {
    void loadGraph()
  }, [])

  const nodeCountByType = useMemo(() => {
    const counter: Record<string, number> = {}
    for (const node of allNodes) {
      counter[node.node_type] = (counter[node.node_type] ?? 0) + 1
    }
    return counter
  }, [allNodes])

  async function loadGraph() {
    setLoading(true)
    setErr('')
    try {
      const nodes = await fetchNodes({
        node_type: nodeType || undefined,
        q: query || undefined,
      })
      setAllNodes(nodes)

      const subgraph = await fetchSubgraph(nodes.map((n) => n.id))
      setFlowNodes(
        subgraph.nodes.map((n, idx) => {
          const visual = nodeVisual(n.node_type)
          return {
            id: String(n.id),
            data: { label: `${n.name} (${n.node_type})` },
            position: radialPosition(idx, subgraph.nodes.length),
            style: {
              borderRadius: 14,
              border: `1px solid ${visual.border}`,
              padding: 10,
              fontSize: 12,
              background: visual.bg,
              minWidth: 138,
              color: '#0f172a',
              boxShadow: '0 6px 14px rgba(15, 23, 42, 0.06)',
            },
          }
        }),
      )
      setFlowEdges(
        subgraph.edges.map((e) => ({
          id: String(e.id),
          source: String(e.source_node_id),
          target: String(e.target_node_id),
          label: e.relation_type,
          style: { stroke: '#64748b', strokeWidth: 1.3 },
          labelStyle: { fontSize: 11, fill: '#0f172a' },
        })),
      )
    } catch (error) {
      setErr('图谱加载失败，请检查后端服务与网络代理配置。')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateNode() {
    if (!newNodeName.trim()) return
    await createNode({ node_type: newNodeType, name: newNodeName.trim(), extra: {} })
    setNewNodeName('')
    await loadGraph()
  }

  async function handleCreateEdge() {
    if (edgeSource === '' || edgeTarget === '') return
    await createEdge({
      source_node_id: Number(edgeSource),
      target_node_id: Number(edgeTarget),
      relation_type: edgeType,
    })
    await loadGraph()
  }

  return (
    <div className="space-y-4">
      <Panel
        title="文献与基准图谱"
        subtitle="按实体类型或关键词检索节点，并在交互画布中查看关系结构。"
      >
        <div className="grid gap-3 md:grid-cols-[1fr_200px_auto]">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="关键词检索，例如 ResNet / CIFAR-10"
            className="input-field"
          />
          <select
            value={nodeType}
            onChange={(e) => setNodeType(e.target.value)}
            className="input-field"
          >
            <option value="">全部类型</option>
            <option value="paper">paper（论文）</option>
            <option value="model">model（模型）</option>
            <option value="dataset">dataset（数据集）</option>
            <option value="metric">metric（指标）</option>
            <option value="task">task（任务）</option>
            <option value="method">method（方法）</option>
          </select>
          <button onClick={loadGraph} className="btn btn-primary">
            {loading ? '加载中...' : '刷新图谱'}
          </button>
        </div>
        {err && <p className="mt-3 text-sm text-rose-600">{err}</p>}
        <div className="mt-3 flex flex-wrap gap-2 text-xs">
          <span className="chip">节点总数：{allNodes.length}</span>
          {Object.entries(nodeCountByType).map(([type, count]) => (
            <span key={type} className="chip">
              {type}: {count}
            </span>
          ))}
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[320px_1fr]">
        <Panel title="图谱编辑器" subtitle="录入节点并定义关系边，支持快速构图。">
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-700">新增节点</p>
              <input
                value={newNodeName}
                onChange={(e) => setNewNodeName(e.target.value)}
                placeholder="节点名称"
                className="input-field w-full"
              />
              <select
                value={newNodeType}
                onChange={(e) => setNewNodeType(e.target.value)}
                className="input-field w-full"
              >
                <option value="paper">paper（论文）</option>
                <option value="model">model（模型）</option>
                <option value="dataset">dataset（数据集）</option>
                <option value="metric">metric（指标）</option>
                <option value="task">task（任务）</option>
                <option value="method">method（方法）</option>
              </select>
              <button onClick={handleCreateNode} className="btn btn-emerald w-full">
                创建节点
              </button>
            </div>

            <div className="h-px bg-slate-200" />

            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-700">新增关系</p>
              <select
                value={edgeSource}
                onChange={(e) =>
                  setEdgeSource(e.target.value ? Number(e.target.value) : '')
                }
                className="input-field w-full"
              >
                <option value="">选择 source 节点</option>
                {allNodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.id} - {node.name}
                  </option>
                ))}
              </select>
              <select
                value={edgeTarget}
                onChange={(e) =>
                  setEdgeTarget(e.target.value ? Number(e.target.value) : '')
                }
                className="input-field w-full"
              >
                <option value="">选择 target 节点</option>
                {allNodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.id} - {node.name}
                  </option>
                ))}
              </select>
              <input
                value={edgeType}
                onChange={(e) => setEdgeType(e.target.value)}
                className="input-field w-full"
                placeholder="关系类型，例如 evaluated_on"
              />
              <button onClick={handleCreateEdge} className="btn btn-amber w-full">
                创建关系
              </button>
            </div>
          </div>
        </Panel>

        <Panel
          title="图谱画布"
          subtitle="支持平移、缩放、迷你地图与关系标签观察。"
          className="h-[700px]"
        >
          <div className="h-[610px] w-full overflow-hidden rounded-xl border border-slate-200 bg-white/65">
            <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
              <MiniMap
                nodeColor={(node) => String(node.style?.background ?? '#f8fafc')}
              />
              <Controls />
              <Background color="#cbd5e1" gap={20} />
            </ReactFlow>
          </div>
        </Panel>
      </div>
    </div>
  )
}
