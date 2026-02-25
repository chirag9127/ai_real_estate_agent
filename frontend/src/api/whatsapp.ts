import apiClient from './client';

export interface Conversation {
  from_number: string;
  run_id: number;
}

export interface ConversationsResponse {
  conversations: Record<string, number>;
}

export interface SendMessageRequest {
  to_number: string;
  message: string;
}

export interface SendResultsRequest {
  to_number: string;
  pipeline_run_id: number;
}

export interface MessageResponse {
  status: string;
  [key: string]: any;
}

export interface StatusResponse {
  from_number: string;
  status: string;
}

export async function listConversations(): Promise<ConversationsResponse> {
  const { data } = await apiClient.get<ConversationsResponse>('/whatsapp/conversations');
  return data;
}

export async function sendMessage(request: SendMessageRequest): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/whatsapp/send-message', request);
  return data;
}

export async function sendResults(request: SendResultsRequest): Promise<MessageResponse> {
  const { data } = await apiClient.post<MessageResponse>('/whatsapp/send-results', request);
  return data;
}

export async function getStatus(fromNumber: string): Promise<StatusResponse> {
  const { data } = await apiClient.get<StatusResponse>(`/whatsapp/status/${encodeURIComponent(fromNumber)}`);
  return data;
}
