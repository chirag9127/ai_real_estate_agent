import { Link } from 'react-router-dom';
import type { PipelineRun, PipelineStage } from '../../types/pipeline';

export const STAGES: { key: PipelineStage; label: string }[] = [
  { key: 'ingestion', label: 'Ingest' },
  { key: 'extraction', label: 'Extract' },
  { key: 'search', label: 'Search' },
  { key: 'ranking', label: 'Rank' },
  { key: 'review', label: 'Review' },
  { key: 'send', label: 'Send' },
];

export const completedAtKey: Record<PipelineStage, keyof PipelineRun> = {
  ingestion: 'ingestion_completed_at',
  extraction: 'extraction_completed_at',
  search: 'search_completed_at',
  ranking: 'ranking_completed_at',
  review: 'review_completed_at',
  send: 'send_completed_at',
};

export function getStageStatus(
  stage: PipelineStage,
  run: PipelineRun
): 'completed' | 'active' | 'pending' | 'failed' {
  if (run.status === 'failed' && run.current_stage === stage) return 'failed';
  if (run[completedAtKey[stage]]) return 'completed';
  if (run.current_stage === stage) return 'active';
  return 'pending';
}

export function getStageStyle(status: 'completed' | 'active' | 'pending' | 'failed') {
  switch (status) {
    case 'completed':
      return { bg: '#4f9664', color: '#fff', border: '#4f9664' };
    case 'active':
      return { bg: '#ff5e25', color: '#0d0d0d', border: '#ff5e25' };
    case 'failed':
      return { bg: '#ff5e25', color: '#fff', border: '#ff5e25' };
    default:
      return { bg: 'transparent', color: '#0d0d0d', border: '#0d0d0d' };
  }
}

export function getStageRoute(
  stage: PipelineStage,
  run: PipelineRun,
  requirementId?: number
): string {
  switch (stage) {
    case 'ingestion':
      return `/transcripts/${run.transcript_id}`;
    case 'extraction':
      return requirementId
        ? `/requirements/${requirementId}`
        : `/transcripts/${run.transcript_id}`;
    case 'search':
      return `/pipeline/${run.id}/search`;
    case 'ranking':
      return `/pipeline/${run.id}/rankings`;
    case 'review':
      return `/pipeline/${run.id}/review`;
    case 'send':
      return `/pipeline/${run.id}/send`;
  }
}

interface PipelineProgressProps {
  run: PipelineRun;
  clickable?: boolean;
  requirementId?: number;
}

export default function PipelineProgress({ run, clickable = false, requirementId }: PipelineProgressProps) {
  return (
    <div className="flex items-center gap-1">
      {STAGES.map((stage, i) => {
        const status = getStageStatus(stage.key, run);
        const style = getStageStyle(status);
        const isNavigable = clickable && status !== 'pending';
        const route = getStageRoute(stage.key, run, requirementId);

        const stageBox = (
          <div
            className={`w-7 h-7 flex items-center justify-center text-[9px] font-medium border ${
              status === 'active' ? 'animate-pulse' : ''
            } ${isNavigable ? 'cursor-pointer hover:opacity-70 transition-opacity' : ''}`}
            style={{
              background: style.bg,
              color: style.color,
              borderColor: style.border,
            }}
          >
            {status === 'completed' ? '✓' : i + 1}
          </div>
        );

        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center">
              {isNavigable ? (
                <Link to={route} className="no-underline">
                  {stageBox}
                </Link>
              ) : (
                stageBox
              )}
              <span className="text-[8px] uppercase mt-1 opacity-60">{stage.label}</span>
            </div>
            {i < STAGES.length - 1 && (
              <div
                className="w-4 h-[1px] mx-0.5"
                style={{
                  background: status === 'completed' ? '#4f9664' : '#0d0d0d20',
                }}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
