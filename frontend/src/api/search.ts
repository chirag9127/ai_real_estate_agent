import apiClient from './client';
import type { Listing } from '../types/listing';

export async function getSearchResults(pipelineRunId: number): Promise<Listing[]> {
  const { data } = await apiClient.get<Listing[]>(`/search/results/${pipelineRunId}`);
  return data;
}
