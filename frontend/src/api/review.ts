import apiClient from './client';
import type { RankedListing } from '../types/listing';

export interface ReviewResponse {
  pipeline_run_id: number;
  rankings: RankedListing[];
  total: number;
}

export async function getPendingReview(pipelineRunId: number): Promise<ReviewResponse> {
  const { data } = await apiClient.get<ReviewResponse>(`/review/${pipelineRunId}`);
  return data;
}

export async function approveListings(
  pipelineRunId: number,
  rankingIds: number[],
): Promise<ReviewResponse> {
  const { data } = await apiClient.post<ReviewResponse>(
    `/review/${pipelineRunId}/approve`,
    { ranking_ids: rankingIds },
  );
  return data;
}

export async function rejectListing(
  pipelineRunId: number,
  rankingId: number,
): Promise<RankedListing> {
  const { data } = await apiClient.post<RankedListing>(
    `/review/${pipelineRunId}/reject/${rankingId}`,
  );
  return data;
}
