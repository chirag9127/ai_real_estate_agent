import apiClient from './client';
import type { Transcript, TranscriptListItem } from '../types/transcript';

export async function uploadTranscript(file: File): Promise<Transcript> {
  const formData = new FormData();
  formData.append('file', file);
  const { data } = await apiClient.post<Transcript>('/transcripts/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function pasteTranscript(text: string, clientName?: string): Promise<Transcript> {
  const { data } = await apiClient.post<Transcript>('/transcripts/paste', {
    text,
    client_name: clientName,
  });
  return data;
}

export async function listTranscripts(): Promise<TranscriptListItem[]> {
  const { data } = await apiClient.get<TranscriptListItem[]>('/transcripts');
  return data;
}

export async function getTranscript(id: number): Promise<Transcript> {
  const { data } = await apiClient.get<Transcript>(`/transcripts/${id}`);
  return data;
}

export async function deleteTranscript(id: number): Promise<void> {
  await apiClient.delete(`/transcripts/${id}`);
}
