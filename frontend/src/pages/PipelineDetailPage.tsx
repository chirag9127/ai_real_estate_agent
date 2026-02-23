import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getPipelineRun } from '../api/pipeline';
import { getRequirementByTranscript } from '../api/requirements';
import type { PipelineRun } from '../types/pipeline';
import PipelineProgress, {
  STAGES,
  completedAtKey,
  getStageStatus,
  getStageStyle,
  getStageRoute,
} from '../components/pipeline/PipelineProgress';
import StatusBadge from '../components/common/StatusBadge';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

export default function PipelineDetailPage() {
  const { runId } = useParams<{ runId: string }>();
  const [run, setRun] = useState<PipelineRun | null>(null);
  const [requirementId, setRequirementId] = useState<number | undefined>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const pipelineRun = await getPipelineRun(Number(runId));
        setRun(pipelineRun);
        try {
          const req = await getRequirementByTranscript(pipelineRun.transcript_id);
          setRequirementId(req.id);
        } catch { /* no requirement yet */ }
      } catch {
        setError('Failed to load pipeline run.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  if (loading) return <LoadingSpinner />;
  if (error && !run) return <ErrorAlert message={error} />;
  if (!run) return <ErrorAlert message="Pipeline run not found." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link to="/" className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity">
          ← Back to Dashboard
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">Pipeline #{run.id}</h1>
        <div className="flex items-center gap-3 mt-2">
          <StatusBadge status={run.status} />
          <Link
            to={`/transcripts/${run.transcript_id}`}
            className="text-[10px] uppercase opacity-50 hover:opacity-100 transition-opacity"
          >
            Transcript #{run.transcript_id}
          </Link>
          <span className="text-[10px] uppercase opacity-50">
            {new Date(run.created_at).toLocaleString()}
          </span>
        </div>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Progress Stepper */}
      <section className="border border-ink bg-surface p-6 flex justify-center">
        <PipelineProgress run={run} clickable requirementId={requirementId} />
      </section>

      {/* Stage Detail List */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Pipeline Stages
        </div>
        {STAGES.map((stage, i) => {
          const status = getStageStatus(stage.key, run);
          const style = getStageStyle(status);
          const route = getStageRoute(stage.key, run, requirementId);
          const isNavigable = status !== 'pending';

          const content = (
            <>
              <div className="px-4 py-4 flex items-center justify-center">
                <div
                  className="w-7 h-7 flex items-center justify-center text-[9px] font-medium border"
                  style={{ background: style.bg, color: style.color, borderColor: style.border }}
                >
                  {status === 'completed' ? '✓' : i + 1}
                </div>
              </div>
              <div className="px-6 py-4 font-heading text-[16px] uppercase">
                {stage.label}
              </div>
              <div className="px-6 py-4">
                <StatusBadge status={status} />
              </div>
              <div className="px-6 py-4 text-[10px] opacity-70">
                {run[completedAtKey[stage.key]]
                  ? new Date(run[completedAtKey[stage.key]] as string).toLocaleString()
                  : '—'}
              </div>
              <div className="px-6 py-4 text-right">{isNavigable ? '→' : ''}</div>
            </>
          );

          const className = `grid grid-cols-[50px_2fr_1fr_1fr_40px] border-b border-ink/20 items-center transition-colors ${
            isNavigable ? 'hover:bg-ink/5 cursor-pointer no-underline text-ink' : 'opacity-50'
          }`;

          return isNavigable ? (
            <Link key={stage.key} to={route} className={className}>
              {content}
            </Link>
          ) : (
            <div key={stage.key} className={className}>
              {content}
            </div>
          );
        })}
      </section>

      {run.error_message && (
        <ErrorAlert message={`Pipeline error: ${run.error_message}`} />
      )}
    </div>
  );
}
