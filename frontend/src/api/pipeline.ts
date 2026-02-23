import apiClient from './client';
import type { PipelineRun } from '../types/pipeline';

export async function runPipeline(transcriptId: number): Promise<PipelineRun> {
  const { data } = await apiClient.post<PipelineRun>(`/pipeline/run/${transcriptId}`);
  return data;
}

export async function getPipelineRun(runId: number): Promise<PipelineRun> {
  const { data } = await apiClient.get<PipelineRun>(`/pipeline/${runId}`);
  return data;
}

export async function listPipelineRuns(): Promise<PipelineRun[]> {
  const { data } = await apiClient.get<PipelineRun[]>('/pipeline');
  return data;
}
