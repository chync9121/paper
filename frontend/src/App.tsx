import { NavLink, Navigate, Route, Routes } from 'react-router-dom'

import { DashboardPage } from './pages/DashboardPage'
import { PaperEditorPage } from './pages/PaperEditorPage'
import { KnowledgeGraphPage } from './pages/KnowledgeGraphPage'
import { PaperStudioPage } from './pages/PaperStudioPage'
import { ReportPage } from './pages/ReportPage'

function tabClassName(active: boolean) {
  return [
    'rounded-full px-4 py-2 text-sm font-semibold transition',
    active
      ? 'bg-slate-900 text-white shadow-[0_8px_18px_rgba(15,23,42,0.25)]'
      : 'bg-white/70 text-slate-700 hover:bg-white hover:text-slate-900',
  ].join(' ')
}

export default function App() {
  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-[var(--line)] bg-white/70 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-4 py-4">
          <div className="space-y-1">
            <h1 className="font-title text-xl font-bold text-slate-900">
              知识驱动的实验评估与论文生成系统
            </h1>
            <p className="text-xs text-slate-600">
              文献图谱 · 实验看板 · 顶会表格 · 研报生成 · 论文自动装配
            </p>
            <div className="flex flex-wrap gap-2 pt-1">
              <span className="chip">FastAPI</span>
              <span className="chip">React + Tailwind</span>
              <span className="chip">Matplotlib + Pandas</span>
            </div>
          </div>

          <nav className="flex items-center gap-2">
            <NavLink to="/graph" className={({ isActive }) => tabClassName(isActive)}>
              图谱中心
            </NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => tabClassName(isActive)}>
              实验看板
            </NavLink>
            <NavLink to="/reports" className={({ isActive }) => tabClassName(isActive)}>
              研报生成
            </NavLink>
            <NavLink to="/paper-studio" className={({ isActive }) => tabClassName(isActive)}>
              论文工坊
            </NavLink>
            <NavLink to="/paper-editor" className={({ isActive }) => tabClassName(isActive)}>
              论文编辑器
            </NavLink>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Navigate to="/graph" replace />} />
          <Route path="/graph" element={<KnowledgeGraphPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/reports" element={<ReportPage />} />
          <Route path="/paper-studio" element={<PaperStudioPage />} />
          <Route path="/paper-editor" element={<PaperEditorPage />} />
        </Routes>
      </main>
    </div>
  )
}
