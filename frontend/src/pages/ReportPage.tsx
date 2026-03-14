import { useEffect, useMemo, useState } from 'react'

import { Panel } from '../components/common/Panel'
import { fetchExperiments } from '../services/experiments'
import { fetchNodes } from '../services/graph'
import { fetchReports, generateReport, type GeneratedReport } from '../services/reports'
import type { Experiment, KGNode } from '../types'

export function ReportPage() {
  const [reportType, setReportType] = useState<'related_work' | 'experimental_analysis'>(
    'related_work',
  )
  const [nodes, setNodes] = useState<KGNode[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedNodeIds, setSelectedNodeIds] = useState<number[]>([])
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<number[]>([])
  const [prompt, setPrompt] = useState('')
  const [modelName, setModelName] = useState('deepseek-chat')
  const [draft, setDraft] = useState('')
  const [history, setHistory] = useState<GeneratedReport[]>([])
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')
  const [lastMetricCount, setLastMetricCount] = useState(0)
  const [lastRunCount, setLastRunCount] = useState(0)
  const [lastUsedModel, setLastUsedModel] = useState('')

  useEffect(() => {
    void bootstrap()
  }, [])

  async function bootstrap() {
    const [nodeData, expData, reportData] = await Promise.all([
      fetchNodes(),
      fetchExperiments(),
      fetchReports(10),
    ])
    setNodes(nodeData)
    setExperiments(expData)
    setHistory(reportData)
  }

  async function handleGenerate() {
    setGenerating(true)
    setError('')
    try {
      const generated = await generateReport({
        report_type: reportType,
        selected_node_ids: selectedNodeIds,
        selected_experiment_ids: selectedExperimentIds,
        prompt,
        model_name: modelName || undefined,
      })
      setDraft(generated.output_text ?? '')
      setLastUsedModel(generated.model_name ?? '')

      const context = generated.context_snapshot as Record<string, unknown>
      setLastMetricCount(Number(context.selected_metric_count ?? 0))
      setLastRunCount(Number(context.selected_run_count ?? 0))

      const reportData = await fetchReports(10)
      setHistory(reportData)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(detail || '生成失败，请检查后端日志与 API Key 配置。')
    } finally {
      setGenerating(false)
    }
  }

  const selectedSummary = useMemo(
    () => ({
      nodeCount: selectedNodeIds.length,
      experimentCount: selectedExperimentIds.length,
    }),
    [selectedNodeIds.length, selectedExperimentIds.length],
  )

  function toggleNode(id: number) {
    setSelectedNodeIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    )
  }

  function toggleExperiment(id: number) {
    setSelectedExperimentIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id],
    )
  }

  return (
    <div className="space-y-4">
      <Panel
        title="综合研报生成（LLM）"
        subtitle="后端会把图谱节点与实验指标打包为上下文，调用 DeepSeek 生成学术段落。"
      >
        <div className="grid gap-3 md:grid-cols-[240px_200px_1fr_auto]">
          <select
            value={reportType}
            onChange={(e) =>
              setReportType(e.target.value as 'related_work' | 'experimental_analysis')
            }
            className="input-field"
          >
            <option value="related_work">相关工作（Related Work）</option>
            <option value="experimental_analysis">实验分析（Experimental Analysis）</option>
          </select>
          <input
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            className="input-field code-text"
            placeholder="deepseek-chat"
          />
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="input-field"
            placeholder="附加要求：如强调跨数据集泛化能力、误差分析、统计显著性"
          />
          <button onClick={handleGenerate} className="btn btn-amber" disabled={generating}>
            {generating ? '生成中...' : '调用大模型生成'}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
          <span className="chip">已选节点：{selectedSummary.nodeCount}</span>
          <span className="chip">已选实验：{selectedSummary.experimentCount}</span>
          <span className="chip">上下文 runs：{lastRunCount}</span>
          <span className="chip">上下文 metrics：{lastMetricCount}</span>
          <span className="chip">模型：{lastUsedModel || modelName}</span>
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="图谱节点选择" subtitle="建议选择 baseline 模型、数据集、指标节点。">
          <div className="soft-scroll grid max-h-[400px] grid-cols-1 gap-2 overflow-y-auto pr-2">
            {nodes.map((node) => (
              <label
                key={node.id}
                className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm hover:border-slate-300 hover:bg-slate-50"
              >
                <span>
                  [{node.node_type}] {node.name}
                </span>
                <input
                  type="checkbox"
                  checked={selectedNodeIds.includes(node.id)}
                  onChange={() => toggleNode(node.id)}
                />
              </label>
            ))}
            {nodes.length === 0 && (
              <p className="text-sm text-slate-500">暂无图谱节点，请先到图谱中心创建。</p>
            )}
          </div>
        </Panel>

        <Panel title="实验选择" subtitle="勾选需要纳入报告证据链的实验。">
          <div className="soft-scroll grid max-h-[400px] grid-cols-1 gap-2 overflow-y-auto pr-2">
            {experiments.map((exp) => (
              <label
                key={exp.id}
                className="flex cursor-pointer items-center justify-between rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-sm hover:border-slate-300 hover:bg-slate-50"
              >
                <span>{exp.name}</span>
                <input
                  type="checkbox"
                  checked={selectedExperimentIds.includes(exp.id)}
                  onChange={() => toggleExperiment(exp.id)}
                />
              </label>
            ))}
            {experiments.length === 0 && (
              <p className="text-sm text-slate-500">暂无实验，请先在实验看板中创建。</p>
            )}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
        <Panel title="生成结果" subtitle="可直接编辑并用于论文初稿撰写。">
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            className="input-field code-text h-[360px] w-full resize-y"
            placeholder="点击“调用大模型生成”后，这里会输出结构化学术文本。"
          />
        </Panel>

        <Panel title="最近生成记录" subtitle="点击记录可回看历史生成结果。">
          <div className="soft-scroll max-h-[360px] space-y-2 overflow-y-auto pr-2">
            {history.map((item) => (
              <button
                key={item.id}
                onClick={() => {
                  setDraft(item.output_text ?? '')
                  setLastUsedModel(item.model_name ?? '')
                }}
                className="w-full rounded-xl border border-slate-200 bg-white/70 px-3 py-2 text-left text-sm hover:border-slate-300 hover:bg-slate-50"
              >
                <p className="font-semibold text-slate-800">#{item.id} {item.report_type}</p>
                <p className="text-xs text-slate-500">{item.model_name || 'unknown-model'}</p>
              </button>
            ))}
            {history.length === 0 && (
              <p className="text-sm text-slate-500">暂无历史记录。</p>
            )}
          </div>
        </Panel>
      </div>
    </div>
  )
}
