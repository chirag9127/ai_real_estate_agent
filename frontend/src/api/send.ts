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

export interface EmailTemplate {
  key: string;
  label: string;
  description: string;
}

export interface PreviewResponse {
  html: string;
  subject: string;
  error?: string;
}

export interface EmailSendRecord {
  id: number;
  pipeline_run_id: number;
  recipient_email: string;
  tone: string;
  subject: string;
  sent_at: string | null;
  client_feedback: string | null;
  client_feedback_at: string | null;
  status: string;
}

export interface BrandingFields {
  agent_phone?: string;
  agent_email?: string;
  brokerage_name?: string;
}

export async function sendEmail(
  pipelineRunId: number,
  recipientEmail: string,
  tone: string = 'professional',
  subject?: string,
  body?: string,
  agentName: string = 'Harry',
  branding: BrandingFields = {},
): Promise<SendResponse> {
  const { data } = await apiClient.post<SendResponse>(
    `/send/${pipelineRunId}`,
    {
      recipient_email: recipientEmail,
      tone,
      subject: subject || null,
      body: body || null,
      agent_name: agentName,
      agent_phone: branding.agent_phone || '',
      agent_email: branding.agent_email || '',
      brokerage_name: branding.brokerage_name || '',
    },
  );
  return data;
}

export async function getSendStatus(pipelineRunId: number): Promise<SendStatusResponse> {
  const { data } = await apiClient.get<SendStatusResponse>(
    `/send/status/${pipelineRunId}`,
  );
  return data;
}

export async function getTemplates(): Promise<EmailTemplate[]> {
  const { data } = await apiClient.get<EmailTemplate[]>('/send/templates');
  return data;
}

export async function previewEmail(
  pipelineRunId: number,
  tone: string = 'professional',
  subject?: string,
  body?: string,
  agentName: string = 'Harry',
  branding: BrandingFields = {},
): Promise<PreviewResponse> {
  const { data } = await apiClient.post<PreviewResponse>(
    `/send/${pipelineRunId}/preview`,
    {
      tone,
      subject: subject || null,
      body: body || null,
      agent_name: agentName,
      agent_phone: branding.agent_phone || '',
      agent_email: branding.agent_email || '',
      brokerage_name: branding.brokerage_name || '',
    },
  );
  return data;
}

export async function getEmailHistory(pipelineRunId: number): Promise<EmailSendRecord[]> {
  const { data } = await apiClient.get<EmailSendRecord[]>(
    `/send/${pipelineRunId}/history`,
  );
  return data;
}

export async function submitFeedback(
  sendId: number,
  feedback: string,
): Promise<EmailSendRecord> {
  const { data } = await apiClient.post<EmailSendRecord>(
    `/send/feedback/${sendId}`,
    { feedback },
  );
  return data;
}
