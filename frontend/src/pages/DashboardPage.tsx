import { useEffect, useState } from 'react'
import ReactECharts from 'echarts-for-react'

import { Panel } from '../components/common/Panel'
import {
  createExperiment,
  fetchExperimentMetrics,
  fetchExperiments,
} from '../services/experiments'
import { generateLatexTable, type LatexTableResponse } from '../services/latex'
import type { Experiment, ExperimentMetricsRow } from '../types'

type TablePreset = 'cvpr' | 'neurips' | 'compact'

interface LatexOptions {
  caption: string
  label: string
  note: string
  precision: number
  useResizebox: boolean
  useThreePartTable: boolean
  showStd: boolean
  omitZeroStd: boolean
  compact: boolean
  tableEnvironment: 'table' | 'table*'
  columnGroupBy: 'dataset' | 'metric'
}

const presetOptions: Record<TablePreset, Partial<LatexOptions>> = {
  cvpr: {
    caption: '主要实验结果对比。',
    label: 'tab:main-results',
    note: '最优结果加粗，次优结果加下划线；若包含多次运行，则显示 mean ± std。',
    precision: 2,
    useResizebox: true,
    useThreePartTable: true,
    showStd: true,
    omitZeroStd: true,
    compact: true,
    tableEnvironment: 'table',
    columnGroupBy: 'dataset',
  },
  neurips: {
    caption: 'Main experimental results.',
    label: 'tab:main-results',
    note: 'Best results are bold, second-best results are underlined, and repeated runs report mean ± std.',
    precision: 2,
    useResizebox: false,
    useThreePartTable: true,
    showStd: true,
    omitZeroStd: true,
    compact: true,
    tableEnvironment: 'table',
    columnGroupBy: 'dataset',
  },
  compact: {
    caption: 'A compact comparison of selected models.',
    label: 'tab:compact-results',
    note: 'Single-run values are shown directly and repeated runs report mean ± std.',
    precision: 2,
    useResizebox: true,
    useThreePartTable: false,
    showStd: true,
    omitZeroStd: true,
    compact: true,
    tableEnvironment: 'table*',
    columnGroupBy: 'metric',
  },
}

const defaultLatexOptions: LatexOptions = {
  caption: presetOptions.cvpr.caption!,
  label: presetOptions.cvpr.label!,
  note: presetOptions.cvpr.note!,
  precision: presetOptions.cvpr.precision!,
  useResizebox: presetOptions.cvpr.useResizebox!,
  useThreePartTable: presetOptions.cvpr.useThreePartTable!,
  showStd: presetOptions.cvpr.showStd!,
  omitZeroStd: presetOptions.cvpr.omitZeroStd!,
  compact: presetOptions.cvpr.compact!,
  tableEnvironment: presetOptions.cvpr.tableEnvironment!,
  columnGroupBy: presetOptions.cvpr.columnGroupBy!,
}

function checkboxClass(enabled: boolean) {
  return enabled
    ? 'chip border-slate-400 bg-slate-900 text-white'
    : 'chip'
}

export function DashboardPage() {
  const [experiments, setExperiments] = useState<Experiment[]>([])
  const [selectedExperiment, setSelectedExperiment] = useState<number | ''>('')
  const [metrics, setMetrics] = useState<ExperimentMetricsRow[]>([])
  const [newExperimentName, setNewExperimentName] = useState('')
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [selectedMetric, setSelectedMetric] = useState('')
  const [latexMetrics, setLatexMetrics] = useState<string[]>([])
  const [preset, setPreset] = useState<TablePreset>('cvpr')
  const [latexOptions, setLatexOptions] = useState<LatexOptions>(defaultLatexOptions)
  const [latexCode, setLatexCode] = useState('')
  const [latexResponse, setLatexResponse] = useState<LatexTableResponse | null>(null)
  const [latexLoading, setLatexLoading] = useState(false)

  useEffect(() => {
    void loadExperiments()
  }, [])

  useEffect(() => {
    if (selectedExperiment === '') return
    void loadMetrics(Number(selectedExperiment))
  }, [selectedExperiment])

  function applyPreset(nextPreset: TablePreset) {
    setPreset(nextPreset)
    setLatexOptions((prev) => ({
      ...prev,
      ...presetOptions[nextPreset],
    }))
  }

  async function loadExperiments() {
    setErr('')
    try {
      const data = await fetchExperiments()
      setExperiments(data)
      if (data.length > 0) {
        setSelectedExperiment((prev) => prev || data[0].id)
      }
    } catch (error) {
      setErr('实验列表加载失败，请检查后端连接。')
      console.error(error)
    }
  }

  async function loadMetrics(experimentId: number) {
    setLoading(true)
    setErr('')
    try {
      const data = await fetchExperimentMetrics(experimentId)
      setMetrics(data)
      const uniqueMetrics = [...new Set(data.map((row) => row.metric_name))]
      setSelectedMetric(uniqueMetrics[0] ?? '')
      setLatexMetrics(uniqueMetrics)
    } catch (error) {
      setErr('指标加载失败，请确认该实验已写入 run metrics。')
      console.error(error)
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateExperiment() {
    if (!newExperimentName.trim()) return
    const item = await createExperiment({
      name: newExperimentName.trim(),
      description: '从前端看板创建',
    })
    setNewExperimentName('')
    await loadExperiments()
    setSelectedExperiment(item.id)
  }

  function toggleLatexMetric(metricName: string) {
    setLatexMetrics((prev) =>
      prev.includes(metricName)
        ? prev.filter((item) => item !== metricName)
        : [...prev, metricName],
    )
  }

  function updateLatexOption<K extends keyof LatexOptions>(key: K, value: LatexOptions[K]) {
    setLatexOptions((prev) => ({
      ...prev,
      [key]: value,
    }))
  }

  async function handleGenerateLatex() {
    if (selectedExperiment === '') return
    setLatexLoading(true)
    setErr('')
    try {
      const response = await generateLatexTable({
        experiment_ids: [Number(selectedExperiment)],
        metric_names: latexMetrics,
        caption: latexOptions.caption,
        label: latexOptions.label,
        note: latexOptions.note,
        placement: 't',
        precision: latexOptions.precision,
        highlight_best: true,
        highlight_second: true,
        use_resizebox: latexOptions.useResizebox,
        compact: latexOptions.compact,
        show_std: latexOptions.showStd,
        omit_zero_std: latexOptions.omitZeroStd,
        use_threeparttable: latexOptions.useThreePartTable,
        table_environment: latexOptions.tableEnvironment,
        column_group_by: latexOptions.columnGroupBy,
      })
      setLatexResponse(response)
      setLatexCode(response.latex_code)
    } catch (error: any) {
      setErr(error?.response?.data?.detail || 'LaTeX 表格生成失败。')
      console.error(error)
    } finally {
      setLatexLoading(false)
    }
  }

  const metricOptions = [...new Set(metrics.map((row) => row.metric_name))]
  const filtered = metrics.filter((row) => !selectedMetric || row.metric_name === selectedMetric)

  const barOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: filtered.map((row) => row.run_name ?? `run-${row.run_id}`),
      axisLabel: { rotate: 22, color: '#334155' },
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#334155' },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [
      {
        type: 'bar',
        data: filtered.map((row) => row.metric_value),
        itemStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: '#0ea5e9' },
              { offset: 1, color: '#0369a1' },
            ],
          },
          borderRadius: [6, 6, 0, 0],
        },
      },
    ],
    grid: { left: 44, right: 18, top: 16, bottom: 72 },
  }

  const lineOption = {
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: filtered.map((row, idx) => `${row.run_name ?? `run-${row.run_id}`}#${idx + 1}`),
      axisLabel: { color: '#334155' },
      axisLine: { lineStyle: { color: '#94a3b8' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#334155' },
      splitLine: { lineStyle: { color: '#e2e8f0' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: filtered.map((row) => row.metric_value),
        lineStyle: { width: 3, color: '#0f766e' },
        itemStyle: { color: '#0f766e' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(15,118,110,0.24)' },
              { offset: 1, color: 'rgba(15,118,110,0.04)' },
            ],
          },
        },
      },
    ],
    grid: { left: 44, right: 18, top: 16, bottom: 46 },
  }

  return (
    <div className="space-y-4">
      <Panel
        title="实验结果看板"
        subtitle="按实验聚合指标、生成对比图，并输出更贴近顶会投稿习惯的 LaTeX 表格。"
      >
        <div className="grid gap-3 md:grid-cols-[1fr_220px_190px]">
          <input
            value={newExperimentName}
            onChange={(e) => setNewExperimentName(e.target.value)}
            placeholder="输入新实验名称"
            className="input-field"
          />
          <button onClick={handleCreateExperiment} className="btn btn-primary">
            新建实验
          </button>
          <select
            value={selectedExperiment}
            onChange={(e) =>
              setSelectedExperiment(e.target.value ? Number(e.target.value) : '')
            }
            className="input-field"
          >
            <option value="">选择实验</option>
            {experiments.map((exp) => (
              <option key={exp.id} value={exp.id}>
                {exp.name}
              </option>
            ))}
          </select>
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="chip">实验数：{experiments.length}</span>
          <span className="chip">指标记录：{metrics.length}</span>
          <span className="chip">当前筛选：{selectedMetric || '全部'}</span>
          {loading && <span className="chip">加载中...</span>}
        </div>
        {err && <p className="mt-3 text-sm text-rose-600">{err}</p>}
      </Panel>

      <Panel title="指标筛选">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedMetric}
            onChange={(e) => setSelectedMetric(e.target.value)}
            className="input-field"
          >
            {metricOptions.length === 0 && <option value="">暂无指标</option>}
            {metricOptions.map((metric) => (
              <option key={metric} value={metric}>
                {metric}
              </option>
            ))}
          </select>
        </div>
      </Panel>

      <div className="grid gap-4 xl:grid-cols-2">
        <Panel title="模型性能柱状对比图" subtitle="适合同一指标下的横向比较。">
          <ReactECharts option={barOption} style={{ height: 360 }} />
        </Panel>
        <Panel title="性能趋势折线图" subtitle="适合观察不同 run 之间的变化趋势。">
          <ReactECharts option={lineOption} style={{ height: 360 }} />
        </Panel>
      </div>

      <Panel
        title="论文表格工作台"
        subtitle="内置 CVPR / NeurIPS / 宽表预设，支持脚注、双栏表、threeparttable 和列分组方式。"
      >
        <div className="grid gap-4 xl:grid-cols-[1.1fr_1.3fr]">
          <div className="space-y-4">
            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-700">投稿预设</p>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => applyPreset('cvpr')} className={checkboxClass(preset === 'cvpr')}>
                  CVPR 风格
                </button>
                <button type="button" onClick={() => applyPreset('neurips')} className={checkboxClass(preset === 'neurips')}>
                  NeurIPS 风格
                </button>
                <button type="button" onClick={() => applyPreset('compact')} className={checkboxClass(preset === 'compact')}>
                  宽表压缩
                </button>
              </div>
            </div>

            <input
              value={latexOptions.caption}
              onChange={(e) => updateLatexOption('caption', e.target.value)}
              className="input-field w-full"
              placeholder="caption"
            />
            <input
              value={latexOptions.label}
              onChange={(e) => updateLatexOption('label', e.target.value)}
              className="input-field w-full code-text"
              placeholder="tab:main-results"
            />
            <textarea
              value={latexOptions.note}
              onChange={(e) => updateLatexOption('note', e.target.value)}
              className="input-field w-full"
              rows={4}
              placeholder="表格脚注"
            />

            <div className="grid gap-3 md:grid-cols-2">
              <select
                value={latexOptions.tableEnvironment}
                onChange={(e) => updateLatexOption('tableEnvironment', e.target.value as 'table' | 'table*')}
                className="input-field"
              >
                <option value="table">单栏表 `table`</option>
                <option value="table*">双栏表 `table*`</option>
              </select>
              <select
                value={latexOptions.columnGroupBy}
                onChange={(e) => updateLatexOption('columnGroupBy', e.target.value as 'dataset' | 'metric')}
                className="input-field"
              >
                <option value="dataset">按数据集分组列</option>
                <option value="metric">按指标分组列</option>
              </select>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm text-slate-700">
                小数位数
                <input
                  type="number"
                  min={1}
                  max={4}
                  value={latexOptions.precision}
                  onChange={(e) => updateLatexOption('precision', Number(e.target.value))}
                  className="input-field mt-1 w-full"
                />
              </label>
              <div className="space-y-2">
                <p className="text-sm font-semibold text-slate-700">输出选项</p>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => updateLatexOption('useResizebox', !latexOptions.useResizebox)} className={checkboxClass(latexOptions.useResizebox)}>
                    resizebox
                  </button>
                  <button type="button" onClick={() => updateLatexOption('useThreePartTable', !latexOptions.useThreePartTable)} className={checkboxClass(latexOptions.useThreePartTable)}>
                    threeparttable
                  </button>
                  <button type="button" onClick={() => updateLatexOption('showStd', !latexOptions.showStd)} className={checkboxClass(latexOptions.showStd)}>
                    mean ± std
                  </button>
                  <button type="button" onClick={() => updateLatexOption('omitZeroStd', !latexOptions.omitZeroStd)} className={checkboxClass(latexOptions.omitZeroStd)}>
                    省略零方差
                  </button>
                  <button type="button" onClick={() => updateLatexOption('compact', !latexOptions.compact)} className={checkboxClass(latexOptions.compact)}>
                    紧凑布局
                  </button>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <p className="text-sm font-semibold text-slate-700">纳入表格的指标</p>
              <div className="flex flex-wrap gap-2">
                {metricOptions.map((metric) => (
                  <button
                    key={metric}
                    onClick={() => toggleLatexMetric(metric)}
                    className={checkboxClass(latexMetrics.includes(metric))}
                    type="button"
                  >
                    {metric}
                  </button>
                ))}
              </div>
            </div>

            <button
              onClick={handleGenerateLatex}
              className="btn btn-amber"
              disabled={latexLoading || selectedExperiment === ''}
            >
              {latexLoading ? '生成中...' : '生成 LaTeX 表格'}
            </button>

            {latexResponse && (
              <div className="rounded-xl border border-slate-200 bg-white/70 p-3 text-sm text-slate-700">
                <p className="font-semibold text-slate-800">生成摘要</p>
                <p className="mt-2">
                  已生成 {latexResponse.model_names.length} 个模型、{latexResponse.dataset_names.length} 个数据集、
                  {latexResponse.metric_names.length} 个指标的表格。
                </p>
                <p className="mt-2 font-semibold text-slate-800">推荐宏包</p>
                <p className="code-text mt-1">{latexResponse.packages_hint.join('  ')}</p>
                <p className="mt-2 font-semibold text-slate-800">规范提示</p>
                {latexResponse.guideline_notes.map((note) => (
                  <p key={note} className="mt-1">
                    {note}
                  </p>
                ))}
              </div>
            )}
          </div>

          <textarea
            value={latexCode}
            onChange={(e) => setLatexCode(e.target.value)}
            className="input-field code-text h-[460px] w-full resize-y"
            placeholder="这里会输出可直接放入论文的 LaTeX 表格代码。"
          />
        </div>
      </Panel>

      <Panel title="指标明细表" subtitle="可作为 LaTeX 表格生成的数据底表和人工核对依据。">
        <div className="soft-scroll overflow-x-auto">
          <table className="min-w-full border-separate border-spacing-0">
            <thead>
              <tr className="bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-600">
                <th className="px-3 py-2">run_id</th>
                <th className="px-3 py-2">run_name</th>
                <th className="px-3 py-2">metric</th>
                <th className="px-3 py-2">value</th>
                <th className="px-3 py-2">stage</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, idx) => (
                <tr
                  key={`${row.run_id}-${row.metric_name}-${idx}`}
                  className="text-sm hover:bg-slate-50/70"
                >
                  <td className="border-t border-slate-100 px-3 py-2 code-text">{row.run_id}</td>
                  <td className="border-t border-slate-100 px-3 py-2">
                    {row.run_name ?? '-'}
                  </td>
                  <td className="border-t border-slate-100 px-3 py-2">{row.metric_name}</td>
                  <td className="border-t border-slate-100 px-3 py-2 code-text">
                    {row.metric_value.toFixed(4)}
                  </td>
                  <td className="border-t border-slate-100 px-3 py-2">{row.stage ?? '-'}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td
                    colSpan={5}
                    className="border-t border-slate-100 px-3 py-5 text-center text-sm text-slate-500"
                  >
                    暂无指标数据，请先在后端录入 run metrics。
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )
}
