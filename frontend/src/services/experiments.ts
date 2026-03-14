import { api } from './api'
import type { Experiment, ExperimentMetricsRow } from '../types'

export async function fetchExperiments() {
  const { data } = await api.get<Experiment[]>('/experiments')
  return data
}

export async function createExperiment(payload: {
  name: string
  description?: string
  task_name?: string
  owner?: string
}) {
  const { data } = await api.post<Experiment>('/experiments', payload)
  return data
}

export async function fetchExperimentMetrics(experimentId: number) {
  const { data } = await api.get<ExperimentMetricsRow[]>(
    `/experiments/${experimentId}/metrics`,
  )
  return data
}
