import apiClient from './client';
import type { RankedListing } from '../types/listing';

export interface RankingsResponse {
  pipeline_run_id: number;
  rankings: RankedListing[];
  total: number;
}

export async function getRankings(pipelineRunId: number): Promise<RankingsResponse> {
  const { data } = await apiClient.get<RankingsResponse>(`/rankings/${pipelineRunId}`);
  return data;
}
