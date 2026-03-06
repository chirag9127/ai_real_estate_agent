import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { getPendingReview } from '../api/review';
import {
  sendEmail,
  getSendStatus,
  previewEmail,
  getEmailHistory,
  submitFeedback,
} from '../api/send';
import type { EmailSendRecord } from '../api/send';
import type { RankedListing } from '../types/listing';
import LoadingSpinner from '../components/common/LoadingSpinner';
import ErrorAlert from '../components/common/ErrorAlert';

const TONE_OPTIONS = [
  { key: 'professional', label: 'Professional' },
  { key: 'casual', label: 'Casual' },
  { key: 'advisory', label: 'Advisory' },
] as const;

const DEFAULT_SUBJECTS: Record<string, string> = {
  professional: 'Your Curated Property Listings',
  casual: 'Found some great places for you!',
  advisory: 'Market-Informed Property Recommendations',
};

const DEFAULT_BODIES: Record<string, string> = {
  professional:
    'Following our recent conversation, I have identified properties that closely align with your stated requirements. Please find the details below.',
  casual:
    "I just wrapped up a fresh search and found some places that I think you're really going to like. Take a look!",
  advisory:
    "After a thorough review of the current inventory, I've selected properties that offer the best combination of value and fit for your criteria.",
};

const FEEDBACK_OPTIONS = [
  { value: 'interested', label: 'Interested' },
  { value: 'not_interested', label: 'Not Interested' },
  { value: 'need_more_info', label: 'Need More Info' },
  { value: 'scheduled_viewing', label: 'Scheduled Viewing' },
] as const;

export default function SendPage() {
  const { runId } = useParams();
  const [approved, setApproved] = useState<RankedListing[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [previewing, setPreviewing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recipientEmail, setRecipientEmail] = useState('');
  const [tone, setTone] = useState('professional');
  const [subject, setSubject] = useState(DEFAULT_SUBJECTS['professional']);
  const [body, setBody] = useState(DEFAULT_BODIES['professional']);
  const [agentName, setAgentName] = useState('Harry');
  const [agentPhone, setAgentPhone] = useState('');
  const [agentEmail, setAgentEmail] = useState('');
  const [brokerageName, setBrokerageName] = useState('');
  const [previewHtml, setPreviewHtml] = useState<string | null>(null);
  const [sendResult, setSendResult] = useState<{
    status: string;
    message: string;
  } | null>(null);
  const [emailHistory, setEmailHistory] = useState<EmailSendRecord[]>([]);
  const [feedbackLoading, setFeedbackLoading] = useState<number | null>(null);

  const pipelineRunId = Number(runId);

  const loadHistory = async () => {
    try {
      const history = await getEmailHistory(pipelineRunId);
      setEmailHistory(history);
    } catch {
      // Non-critical — don't block the page
    }
  };

  useEffect(() => {
    async function load() {
      try {
        const data = await getPendingReview(pipelineRunId);
        setApproved(data.rankings.filter((r) => r.approved_by_harry === true));

        const status = await getSendStatus(pipelineRunId);
        if (status.status === 'sent') {
          setSendResult({
            status: 'sent',
            message: `${status.sent_count} listings were sent on ${new Date(status.sent_at!).toLocaleString()}.`,
          });
        }

        await loadHistory();
      } catch {
        setError('Failed to load send data.');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  const brandingFields = {
    agent_phone: agentPhone,
    agent_email: agentEmail,
    brokerage_name: brokerageName,
  };

  const handleToneChange = (newTone: string) => {
    setTone(newTone);
    setSubject(DEFAULT_SUBJECTS[newTone] ?? DEFAULT_SUBJECTS['professional']);
    setBody(DEFAULT_BODIES[newTone] ?? DEFAULT_BODIES['professional']);
    setPreviewHtml(null);
  };

  const handlePreview = async () => {
    setPreviewing(true);
    setError(null);
    try {
      const result = await previewEmail(
        pipelineRunId,
        tone,
        subject,
        body,
        agentName,
        brandingFields,
      );
      setPreviewHtml(result.html);
    } catch {
      setError('Failed to generate preview.');
    } finally {
      setPreviewing(false);
    }
  };

  const handleSend = async () => {
    if (!recipientEmail.trim()) return;
    setSending(true);
    setError(null);
    try {
      const result = await sendEmail(
        pipelineRunId,
        recipientEmail.trim(),
        tone,
        subject,
        body,
        agentName,
        brandingFields,
      );
      setSendResult({ status: result.status, message: result.message });
      await loadHistory();
    } catch {
      setError('Failed to send email.');
    } finally {
      setSending(false);
    }
  };

  const handleFeedback = async (sendId: number, feedback: string) => {
    setFeedbackLoading(sendId);
    try {
      await submitFeedback(sendId, feedback);
      await loadHistory();
    } catch {
      setError('Failed to record feedback.');
    } finally {
      setFeedbackLoading(null);
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
        <>
          {/* Tone selector */}
          <section className="border border-ink bg-surface">
            <div className="p-6 border-b border-ink font-heading uppercase">
              Email Tone
            </div>
            <div className="p-6">
              <div className="flex gap-3">
                {TONE_OPTIONS.map((opt) => (
                  <button
                    key={opt.key}
                    onClick={() => handleToneChange(opt.key)}
                    className={`flex-1 py-2.5 text-[11px] uppercase tracking-[1px] border transition-colors cursor-pointer ${
                      tone === opt.key
                        ? 'bg-ink text-surface border-ink'
                        : 'bg-transparent text-ink border-ink/30 hover:border-ink'
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          {/* Email fields */}
          <section className="border border-ink bg-surface">
            <div className="p-6 border-b border-ink font-heading uppercase">
              Compose Email
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                  Agent Name
                </label>
                <input
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                    Agent Phone (optional)
                  </label>
                  <input
                    type="text"
                    value={agentPhone}
                    onChange={(e) => setAgentPhone(e.target.value)}
                    placeholder="(555) 123-4567"
                    className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                    Agent Email (optional)
                  </label>
                  <input
                    type="email"
                    value={agentEmail}
                    onChange={(e) => setAgentEmail(e.target.value)}
                    placeholder="agent@example.com"
                    className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                  />
                </div>
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                  Brokerage Name (optional)
                </label>
                <input
                  type="text"
                  value={brokerageName}
                  onChange={(e) => setBrokerageName(e.target.value)}
                  placeholder="ABC Realty"
                  className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                  Subject Line
                </label>
                <input
                  type="text"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                  Email Body
                </label>
                <textarea
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  rows={4}
                  className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors resize-y"
                />
              </div>
              <div>
                <label className="block text-[10px] uppercase tracking-[1px] opacity-50 mb-2">
                  Recipient Email
                </label>
                <input
                  type="email"
                  value={recipientEmail}
                  onChange={(e) => setRecipientEmail(e.target.value)}
                  placeholder="client@example.com"
                  className="w-full px-4 py-2.5 border border-ink bg-transparent text-[13px] font-mono outline-none focus:border-accent-orange transition-colors"
                />
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handlePreview}
                  disabled={previewing || approved.length === 0}
                  className="flex-1 py-3 border border-ink text-[11px] uppercase tracking-[1px] cursor-pointer hover:bg-ink hover:text-surface transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {previewing ? 'Generating...' : 'Preview'}
                </button>
                <button
                  onClick={handleSend}
                  disabled={sending || !recipientEmail.trim() || approved.length === 0}
                  className="flex-1 py-3 bg-ink text-surface text-[11px] uppercase tracking-[1px] cursor-pointer hover:opacity-80 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {sending ? 'Sending...' : `Send ${approved.length} Listings`}
                </button>
              </div>
            </div>
          </section>

          {/* Preview */}
          {previewHtml && (
            <section className="border border-ink bg-surface">
              <div className="p-6 border-b border-ink font-heading uppercase">
                Email Preview
              </div>
              <div className="p-6">
                <div
                  className="border border-ink/20 bg-white p-0"
                  style={{ minHeight: 200 }}
                >
                  <div dangerouslySetInnerHTML={{ __html: previewHtml }} />
                </div>
              </div>
            </section>
          )}
        </>
      )}

      {sendResult?.status === 'error' && (
        <ErrorAlert message={sendResult.message} />
      )}

      {/* Send History */}
      {emailHistory.length > 0 && (
        <section className="border border-ink bg-surface">
          <div className="p-6 border-b border-ink font-heading uppercase">
            Send History
          </div>
          <div className="divide-y divide-ink/20">
            {emailHistory.map((record) => (
              <div key={record.id} className="p-6 space-y-3">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="font-heading text-[13px] uppercase">
                      {record.recipient_email}
                    </span>
                    <span className="block text-[11px] opacity-60 mt-1">
                      {record.subject} &middot; {record.tone}
                    </span>
                    {record.sent_at && (
                      <span className="block text-[10px] opacity-40 mt-1">
                        Sent {new Date(record.sent_at).toLocaleString()}
                      </span>
                    )}
                  </div>
                  <span
                    className={`text-[10px] uppercase tracking-[1px] px-2 py-1 border ${
                      record.status === 'responded'
                        ? 'border-accent-green text-accent-green'
                        : 'border-ink/30 opacity-50'
                    }`}
                  >
                    {record.status}
                  </span>
                </div>

                {record.client_feedback ? (
                  <div className="text-[11px] opacity-70">
                    Feedback: <strong>{record.client_feedback.replace(/_/g, ' ')}</strong>
                    {record.client_feedback_at && (
                      <span className="ml-2 opacity-50">
                        ({new Date(record.client_feedback_at).toLocaleString()})
                      </span>
                    )}
                  </div>
                ) : (
                  <div className="flex gap-2 flex-wrap">
                    <span className="text-[10px] uppercase tracking-[1px] opacity-40 self-center mr-1">
                      Record feedback:
                    </span>
                    {FEEDBACK_OPTIONS.map((opt) => (
                      <button
                        key={opt.value}
                        onClick={() => handleFeedback(record.id, opt.value)}
                        disabled={feedbackLoading === record.id}
                        className="px-3 py-1.5 text-[10px] uppercase tracking-[0.5px] border border-ink/30 hover:border-ink hover:bg-ink hover:text-surface transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        {opt.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
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
