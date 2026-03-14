import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import { Panel } from '../components/common/Panel'
import { fetchExperiments } from '../services/experiments'
import { fetchNodes } from '../services/graph'
import { generatePaper, type GeneratedPaperDraft } from '../services/paperGeneration'
import type { Experiment, KGNode } from '../types'

const SECTION_LABELS: Record<string, string> = {
  abstract: '摘要',
  introduction: '引言',
  related_work: '相关工作',
  method: '方法',
  experiments: '实验',
  conclusion: '结论',
}

export function PaperStudioPage() {
  const [nodes, setNodes] = useState<KGNode[]>([])
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedNodeIds, setSelectedNodeIds] = useState<number[]>([])
  const [selectedExperimentIds, setSelectedExperimentIds] = useState<number[]>([])
  const [title, setTitle] = useState('Knowledge-Driven Evaluation and Auto-Writing for AI Research')
  const [targetVenue, setTargetVenue] = useState('CVPR')
  const [mainMetrics, setMainMetrics] = useState('Top-1 Accuracy,Macro-F1,ECE')
  const [modelName, setModelName] = useState('deepseek-chat')
  const [prompt, setPrompt] = useState(
    '强调知识图谱、自动绘图、顶会级表格引擎以及论文装配能力之间的协同价值。',
  )
  const [useLlm, setUseLlm] = useState(true)
  const [tryCompilePdf, setTryCompilePdf] = useState(true)
  const [result, setResult] = useState<GeneratedPaperDraft | null>(null)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    void bootstrap()
  }, [])

  async function bootstrap() {
    const [nodeData, experimentData] = await Promise.all([fetchNodes(), fetchExperiments()])
    setNodes(nodeData)
    setExperiments(experimentData)
  }

  async function handleGeneratePaper() {
    setGenerating(true)
    setError('')
    try {
      const generated = await generatePaper({
        title,
        experiment_ids: selectedExperimentIds,
        selected_node_ids: selectedNodeIds,
        target_venue: targetVenue,
        main_metric_names: mainMetrics
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        prompt,
        model_name: modelName || undefined,
        use_llm: useLlm,
        try_compile_pdf: tryCompilePdf,
      })
      setResult(generated)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(detail || '论文生成失败，请检查后端日志或 LLM 配置。')
    } finally {
      setGenerating(false)
    }
  }

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

  const summary = useMemo(
    () => ({
      nodeCount: selectedNodeIds.length,
      experimentCount: selectedExperimentIds.length,
      hasResult: Boolean(result),
    }),
    [result, selectedExperimentIds.length, selectedNodeIds.length],
  )

  return (
    <div className="space-y-4">
      <Panel
        title="顶会论文自动装配"
        subtitle="系统会复用已有实验数据、LaTeX 表格引擎和 Matplotlib 绘图能力，自动生成一套可继续投稿打磨的论文工程目录。"
      >
        <div className="grid gap-3 lg:grid-cols-[1.2fr_180px_220px]">
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="input-field"
            placeholder="论文标题"
          />
          <input
            value={targetVenue}
            onChange={(e) => setTargetVenue(e.target.value)}
            className="input-field code-text"
            placeholder="CVPR / NeurIPS / ACL"
          />
          <input
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            className="input-field code-text"
            placeholder="deepseek-chat"
          />
        </div>

        <div className="mt-3 grid gap-3 lg:grid-cols-[1fr_1fr]">
          <input
            value={mainMetrics}
            onChange={(e) => setMainMetrics(e.target.value)}
            className="input-field"
            placeholder="用逗号分隔主要指标，例如 Top-1 Accuracy, Macro-F1, ECE"
          />
          <input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            className="input-field"
            placeholder="补充写作要求"
          />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-3 text-sm text-slate-700">
          <label className="inline-flex items-center gap-2">
            <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
            使用大模型撰写章节
          </label>
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox"
              checked={tryCompilePdf}
              onChange={(e) => setTryCompilePdf(e.target.checked)}
            />
            尝试编译 PDF
          </label>
          <span className="chip">已选节点：{summary.nodeCount}</span>
          <span className="chip">已选实验：{summary.experimentCount}</span>
          <button onClick={handleGeneratePaper} className="btn btn-amber" disabled={generating}>
            {generating ? '论文生成中...' : '一键生成论文工程'}
          </button>
          <Link to="/paper-editor" className="chip no-underline text-slate-800">
            打开论文编辑器
          </Link>
        </div>

        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Panel title="图谱证据选择" subtitle="建议优先选择论文节点、基线模型、数据集与关键指标节点。">
          <div className="soft-scroll grid max-h-[380px] gap-2 overflow-y-auto pr-2">
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
            {nodes.length === 0 && <p className="text-sm text-slate-500">暂无图谱节点。</p>}
          </div>
        </Panel>

        <Panel title="实验选择" subtitle="选中的实验将用于自动生成主结果表、消融表以及图像。">
          <div className="soft-scroll grid max-h-[380px] gap-2 overflow-y-auto pr-2">
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
            {experiments.length === 0 && <p className="text-sm text-slate-500">暂无实验记录。</p>}
          </div>
        </Panel>
      </div>

      <div className="grid gap-4 xl:grid-cols-[1fr_1.3fr]">
        <Panel title="论文产物" subtitle="生成完成后，这里会展示可访问的 LaTeX 工程路径与链接。">
          {result ? (
            <div className="space-y-3 text-sm text-slate-700">
              <div className="rounded-2xl border border-slate-200 bg-white/70 p-4">
                <p className="font-semibold text-slate-900">{result.title}</p>
                <p className="mt-1 text-slate-600">目标会场：{result.target_venue}</p>
                <p className="mt-1 break-all">输出目录：{result.output_dir}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <span className="chip">LLM：{result.used_llm ? '已使用' : '回退模板'}</span>
                  <span className="chip">PDF：{result.pdf_compiled ? '已编译' : '未编译'}</span>
                </div>
              </div>

              <div className="grid gap-2">
                {result.tex_url && (
                  <a
                    href={result.tex_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-slate-200 bg-white/70 px-3 py-2 hover:bg-slate-50"
                  >
                    打开 main.tex
                  </a>
                )}
                {result.context_snapshot_url && (
                  <a
                    href={result.context_snapshot_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-slate-200 bg-white/70 px-3 py-2 hover:bg-slate-50"
                  >
                    查看上下文快照
                  </a>
                )}
                {result.pdf_url && (
                  <a
                    href={result.pdf_url}
                    target="_blank"
                    rel="noreferrer"
                    className="rounded-xl border border-slate-200 bg-white/70 px-3 py-2 hover:bg-slate-50"
                  >
                    打开生成的 PDF
                  </a>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">
              选择图谱节点与实验后，点击“一键生成论文工程”，系统会输出主文档、图、表和参考文献。
            </p>
          )}
        </Panel>

        <Panel title="章节预览" subtitle="生成后可快速检查摘要、相关工作、实验分析等内容。">
          {summary.hasResult && result ? (
            <div className="soft-scroll max-h-[540px] space-y-3 overflow-y-auto pr-2">
              {Object.entries(result.sections).map(([key, value]) => (
                <div key={key} className="rounded-2xl border border-slate-200 bg-white/70 p-4">
                  <p className="font-semibold text-slate-900">{SECTION_LABELS[key] || key}</p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-7 text-slate-700">
                    {value}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">这里会展示自动生成的论文章节内容。</p>
          )}
        </Panel>
      </div>
    </div>
  )
}
