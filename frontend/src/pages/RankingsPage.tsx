import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getRankings } from '../api/rankings';
import ErrorAlert from '../components/common/ErrorAlert';
import LoadingSpinner from '../components/common/LoadingSpinner';
import type { RankedListing } from '../types/listing';

export default function RankingsPage() {
  const { runId } = useParams();
  const [rankings, setRankings] = useState<RankedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getRankings(Number(runId));
        setRankings(data.rankings);
      } catch {
        setError('Failed to load rankings.');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [runId]);

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
      </div>

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
                onMouseEnter={() => { setHovered(item.id); }}
                onMouseLeave={() => { setHovered(null); }}
                onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
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
