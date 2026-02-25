import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getPendingReview } from '../api/review';
import { sendEmail, getSendStatus } from '../api/send';
import ErrorAlert from '../components/common/ErrorAlert';
import LoadingSpinner from '../components/common/LoadingSpinner';
import type { RankedListing } from '../types/listing';

export default function SendPage() {
  const { runId } = useParams();
  const [approved, setApproved] = useState<RankedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [sendResult, setSendResult] = useState<{
    status: string;
    message: string;
  } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        // Load approved listings
        const data = await getPendingReview(Number(runId));
        setApproved(data.rankings.filter((r) => r.approved_by_harry === true));

        // Check if already sent
        const status = await getSendStatus(Number(runId));
        if (status.status === 'sent') {
          setSendResult({
            status: 'sent',
            message: `${status.sent_count} listings were sent on ${status.sent_at ? new Date(status.sent_at).toLocaleString() : 'unknown date'}.`,
          });
        }
      } catch {
        setError('Failed to load send data.');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [runId]);

  const handleSend = async () => {
    if (!recipientEmail.trim()) return;
    setSending(true);
    setError(null);
    try {
      const result = await sendEmail(Number(runId), recipientEmail.trim());
      setSendResult({ status: result.status, message: result.message });
    } catch {
      setError('Failed to send email.');
    } finally {
      setSending(false);
    }
  };

  if (loading) return <LoadingSpinner />;
  if (error && approved.length === 0) return <ErrorAlert message={error} />;

  const alreadySent = sendResult?.status === 'sent';

  return (
    <div className="space-y-6">
      <div>
        <Link
          to={`/pipeline/${runId}/review`}
          className="text-[10px] uppercase tracking-[1px] opacity-50 hover:opacity-100 transition-opacity"
        >
          &larr; Back to Review
        </Link>
        <h1 className="font-heading text-[32px] uppercase mt-2">Send to Client</h1>
      </div>

      {error && <ErrorAlert message={error} />}

      {/* Send summary */}
      <section className="border border-ink bg-surface">
        <div className="p-6 border-b border-ink font-heading uppercase">
          Send Summary
        </div>
        <div className="p-6 space-y-3 text-[12px]">
          <div className="flex justify-between border-b border-ink/20 pb-3">
            <span className="uppercase text-[10px] opacity-50">Pipeline Run</span>
            <span className="font-heading">#{runId}</span>
          </div>
          <div className="flex justify-between border-b border-ink/20 pb-3">
            <span className="uppercase text-[10px] opacity-50">Approved Listings</span>
            <span className="font-heading">{approved.length} Properties</span>
          </div>
          <div className="flex justify-between">
            <span className="uppercase text-[10px] opacity-50">Delivery Method</span>
            <span className="font-heading">Email</span>
          </div>
        </div>
      </section>

      {/* Approved listings */}
      {approved.length > 0 && (
        <section className="border border-ink bg-surface">
          <div className="p-6 border-b border-ink font-heading uppercase">
            Approved Listings
          </div>
          {approved.map((item) => (
            <div
              key={item.id}
              className="border-b border-ink/30 flex items-center gap-4 px-6 py-4"
            >
              <div className="font-heading text-[20px] opacity-30 w-8 text-center">
                {item.rank_position}
              </div>
              <div className="flex-1">
                <span className="font-heading text-[14px] uppercase">
                  {item.listing.address ?? 'Unknown Address'}
                </span>
                <span className="block opacity-70 text-[11px]">
                  ${item.listing.price?.toLocaleString() ?? 'N/A'}
                  {item.listing.bedrooms != null && (
                    <> &middot; {item.listing.bedrooms} bed / {item.listing.bathrooms ?? '?'} bath</>
                  )}
                </span>
              </div>
              <span className="font-heading text-[14px]">
                {Math.round((item.overall_score ?? 0) * 100)}%
              </span>
            </div>
          ))}
        </section>
      )}

      {/* Send form / result */}
      {alreadySent ? (
        <div className="border border-accent-green bg-accent-green/10 p-6 text-center">
          <p className="font-heading text-[18px] uppercase">Listings Sent Successfully</p>
          <p className="text-[11px] opacity-60 mt-2">{sendResult.message}</p>
        </div>
      ) : (
        <section className="border border-ink bg-surface">
          <div className="p-6 border-b border-ink font-heading uppercase">
            Send Email
          </div>
          <div className="p-6 space-y-4">
            <div>
              <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                Recipient Email
              </label>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => { setRecipientEmail(e.target.value); }}
                placeholder="client@example.com"
                className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
              />
            </div>
            <button
              onClick={() => { void handleSend(); }}
              disabled={sending || !recipientEmail.trim() || approved.length === 0}
              className="w-full py-3 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {sending ? 'Sending...' : `Send ${approved.length} Listings`}
            </button>
          </div>
        </section>
      )}

      {sendResult?.status === 'error' && (
        <ErrorAlert message={sendResult.message} />
      )}

      <div className="flex justify-end">
        <Link
          to="/"
          className="px-4 py-2 bg-ink text-surface text-[11px] uppercase tracking-[1px] no-underline hover:opacity-80 transition-opacity"
        >
          Back to Dashboard
        </Link>
      </div>
    </div>
  );
}
