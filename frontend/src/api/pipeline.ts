import apiClient from './client';
import type { PipelineRun } from '../types/pipeline';

export async function startPipeline(transcriptId: number): Promise<PipelineRun> {
  const { data } = await apiClient.post<PipelineRun>(`/pipeline/start/${transcriptId}`);
  return data;
}

export async function runExtraction(runId: number): Promise<PipelineRun> {
  const { data } = await apiClient.post<PipelineRun>(`/pipeline/${runId}/extract`);
  return data;
}

export async function runSearch(runId: number): Promise<PipelineRun> {
  const { data } = await apiClient.post<PipelineRun>(`/pipeline/${runId}/search`);
  return data;
}

export async function runRanking(runId: number): Promise<PipelineRun> {
  const { data } = await apiClient.post<PipelineRun>(`/pipeline/${runId}/rank`);
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
