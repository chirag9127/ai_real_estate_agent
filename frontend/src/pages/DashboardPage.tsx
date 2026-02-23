import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { listTranscripts } from '../api/transcripts';
import { listPipelineRuns } from '../api/pipeline';
import type { TranscriptListItem } from '../types/transcript';
import type { PipelineRun } from '../types/pipeline';
import StatusBadge from '../components/common/StatusBadge';
import PipelineProgress from '../components/pipeline/PipelineProgress';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

function KPICard({
  color,
  label,
  number,
  icon,
  value,
  subtitle,
}: {
  color: 'orange' | 'green' | 'white';
  label: string;
  number: string;
  icon: string;
  value: string;
  subtitle: string;
}) {
  const bgColor =
    color === 'orange'
      ? 'bg-accent-orange'
      : color === 'green'
        ? 'bg-accent-green'
        : 'bg-[#f2f2f2]';

  return (
    <article
      className={`border border-ink p-6 flex flex-col justify-between min-h-[220px] relative ${bgColor}`}
    >
      <div className="font-mono text-[10px] uppercase tracking-[1px] flex justify-between border-b border-ink/10 pb-1">
        <span>{label}</span>
        <span>{number}</span>
      </div>
      <div className="w-10 h-10 border border-ink rounded-full flex items-center justify-center text-[20px] mb-16">
        {icon}
      </div>
      <div>
        <div className="font-heading text-[48px] uppercase leading-[0.9]">{value}</div>
        <div className="text-[10px] mt-2 opacity-70">{subtitle}</div>
      </div>
      {color === 'white' && (
        <div className="absolute opacity-50 pointer-events-none border border-ink rounded-full w-20 h-20 -right-5 -bottom-5" />
      )}
    </article>
  );
}

function FilterPill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  const [hovered, setHovered] = useState(false);
  const show = active || hovered;

  return (
    <button
      className="px-3 py-1 border border-ink rounded-full text-[11px] uppercase cursor-pointer transition-all duration-200"
      style={{
        background: show ? '#0d0d0d' : 'transparent',
        color: show ? '#d4d4d4' : '#0d0d0d',
      }}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {children}
    </button>
  );
}

export default function DashboardPage() {
  const [transcripts, setTranscripts] = useState<TranscriptListItem[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<PipelineRun[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState('All');

  useEffect(() => {
    async function load() {
      try {
        const [t, p] = await Promise.all([listTranscripts(), listPipelineRuns()]);
        setTranscripts(t);
        setPipelineRuns(p);
      } catch {
        setError('Failed to load dashboard data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  const stats = {
    total: transcripts.length,
    extracted: transcripts.filter((t) => t.status === 'extracted').length,
    pending: transcripts.filter((t) => t.status === 'uploaded').length,
    pipelines: pipelineRuns.length,
  };

  const filteredTranscripts =
    activeFilter === 'All'
      ? transcripts
      : activeFilter === 'Extracted'
        ? transcripts.filter((t) => t.status === 'extracted')
        : transcripts.filter((t) => t.status === 'uploaded');

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-3 gap-6">
        <KPICard
          color="orange"
          label="Total Transcripts"
          number="01"
          icon="☻"
          value={String(stats.total)}
          subtitle={`${stats.extracted} extracted`}
        />
        <KPICard
          color="green"
          label="Pipeline Runs"
          number="02"
          icon="⊕"
          value={String(stats.pipelines)}
          subtitle="End-to-end workflows"
        />
        <KPICard
          color="white"
          label="Pending"
          number="03"
          icon="✉"
          value={String(stats.pending)}
          subtitle="Awaiting extraction"
        />
      </div>

      {/* Active Pipelines */}
      {pipelineRuns.length > 0 && (
        <section className="border border-ink bg-surface">
          <div className="p-6 border-b border-ink font-heading uppercase">
            Active Pipelines
          </div>
          <div>
            {pipelineRuns.slice(0, 5).map((run) => (
              <Link
                key={run.id}
                to={`/pipeline/${run.id}`}
                className="flex items-center justify-between px-6 py-4 border-b border-ink/20 hover:bg-ink/5 transition-colors no-underline text-ink"
              >
                <span className="text-[12px] uppercase">
                  Pipeline #{run.id} — Transcript #{run.transcript_id}
                </span>
                <PipelineProgress run={run} />
              </Link>
            ))}
          </div>
        </section>
      )}

      {/* Recent Transcripts */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink flex justify-between items-center">
          <div className="font-heading uppercase">Recent Transcripts</div>
          <div className="flex gap-3">
            <FilterPill active={activeFilter === 'All'} onClick={() => setActiveFilter('All')}>
              All
            </FilterPill>
            <FilterPill
              active={activeFilter === 'Extracted'}
              onClick={() => setActiveFilter('Extracted')}
            >
              Extracted
            </FilterPill>
            <FilterPill
              active={activeFilter === 'Pending'}
              onClick={() => setActiveFilter('Pending')}
            >
              Pending
            </FilterPill>
          </div>
        </div>

        {filteredTranscripts.length === 0 ? (
          <div className="p-6 text-[11px] uppercase opacity-50">
            No transcripts yet. Upload one to get started.
          </div>
        ) : (
          <div>
            {filteredTranscripts.slice(0, 10).map((t) => (
              <Link
                key={t.id}
                to={`/transcripts/${t.id}`}
                className="grid grid-cols-[2fr_1fr_1fr_40px] border-b border-ink items-center hover:bg-white/40 transition-colors no-underline text-ink"
              >
                <div className="px-6 py-3 flex flex-col gap-0.5">
                  <span className="font-heading text-[18px] font-medium">
                    {t.filename || `Transcript #${t.id}`}
                  </span>
                  <span className="opacity-70 uppercase text-[10px]">
                    {t.upload_method} upload
                  </span>
                </div>
                <div className="px-6 py-3">
                  <StatusBadge status={t.status} />
                </div>
                <div className="px-6 py-3 text-[10px]">
                  {new Date(t.created_at).toLocaleDateString()}
                </div>
                <div className="px-6 py-3 text-right">→</div>
              </Link>
            ))}
          </div>
        )}
      </section>

      {/* FAB - Upload */}
      <Link
        to="/upload"
        className="fixed bottom-10 right-10 w-16 h-16 bg-ink rounded-full flex items-center justify-center text-surface text-2xl cursor-pointer shadow-lg z-10 hover:scale-105 transition-transform no-underline"
      >
        →
      </Link>
    </div>
  );
}
