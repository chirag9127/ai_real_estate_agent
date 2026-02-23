export interface Transcript {
  id: number;
  client_id: number | null;
  filename: string | null;
  raw_text: string;
  upload_method: 'file' | 'paste';
  status: 'uploaded' | 'extracting' | 'extracted' | 'failed';
  created_at: string;
}

export interface TranscriptListItem {
  id: number;
  client_id: number | null;
  filename: string | null;
  upload_method: 'file' | 'paste';
  status: string;
  created_at: string;
}
