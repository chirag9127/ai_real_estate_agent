import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { getPendingReview, approveListings } from '../api/review';
import ErrorAlert from '../components/common/ErrorAlert';
import LoadingSpinner from '../components/common/LoadingSpinner';
import type { RankedListing } from '../types/listing';

export default function ReviewPage() {
  const { runId } = useParams();
  const navigate = useNavigate();
  const [rankings, setRankings] = useState<RankedListing[]>([]);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getPendingReview(Number(runId));
        setRankings(data.rankings);
        // Pre-select listings that pass all must-haves
        const passing = new Set(
          data.rankings
            .filter((r) => r.must_have_pass)
            .map((r) => r.id),
        );
        setSelected(passing);
      } catch {
        setError('Failed to load review data.');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [runId]);

  const toggle = (id: number) => {
    const next = new Set(selected);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelected(next);
  };

  const selectAll = () => { setSelected(new Set(rankings.map((r) => r.id))); };
  const selectNone = () => { setSelected(new Set()); };

  const handleApprove = async () => {
    setSubmitting(true);
    setError(null);
    try {
      await approveListings(Number(runId), Array.from(selected));
      void navigate(`/pipeline/${runId}/send`);
    } catch {
      setError('Failed to submit approval.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error && rankings.length === 0) return <ErrorAlert message={error} />;

  const passCount = rankings.filter((r) => r.must_have_pass).length;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <Link
          to={`/pipeline/${runId}/rankings`}
          className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity"
        >
          &larr; Back to Rankings
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">Review &amp; Approve</h1>
        <p className="text-[10px] uppercase opacity-50 mt-1">
          {rankings.length} properties &middot; {passCount} pass all must-haves &middot;
          select listings to send to the client
        </p>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Bulk actions */}
      <div className="flex items-center gap-3">
        <button
          onClick={selectAll}
          className="px-3 py-1.5 border border-ink text-[10px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors"
        >
          Select All
        </button>
        <button
          onClick={selectNone}
          className="px-3 py-1.5 border border-ink text-[10px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors"
        >
          Select None
        </button>
        <span className="text-[10px] uppercase opacity-50 ml-auto">
          {selected.size} of {rankings.length} selected
        </span>
      </div>

      {/* Listings */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Listings for Review
        </div>
        {rankings.length === 0 ? (
          <div className="p-6 text-center text-[11px] uppercase opacity-50">
            No ranked listings to review.
          </div>
        ) : (
          rankings.map((item) => {
            const isSelected = selected.has(item.id);
            return (
              <div key={item.id}>
                {/* Main row */}
                <div
                  className="grid grid-cols-[44px_50px_2fr_1fr_1fr_1fr] border-b border-ink/30 items-center transition-colors cursor-pointer"
                  style={{
                    background: isSelected ? 'rgba(79,150,100,0.06)' : 'transparent',
                  }}
                >
                  {/* Checkbox */}
                  <div
                    className="px-3 py-4 flex items-center justify-center"
                    onClick={() => { toggle(item.id); }}
                  >
                    <div
                      className="w-5 h-5 border border-ink flex items-center justify-center text-[11px] transition-colors"
                      style={{
                        background: isSelected ? '#0d0d0d' : 'transparent',
                        color: isSelected ? '#d4d4d4' : 'transparent',
                      }}
                    >
                      &#10003;
                    </div>
                  </div>

                  {/* Rank */}
                  <div
                    className="px-2 py-4 font-heading text-[24px] opacity-30 text-center"
                    onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
                  >
                    {item.rank_position}
                  </div>

                  {/* Address + details */}
                  <div
                    className="px-6 py-4 flex flex-col gap-0.5"
                    onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
                  >
                    <span className="font-heading text-[16px] uppercase">
                      {item.listing.address ?? 'Unknown Address'}
                    </span>
                    <span className="opacity-70 text-[11px]">
                      ${item.listing.price?.toLocaleString() ?? 'N/A'}
                      {item.listing.bedrooms != null && (
                        <> &middot; {item.listing.bedrooms} bed / {item.listing.bathrooms ?? '?'} bath</>
                      )}
                      {item.listing.sqft != null && (
                        <> &middot; {item.listing.sqft.toLocaleString()} sqft</>
                      )}
                    </span>
                  </div>

                  {/* Score */}
                  <div
                    className="px-6 py-4"
                    onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
                  >
                    <div className="text-[9px] uppercase opacity-50 mb-1">Score</div>
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

                  {/* Must-haves */}
                  <div
                    className="px-6 py-4 text-center"
                    onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
                  >
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

                  {/* Nice-to-have */}
                  <div
                    className="px-6 py-4 text-center"
                    onClick={() => { setExpandedId(expandedId === item.id ? null : item.id); }}
                  >
                    <div className="text-[9px] uppercase opacity-50 mb-1">Nice-to-Have</div>
                    <span className="font-heading text-[14px]">
                      {Math.round((item.nice_to_have_score ?? 0) * 100)}%
                    </span>
                  </div>
                </div>

                {/* Expandable breakdown */}
                {expandedId === item.id && item.score_breakdown && (
                  <div className="border-b border-ink/30 bg-ink/5 px-8 py-4 space-y-4">
                    {/* Description */}
                    {item.listing.description && (
                      <div>
                        <div className="text-[9px] uppercase opacity-50 mb-1 font-heading">Description</div>
                        <p className="text-[11px] opacity-70 leading-relaxed max-w-[600px]">
                          {item.listing.description}
                        </p>
                      </div>
                    )}

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
                          ),
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
                                <span className="font-heading w-[32px] text-right">
                                  {Math.round(detail.score * 100)}%
                                </span>
                                <span className="uppercase opacity-70">{name}</span>
                                <span className="opacity-40">{detail.reason}</span>
                              </div>
                            ),
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </section>

      {/* Footer actions */}
      <div className="flex justify-between items-center">
        <p className="text-[10px] uppercase opacity-50">
          {selected.size} listing(s) selected for approval
        </p>
        <button
          onClick={() => {
            void handleApprove();
          }}
          disabled={submitting || selected.size === 0}
          className="px-5 py-2.5 bg-accent-green text-ink text-[11px] uppercase tracking-[1px] border border-ink cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {submitting ? 'Approving...' : `Approve ${selected.size} & Continue`}
        </button>
      </div>
    </div>
  );
}
