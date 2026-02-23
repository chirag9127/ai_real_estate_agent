import apiClient from './client';

export interface SendResponse {
  pipeline_run_id: number;
  status: string;
  recipient?: string;
  listings_sent?: number;
  message: string;
}

export interface SendStatusResponse {
  pipeline_run_id: number;
  status: string;
  sent_count: number;
  approved_count: number;
  sent_at: string | null;
}

export async function sendEmail(
  pipelineRunId: number,
  recipientEmail: string,
): Promise<SendResponse> {
  const { data } = await apiClient.post<SendResponse>(
    `/send/${pipelineRunId}`,
    { recipient_email: recipientEmail },
  );
  return data;
}

export async function getSendStatus(pipelineRunId: number): Promise<SendStatusResponse> {
  const { data } = await apiClient.get<SendStatusResponse>(
    `/send/status/${pipelineRunId}`,
  );
  return data;
}
