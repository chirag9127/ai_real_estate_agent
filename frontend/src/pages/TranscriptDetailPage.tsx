import { useEffect, useState } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { startPipeline, runExtraction, runSearch, runRanking } from '../api/pipeline';
import { extractRequirements, getRequirementByTranscript } from '../api/requirements';
import { getTranscript, deleteTranscript } from '../api/transcripts';
import ErrorAlert from '../components/common/ErrorAlert';
import LoadingSpinner from '../components/common/LoadingSpinner';
import StatusBadge from '../components/common/StatusBadge';
import type { ExtractedRequirement } from '../types/requirement';
import type { Transcript } from '../types/transcript';

export default function TranscriptDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [requirement, setRequirement] = useState<ExtractedRequirement | null>(null);
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [runningPipeline, setRunningPipeline] = useState(false);
  const [pipelineStage, setPipelineStage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const t = await getTranscript(Number(id));
        setTranscript(t);
        if (t.status === 'extracted') {
          try {
            const req = await getRequirementByTranscript(t.id);
            setRequirement(req);
          } catch { /* no requirement yet */ }
        }
      } catch {
        setError('Failed to load transcript.');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  const handleExtract = async () => {
    if (!transcript) return;
    setExtracting(true);
    setError(null);
    try {
      const req = await extractRequirements(transcript.id);
      setRequirement(req);
      setTranscript({ ...transcript, status: 'extracted' });
    } catch {
      setError('Extraction failed. Please try again.');
      setTranscript({ ...transcript, status: 'failed' });
    } finally {
      setExtracting(false);
    }
  };

  const handleRunPipeline = async () => {
    if (!transcript) return;
    setRunningPipeline(true);
    setError(null);
    try {
      setPipelineStage('Starting pipeline...');
      const run = await startPipeline(transcript.id);

      setPipelineStage('Extracting requirements...');
      await runExtraction(run.id);

      setPipelineStage('Searching listings...');
      await runSearch(run.id);

      setPipelineStage('Ranking results...');
      await runRanking(run.id);

      void navigate(`/pipeline/${run.id}/search`);
    } catch {
      setError('Pipeline failed. Please try again.');
    } finally {
      setRunningPipeline(false);
      setPipelineStage(null);
    }
  };

  const handleDelete = async () => {
    if (!transcript || !confirm('Delete this transcript?')) return;
    try {
      await deleteTranscript(transcript.id);
      void navigate('/');
    } catch {
      setError('Failed to delete transcript.');
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error && !transcript) return <ErrorAlert message={error} />;
  if (!transcript) return <ErrorAlert message="Transcript not found." />;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <Link to="/" className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity">
            ← Back to Dashboard
          </Link>
          <h1 className="font-heading text-[32px] uppercase mt-2">
            {transcript.filename ?? `Transcript #${transcript.id}`}
          </h1>
          <div className="flex items-center gap-3 mt-2">
            <StatusBadge status={transcript.status} />
            <span className="text-[10px] uppercase opacity-50">
              {new Date(transcript.created_at).toLocaleString()} via {transcript.upload_method}
            </span>
          </div>
        </div>
        <div className="flex gap-2">
          {transcript.status === 'uploaded' && (
            <button
              onClick={() => {
                void handleExtract();
              }}
              disabled={extracting}
              className="px-4 py-2 bg-accent-orange text-ink text-[11px] uppercase tracking-[1px] border border-ink cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50"
            >
              {extracting ? 'Extracting...' : 'Extract Requirements'}
            </button>
          )}
          {transcript.status === 'extracted' && requirement && (
            <>
              <Link
                to={`/requirements/${requirement.id}`}
                className="px-4 py-2 bg-accent-green text-ink text-[11px] uppercase tracking-[1px] border border-ink no-underline hover:opacity-80 transition-opacity"
              >
                View Requirements
              </Link>
              <button
                onClick={() => {
                  void handleRunPipeline();
                }}
                disabled={runningPipeline}
                className="px-4 py-2 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-50"
              >
                {runningPipeline ? 'Running Pipeline...' : 'Run Pipeline'}
              </button>
            </>
          )}
          <button
            onClick={() => {
              void handleDelete();
            }}
            className="px-4 py-2 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors"
          >
            Delete
          </button>
        </div>
      </div>

      {runningPipeline && (
        <div className="border border-ink bg-surface p-8 flex flex-col items-center gap-4">
          <div className="h-6 w-6 animate-spin border-2 border-ink border-t-transparent" />
          <p className="text-[11px] uppercase tracking-[1px] opacity-70">
            {pipelineStage ?? 'Running pipeline...'}
          </p>
        </div>
      )}

      {error && <ErrorAlert message={error} />}

      {/* Transcript Content */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Transcript Content
        </div>
        <pre className="whitespace-pre-wrap text-[12px] font-mono p-6 max-h-[600px] overflow-y-auto leading-relaxed">
          {transcript.raw_text}
        </pre>
      </section>
    </div>
  );
}
