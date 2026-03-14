import { api } from './api'

export interface PaperProjectSummary {
  project_name: string
  title: string
  updated_at: string
  pdf_exists: boolean
  pdf_url?: string | null
  tex_url?: string | null
}

export interface PaperFileRead {
  project_name: string
  file_path: string
  content: string
  updated_at: string
}

export interface PaperCompileResponse {
  project_name: string
  success: boolean
  pdf_url?: string | null
  log: string
  compiled_at: string
}

export async function fetchPaperProjects() {
  const { data } = await api.get<PaperProjectSummary[]>('/paper-editor/projects')
  return data
}

export async function fetchProjectFiles(projectName: string) {
  const { data } = await api.get<string[]>(`/paper-editor/projects/${projectName}/files`)
  return data
}

export async function fetchProjectFile(projectName: string, filePath: string) {
  const { data } = await api.get<PaperFileRead>(
    `/paper-editor/projects/${projectName}/files/${filePath}`,
  )
  return data
}

export async function saveProjectFile(projectName: string, filePath: string, content: string) {
  const { data } = await api.put<PaperFileRead>(
    `/paper-editor/projects/${projectName}/files/${filePath}`,
    { content },
  )
  return data
}

export async function compileProject(projectName: string) {
  const { data } = await api.post<PaperCompileResponse>(
    `/paper-editor/projects/${projectName}/compile`,
  )
  return data
}
