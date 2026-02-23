import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getSearchResults } from '../api/search';
import type { Listing } from '../types/listing';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

export default function SearchResultsPage() {
  const { runId } = useParams();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [hovered, setHovered] = useState<number | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const data = await getSearchResults(Number(runId));
        setListings(data);
      } catch {
        setError('Failed to load search results.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  if (loading) return <LoadingSpinner />;
  if (error) return <ErrorAlert message={error} />;

  return (
    <div className="space-y-6">
      <div>
        <Link to={`/pipeline/${runId}`} className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity">
          ← Back to Pipeline
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">Search Results</h1>
        <p className="text-[10px] uppercase opacity-50 mt-1">
          {listings.length} properties found · Pipeline Run #{runId}
        </p>
      </div>

      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Properties Found
        </div>
        {listings.length === 0 ? (
          <div className="p-6 text-center text-[11px] uppercase opacity-50">
            No properties found matching your criteria.
          </div>
        ) : (
          listings.map((listing) => (
            <div
              key={listing.id}
              className="grid grid-cols-[80px_2fr_1fr_1fr_40px] border-b border-ink items-center transition-colors"
              style={{ background: hovered === listing.id ? 'rgba(255,255,255,0.4)' : 'transparent' }}
              onMouseEnter={() => setHovered(listing.id)}
              onMouseLeave={() => setHovered(null)}
            >
              {listing.image_url ? (
                <img
                  src={listing.image_url}
                  alt=""
                  className="w-full h-[50px] object-cover border-r border-ink block"
                />
              ) : (
                <div className="w-full h-[50px] bg-ink/10 border-r border-ink flex items-center justify-center text-[9px] opacity-30">
                  —
                </div>
              )}
              <div className="px-6 py-3 flex flex-col gap-0.5">
                <span className="font-heading text-[18px] font-medium">
                  ${listing.price?.toLocaleString() ?? 'N/A'}
                </span>
                <span className="opacity-70 uppercase text-[10px]">{listing.address}</span>
              </div>
              <div className="px-6 py-3">
                <span
                  className="inline-block px-2 py-0.5 border border-ink text-[9px] uppercase rounded-full"
                >
                  {listing.property_type ?? 'Unknown'}
                </span>
              </div>
              <div className="px-6 py-3 text-[10px]">
                {listing.bedrooms ?? '—'} BEDS / {listing.bathrooms ?? '—'} BATHS
                {listing.sqft ? ` / ${listing.sqft.toLocaleString()} SQFT` : ''}
              </div>
              <div className="px-6 py-3 text-right">
                {listing.zillow_url ? (
                  <a
                    href={listing.zillow_url}
                    target="_blank"
                    rel="noreferrer"
                    className="hover:opacity-60 transition-opacity"
                    onClick={(e) => e.stopPropagation()}
                  >
                    →
                  </a>
                ) : (
                  '→'
                )}
              </div>
            </div>
          ))
        )}
      </section>

      <div className="flex justify-end">
        <Link
          to={`/pipeline/${runId}/rankings`}
          className="px-4 py-2 bg-ink text-surface text-[11px] uppercase tracking-[1px] no-underline hover:opacity-80 transition-opacity"
        >
          View Rankings →
        </Link>
      </div>
    </div>
  );
}
