export type PipelineStage = 'ingestion' | 'extraction' | 'search' | 'ranking' | 'review' | 'send';
export type PipelineStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export interface PipelineRun {
  id: number;
  transcript_id: number;
  current_stage: PipelineStage;
  status: PipelineStatus;
  ingestion_completed_at: string | null;
  extraction_completed_at: string | null;
  search_completed_at: string | null;
  ranking_completed_at: string | null;
  review_completed_at: string | null;
  send_completed_at: string | null;
  error_message: string | null;
  created_at: string;
}
