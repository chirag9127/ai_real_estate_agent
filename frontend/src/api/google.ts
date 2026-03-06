import apiClient from './client';

export interface GoogleDocItem {
  id: string;
  name: string;
  modifiedTime: string;
}

export interface GoogleCredentials {
  token: string;
  refresh_token: string | null;
  token_uri: string;
  client_id: string;
  client_secret: string;
  scopes: string[];
}

export async function getAuthUrl(): Promise<string> {
  const { data } = await apiClient.get<{ auth_url: string }>('/google/auth-url');
  return data.auth_url;
}

export async function exchangeCode(code: string): Promise<GoogleCredentials> {
  const { data } = await apiClient.post<{ credentials: GoogleCredentials }>(
    '/google/callback',
    { code },
  );
  return data.credentials;
}

export async function listDocs(credentials: GoogleCredentials): Promise<GoogleDocItem[]> {
  const { data } = await apiClient.post<GoogleDocItem[]>('/google/docs/list', {
    credentials,
  });
  return data;
}

export async function importDoc(
  credentials: GoogleCredentials,
  docId: string,
): Promise<{ id: number }> {
  const { data } = await apiClient.post<{ id: number }>('/google/docs', {
    credentials,
    document_id: docId,
  });
  return data;
}
