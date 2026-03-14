import { useEffect, useMemo, useState } from 'react'

import { Panel } from '../components/common/Panel'
import {
  compileProject,
  fetchPaperProjects,
  fetchProjectFile,
  fetchProjectFiles,
  saveProjectFile,
  type PaperCompileResponse,
  type PaperProjectSummary,
} from '../services/paperEditor'

export function PaperEditorPage() {
  const [projects, setProjects] = useState<PaperProjectSummary[]>([])
  const [selectedProject, setSelectedProject] = useState('')
  const [files, setFiles] = useState<string[]>([])
  const [selectedFile, setSelectedFile] = useState('')
  const [content, setContent] = useState('')
  const [savedContent, setSavedContent] = useState('')
  const [pdfUrl, setPdfUrl] = useState('')
  const [compileLog, setCompileLog] = useState('编译日志会显示在这里。')
  const [autoCompile, setAutoCompile] = useState(false)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [compiling, setCompiling] = useState(false)
  const [error, setError] = useState('')
  const [previewKey, setPreviewKey] = useState(Date.now())

  useEffect(() => {
    void bootstrap()
  }, [])

  useEffect(() => {
    if (!selectedProject) return
    void loadProjectFiles(selectedProject)
  }, [selectedProject])

  useEffect(() => {
    if (!selectedProject || !selectedFile) return
    void loadFile(selectedProject, selectedFile)
  }, [selectedProject, selectedFile])

  useEffect(() => {
    if (!autoCompile || !selectedProject || !selectedFile) return
    if (content === savedContent) return

    const timer = window.setTimeout(() => {
      void handleCompile()
    }, 1500)

    return () => window.clearTimeout(timer)
  }, [autoCompile, content, savedContent, selectedFile, selectedProject])

  async function bootstrap() {
    setLoading(true)
    setError('')
    try {
      const projectList = await fetchPaperProjects()
      setProjects(projectList)
      if (projectList.length > 0) {
        const latest = projectList[0]
        setSelectedProject(latest.project_name)
        setPdfUrl(latest.pdf_url ?? '')
      }
    } catch (e) {
      setError('论文项目加载失败，请确认后端服务正在运行。')
    } finally {
      setLoading(false)
    }
  }

  async function loadProjectFiles(projectName: string) {
    setLoading(true)
    setError('')
    try {
      const [projectFiles, projectList] = await Promise.all([
        fetchProjectFiles(projectName),
        fetchPaperProjects(),
      ])
      setProjects(projectList)
      setFiles(projectFiles)
      setSelectedFile((prev) => (prev && projectFiles.includes(prev) ? prev : projectFiles[0] ?? ''))
      const project = projectList.find((item) => item.project_name === projectName)
      setPdfUrl(project?.pdf_url ?? '')
    } catch (e) {
      setError('论文文件列表加载失败。')
    } finally {
      setLoading(false)
    }
  }

  async function loadFile(projectName: string, filePath: string) {
    setLoading(true)
    setError('')
    try {
      const file = await fetchProjectFile(projectName, filePath)
      setContent(file.content)
      setSavedContent(file.content)
    } catch (e) {
      setError('文件内容加载失败。')
    } finally {
      setLoading(false)
    }
  }

  async function handleSave() {
    if (!selectedProject || !selectedFile) return
    setSaving(true)
    setError('')
    try {
      const file = await saveProjectFile(selectedProject, selectedFile, content)
      setSavedContent(file.content)
    } catch (e) {
      setError('保存失败，请稍后重试。')
    } finally {
      setSaving(false)
    }
  }

  async function handleCompile() {
    if (!selectedProject) return
    setCompiling(true)
    setError('')
    try {
      if (content !== savedContent && selectedFile) {
        const file = await saveProjectFile(selectedProject, selectedFile, content)
        setSavedContent(file.content)
      }
      const result = await compileProject(selectedProject)
      applyCompileResult(result)
      const projectList = await fetchPaperProjects()
      setProjects(projectList)
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setError(detail || '编译失败，请查看日志。')
    } finally {
      setCompiling(false)
    }
  }

  function applyCompileResult(result: PaperCompileResponse) {
    setCompileLog(result.log || '没有返回编译日志。')
    if (result.pdf_url) {
      setPdfUrl(result.pdf_url)
      setPreviewKey(Date.now())
    }
  }

  const currentProject = useMemo(
    () => projects.find((item) => item.project_name === selectedProject) ?? null,
    [projects, selectedProject],
  )

  const isDirty = content !== savedContent

  return (
    <div className="space-y-4">
      <Panel
        title="网页实时论文编辑器"
        subtitle="选择生成好的论文工程，编辑 LaTeX 与 BibTeX 文件，保存后重新编译并在右侧实时预览 PDF。"
      >
        <div className="grid gap-3 lg:grid-cols-[1.1fr_200px_auto_auto]">
          <select
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
            className="input-field"
          >
            <option value="">选择论文项目</option>
            {projects.map((project) => (
              <option key={project.project_name} value={project.project_name}>
                {project.title}
              </option>
            ))}
          </select>

          <select
            value={selectedFile}
            onChange={(e) => setSelectedFile(e.target.value)}
            className="input-field code-text"
            disabled={!selectedProject}
          >
            <option value="">选择文件</option>
            {files.map((file) => (
              <option key={file} value={file}>
                {file}
              </option>
            ))}
          </select>

          <button onClick={handleSave} className="btn btn-primary" disabled={!selectedFile || saving}>
            {saving ? '保存中...' : '保存'}
          </button>

          <button
            onClick={handleCompile}
            className="btn btn-amber"
            disabled={!selectedProject || compiling}
          >
            {compiling ? '编译中...' : '保存并编译'}
          </button>
        </div>

        <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-700">
          <span className="chip">项目数：{projects.length}</span>
          <span className="chip">当前文件：{selectedFile || '未选择'}</span>
          <span className="chip">修改状态：{isDirty ? '未保存' : '已保存'}</span>
          <span className="chip">PDF：{currentProject?.pdf_exists ? '已存在' : '待编译'}</span>
          {loading && <span className="chip">加载中...</span>}
          <label className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white/70 px-3 py-1.5">
            <input
              type="checkbox"
              checked={autoCompile}
              onChange={(e) => setAutoCompile(e.target.checked)}
            />
            自动编译预览
          </label>
        </div>
        {error && <p className="mt-3 text-sm text-rose-600">{error}</p>}
      </Panel>

      <div className="grid gap-4 xl:grid-cols-[0.95fr_1.05fr]">
        <Panel
          title="源码编辑"
          subtitle="推荐先改 main.tex、tables/main_results.tex、tables/ablation.tex 和 refs.bib。"
        >
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="input-field code-text h-[760px] w-full resize-y"
            placeholder="这里会显示可编辑的 LaTeX 或 BibTeX 内容。"
            disabled={!selectedFile}
          />
        </Panel>

        <div className="space-y-4">
          <Panel
            title="PDF 预览"
            subtitle="每次“保存并编译”后，右侧预览会自动刷新。若 PDF 仍未生成，请查看下方编译日志。"
          >
            {pdfUrl ? (
              <iframe
                key={previewKey}
                src={`${pdfUrl}?v=${previewKey}`}
                title="paper-pdf-preview"
                className="h-[520px] w-full rounded-2xl border border-slate-200 bg-white"
              />
            ) : (
              <div className="flex h-[520px] items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white/60 text-sm text-slate-500">
                当前项目还没有可预览的 PDF，请先编译一次。
              </div>
            )}
          </Panel>

          <Panel
            title="编译日志"
            subtitle="这里会显示 pdflatex / bibtex 的输出，便于定位编译错误。"
          >
            <pre className="code-text soft-scroll h-[216px] overflow-auto rounded-2xl border border-slate-200 bg-slate-950 p-4 text-xs leading-6 text-slate-100">
              {compileLog}
            </pre>
          </Panel>
        </div>
      </div>
    </div>
  )
}
