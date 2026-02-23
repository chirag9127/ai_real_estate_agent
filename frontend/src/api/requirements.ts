import apiClient from './client';
import type { ExtractedRequirement, RequirementUpdate } from '../types/requirement';

export async function extractRequirements(transcriptId: number): Promise<ExtractedRequirement> {
  const { data } = await apiClient.post<ExtractedRequirement>(
    `/transcripts/${transcriptId}/extract`
  );
  return data;
}

export async function getRequirement(id: number): Promise<ExtractedRequirement> {
  const { data } = await apiClient.get<ExtractedRequirement>(`/requirements/${id}`);
  return data;
}

export async function getRequirementByTranscript(
  transcriptId: number
): Promise<ExtractedRequirement> {
  const { data } = await apiClient.get<ExtractedRequirement>(
    `/transcripts/${transcriptId}/requirements`
  );
  return data;
}

export async function updateRequirement(
  id: number,
  updates: RequirementUpdate
): Promise<ExtractedRequirement> {
  const { data } = await apiClient.put<ExtractedRequirement>(`/requirements/${id}`, updates);
  return data;
}
