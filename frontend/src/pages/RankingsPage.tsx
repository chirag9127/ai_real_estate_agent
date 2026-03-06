import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getRankings } from '../api/rankings';
import { runRanking } from '../api/pipeline';
import type { RankedListing, WeightAdjustments } from '../types/listing';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

const BOOST_LABELS: Record<string, string> = {
  location_weight_boost: 'Location',
  price_weight_boost: 'Price / Budget',
  lot_size_weight_boost: 'Lot Size',
  layout_weight_boost: 'Layout / Rooms',
  basement_weight_boost: 'Basement',
};

function getTopBoostReason(adj: WeightAdjustments): string | null {
  let top: string | null = null;
  let max = 1.0;
  for (const [key, value] of Object.entries(adj)) {
    if (value > max) {
      max = value;
      top = BOOST_LABELS[key] ?? key;
    }
  }
  return top;
}

export default function RankingsPage() {
  const { runId } = useParams();
  const [rankings, setRankings] = useState<RankedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [scoringMode, setScoringMode] = useState<'strict' | 'flexible'>('strict');
  const [pendingMode, setPendingMode] = useState<'strict' | 'flexible'>('strict');
  const [reranking, setReranking] = useState(false);
  const [learningExpanded, setLearningExpanded] = useState(false);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRankings(Number(runId));
        setRankings(data.rankings);
        // Detect current scoring mode from first ranking with a breakdown
        const first = data.rankings.find((r: RankedListing) => r.score_breakdown);
        if (first?.score_breakdown?.scoring_mode) {
          const mode = first.score_breakdown.scoring_mode as 'strict' | 'flexible';
          setScoringMode(mode);
          setPendingMode(mode);
        }
      } catch {
        setError('Failed to load rankings.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  async function handleRerank() {
    setReranking(true);
    setError(null);
    try {
      await runRanking(Number(runId), pendingMode);
      const data = await getRankings(Number(runId));
      setRankings(data.rankings);
      setScoringMode(pendingMode);
    } catch {
      setError('Failed to re-rank listings.');
    } finally {
      setReranking(false);
    }
  }

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  const passCount = rankings.filter((r) => r.must_have_pass).length;

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/pipeline/${runId}/search`}
          className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity"
        >
          &larr; Back to Search Results
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">Ranked Properties</h1>
        <p className="text-[10px] uppercase opacity-50 mt-1">
          {rankings.length} properties ranked &middot; {passCount} pass all must-haves &middot; Pipeline Run #{runId}
        </p>

        {/* Scoring mode toggle */}
        <div className="flex items-center gap-3 mt-3">
          <span className="text-[10px] uppercase opacity-50">Scoring Mode:</span>
          <button
            className="px-3 py-1 border text-[10px] uppercase tracking-[1px] transition-opacity"
            style={{
              borderColor: pendingMode === 'strict' ? '#1a1a1a' : '#ccc',
              backgroundColor: pendingMode === 'strict' ? '#1a1a1a' : 'transparent',
              color: pendingMode === 'strict' ? '#fff' : '#1a1a1a',
            }}
            onClick={() => setPendingMode('strict')}
          >
            Strict
          </button>
          <button
            className="px-3 py-1 border text-[10px] uppercase tracking-[1px] transition-opacity"
            style={{
              borderColor: pendingMode === 'flexible' ? '#1a1a1a' : '#ccc',
              backgroundColor: pendingMode === 'flexible' ? '#1a1a1a' : 'transparent',
              color: pendingMode === 'flexible' ? '#fff' : '#1a1a1a',
            }}
            onClick={() => setPendingMode('flexible')}
          >
            Flexible
          </button>
          {pendingMode !== scoringMode && (
            <button
              className="px-3 py-1 bg-ink text-surface text-[10px] uppercase tracking-[1px] hover:opacity-80 transition-opacity disabled:opacity-40"
              disabled={reranking}
              onClick={handleRerank}
            >
              {reranking ? 'Re-ranking…' : 'Re-rank'}
            </button>
          )}
        </div>
      </div>

      {/* Learning adjustments banner */}
      {(() => {
        const first = rankings.find((r) => r.score_breakdown?.weight_adjustments);
        const adj = first?.score_breakdown?.weight_adjustments;
        if (!adj) return null;
        const hasBoost = Object.values(adj).some((v) => v > 1.0);
        if (!hasBoost) return null;
        const topReason = getTopBoostReason(adj);
        return (
          <div className="border border-ink bg-surface p-4">
            <div
              className="flex items-center gap-2 cursor-pointer"
              onClick={() => setLearningExpanded(!learningExpanded)}
            >
              <span className="text-[11px]">&#9889;</span>
              <span className="text-[10px] uppercase tracking-[1px] opacity-70">
                Rankings adjusted based on previous rejection patterns
              </span>
              {topReason && (
                <span className="text-[9px] opacity-50 ml-2">
                  &middot; Top factor: {topReason}
                </span>
              )}
              <span className="text-[9px] ml-auto opacity-40">
                {learningExpanded ? '▲' : '▼'}
              </span>
            </div>
            {learningExpanded && (
              <div className="mt-3 space-y-1">
                {Object.entries(adj).map(([key, value]) => (
                  <div key={key} className="flex items-center gap-2 text-[10px]">
                    <span className="uppercase opacity-70 min-w-[120px]">
                      {BOOST_LABELS[key] ?? key}
                    </span>
                    <div className="w-[60px] h-[3px] bg-ink/10 flex-shrink-0">
                      <div
                        className="h-full bg-ink transition-all"
                        style={{ width: `${Math.min(((value - 1.0) / 1.0) * 100, 100)}%` }}
                      />
                    </div>
                    <span className="font-heading w-[40px] text-right">
                      {value.toFixed(2)}x
                    </span>
                    {value > 1.0 && (
                      <span className="opacity-40">
                        (+{Math.round((value - 1.0) * 100)}% weight)
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })()}

      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">Rankings</div>
        {rankings.length === 0 ? (
          <div className="p-6 text-center text-[11px] uppercase opacity-50">
            No rankings available yet.
          </div>
        ) : (
          rankings.map((item) => (
            <div key={item.id}>
              {/* Main row */}
              <div
                className="grid grid-cols-[50px_2fr_1fr_1fr_1fr] border-b border-ink items-center transition-colors cursor-pointer"
                style={{
                  background: hovered === item.id ? 'rgba(255,255,255,0.4)' : 'transparent',
                }}
                onMouseEnter={() => setHovered(item.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
              >
                <div className="px-4 py-4 font-heading text-[24px] opacity-30 text-center">
                  {item.rank_position}
                </div>
                <div className="px-6 py-4 flex flex-col gap-0.5">
                  <span className="font-heading text-[16px] uppercase">
                    {item.listing.address ?? 'Unknown Address'}
                  </span>
                  <span className="opacity-70 text-[11px]">
                    ${item.listing.price?.toLocaleString() ?? 'N/A'}
                    {item.listing.bedrooms != null && (
                      <> &middot; {item.listing.bedrooms} bed / {item.listing.bathrooms ?? '?'} bath</>
                    )}
                  </span>
                  {item.listing.mls_number ? (
                    <span className="text-[9px] uppercase opacity-50">MLS# {item.listing.mls_number}</span>
                  ) : item.listing.external_id ? (
                    <span className="text-[9px] uppercase opacity-50">ID# {item.listing.external_id}</span>
                  ) : null}
                </div>
                <div className="px-6 py-4">
                  <div className="text-[9px] uppercase opacity-50 mb-1">Overall</div>
                  <div className="w-full h-[3px] bg-ink/10">
                    <div
                      className="h-full bg-ink transition-all"
                      style={{ width: `${(item.overall_score ?? 0) * 100}%` }}
                    />
                  </div>
                  <div className="text-[11px] mt-1 font-heading">
                    {Math.round((item.overall_score ?? 0) * 100)}%
                  </div>
                </div>
                <div className="px-6 py-4 text-center">
                  <div className="text-[9px] uppercase opacity-50 mb-1">Must-Haves</div>
                  <span
                    className="inline-block px-2 py-0.5 border text-[9px] uppercase rounded-full"
                    style={{
                      borderColor: item.must_have_pass ? '#4f9664' : '#ff5e25',
                      color: item.must_have_pass ? '#4f9664' : '#ff5e25',
                    }}
                  >
                    {item.must_have_pass ? 'Pass' : 'Fail'}
                  </span>
                </div>
                <div className="px-6 py-4 text-center">
                  <div className="text-[9px] uppercase opacity-50 mb-1">Nice-to-Have</div>
                  <span className="font-heading text-[14px]">
                    {Math.round((item.nice_to_have_score ?? 0) * 100)}%
                  </span>
                </div>
              </div>

              {/* Expandable breakdown */}
              {expandedId === item.id && item.score_breakdown && (
                <div className="border-b border-ink bg-ink/5 px-8 py-4 space-y-4">
                  {/* Satisfaction summary */}
                  <div className="flex gap-6">
                    <div>
                      <div className="text-[9px] uppercase opacity-50 mb-1 font-heading">
                        Must-Have Satisfaction
                      </div>
                      <span className="font-heading text-[14px]">
                        {Math.round(item.score_breakdown.must_have_satisfaction * 100)}%
                      </span>
                    </div>
                    <div>
                      <div className="text-[9px] uppercase opacity-50 mb-1 font-heading">
                        Nice-to-Have Satisfaction
                      </div>
                      <span className="font-heading text-[14px]">
                        {Math.round(item.score_breakdown.nice_to_have_satisfaction * 100)}%
                      </span>
                    </div>
                    <div>
                      <div className="text-[9px] uppercase opacity-50 mb-1 font-heading">
                        Mode
                      </div>
                      <span className="text-[10px] uppercase opacity-70">
                        {item.score_breakdown.scoring_mode}
                      </span>
                    </div>
                  </div>

                  {/* Must-have checks */}
                  <div>
                    <div className="text-[9px] uppercase opacity-50 mb-2 font-heading">
                      Must-Have Checks
                    </div>
                    <div className="space-y-1.5">
                      {Object.entries(item.score_breakdown.must_have_checks).map(
                        ([name, check]) => (
                          <div key={name} className="flex items-center gap-2 text-[10px]">
                            <span
                              className="w-[6px] h-[6px] rounded-full inline-block flex-shrink-0"
                              style={{ backgroundColor: check.pass ? '#4f9664' : '#ff5e25' }}
                            />
                            <span className="uppercase opacity-70 min-w-[100px]">{name}</span>
                            <span className="opacity-40">{check.reason}</span>
                          </div>
                        )
                      )}
                    </div>
                  </div>

                  {/* Nice-to-have details */}
                  {Object.keys(item.score_breakdown.nice_to_have_details).length > 0 && (
                    <div>
                      <div className="text-[9px] uppercase opacity-50 mb-2 font-heading">
                        Nice-to-Have Scores
                      </div>
                      <div className="space-y-1.5">
                        {Object.entries(item.score_breakdown.nice_to_have_details).map(
                          ([name, detail]) => (
                            <div key={name} className="flex items-center gap-2 text-[10px]">
                              <div className="w-[40px] h-[3px] bg-ink/10 flex-shrink-0">
                                <div
                                  className="h-full"
                                  style={{
                                    width: `${detail.score * 100}%`,
                                    backgroundColor: '#4f9664',
                                  }}
                                />
                              </div>
                              <span className="font-heading w-[32px] text-right">{Math.round(detail.score * 100)}%</span>
                              <span className="uppercase opacity-70">{name}</span>
                              <span className="opacity-40">{detail.reason}</span>
                            </div>
                          )
                        )}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))
        )}
      </section>

      <div className="flex justify-end">
        <Link
          to={`/pipeline/${runId}/review`}
          className="px-4 py-2 bg-ink text-surface text-[11px] uppercase tracking-[1px] no-underline hover:opacity-80 transition-opacity"
        >
          Review &rarr;
        </Link>
      </div>
    </div>
  );
}
